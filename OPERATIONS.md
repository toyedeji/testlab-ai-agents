# Operations & Maintenance Guide

## Daily Operations

### Morning Checklist (5 minutes)

```bash
# 1. Check agent status
docker-compose ps

# 2. Review overnight alerts
sqlite3 data/monitor/analysis_history.db \
  "SELECT timestamp, severity, summary FROM analyses 
   WHERE timestamp > datetime('now', '-24 hours') 
   AND severity IN ('WARNING', 'CRITICAL')
   ORDER BY timestamp DESC;"

# 3. Check last monitoring cycle
docker-compose logs --tail=50 monitor-agent | grep "Monitoring cycle complete"

# 4. View dashboard
# Open http://your-host:8888 in browser
```

### If Issues Found

```bash
# View full analysis for a specific issue
sqlite3 data/monitor/analysis_history.db \
  "SELECT full_analysis FROM analyses WHERE id = <ID>;"

# Check what remediation did
sqlite3 data/remediation/remediation_history.db \
  "SELECT * FROM remediations WHERE timestamp > datetime('now', '-24 hours');"

# Review detailed logs
docker-compose logs --tail=200 monitor-agent
docker-compose logs --tail=200 remediation-agent
```

## Weekly Maintenance

### Database Maintenance

```bash
# Vacuum databases to reclaim space
sqlite3 data/monitor/analysis_history.db "VACUUM;"
sqlite3 data/remediation/remediation_history.db "VACUUM;"

# Archive old data (keep last 30 days)
sqlite3 data/monitor/analysis_history.db \
  "DELETE FROM analyses WHERE timestamp < datetime('now', '-30 days');"

sqlite3 data/remediation/remediation_history.db \
  "DELETE FROM remediations WHERE timestamp < datetime('now', '-30 days');"
```

### Review Performance

```bash
# Count analyses by severity (last 7 days)
sqlite3 data/monitor/analysis_history.db \
  "SELECT severity, COUNT(*) as count 
   FROM analyses 
   WHERE timestamp > datetime('now', '-7 days')
   GROUP BY severity;"

# Remediation success rate
sqlite3 data/remediation/remediation_history.db \
  "SELECT 
     COUNT(*) as total,
     SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
     SUM(CASE WHEN dry_run = 1 THEN 1 ELSE 0 END) as dry_runs
   FROM remediations 
   WHERE timestamp > datetime('now', '-7 days');"

# Most common actions
sqlite3 data/remediation/remediation_history.db \
  "SELECT action_type, COUNT(*) as count 
   FROM remediations 
   WHERE timestamp > datetime('now', '-7 days')
   GROUP BY action_type 
   ORDER BY count DESC;"
```

### Update Agents

```bash
# Pull latest code (if using git)
git pull

# Rebuild images
docker-compose build

# Restart with new version
docker-compose down
docker-compose up -d

# Verify startup
docker-compose logs -f monitor-agent
```

## Monthly Tasks

### Tune Configuration

Review false positives and adjust thresholds:

```bash
# Identify recurring INFO alerts that might be noise
sqlite3 data/monitor/analysis_history.db \
  "SELECT summary, COUNT(*) as frequency 
   FROM analyses 
   WHERE severity = 'INFO' 
   AND timestamp > datetime('now', '-30 days')
   GROUP BY summary 
   HAVING frequency > 10
   ORDER BY frequency DESC;"
```

Consider adjusting:
- MONITOR_INTERVAL: If too frequent, increase from 300s to 600s
- Severity thresholds: Edit monitor_agent.py to adjust what's WARNING vs INFO
- APPROVED_ACTIONS: Add more as confidence grows

### Backup Critical Data

```bash
# Backup databases
tar -czf testlab-agents-backup-$(date +%Y%m%d).tar.gz \
  data/monitor/*.db \
  data/remediation/*.db \
  .env

# Backup to remote location
scp testlab-agents-backup-*.tar.gz user@backup-server:/backups/
```

### Review API Usage

Check Anthropic API usage:
1. Visit https://console.anthropic.com
2. Go to Usage section
3. Compare to expected: ~20-50 API calls/day
4. Review costs: Should be $5-15/month

If usage is higher than expected:
```bash
# Check monitoring frequency
grep MONITOR_INTERVAL .env

# Count analyses per day
sqlite3 data/monitor/analysis_history.db \
  "SELECT DATE(timestamp), COUNT(*) 
   FROM analyses 
   WHERE timestamp > datetime('now', '-7 days')
   GROUP BY DATE(timestamp);"
```

## Monitoring the Monitors

### Health Checks

```bash
# Check if agents are running
docker-compose ps | grep -E "monitor-agent|remediation-agent"

# Verify last successful run
docker-compose logs --tail=1 monitor-agent | grep "Monitoring cycle complete"

# Check for errors
docker-compose logs monitor-agent | grep -i error | tail -20
docker-compose logs remediation-agent | grep -i error | tail -20

# Verify disk space for data
df -h data/

# Check database sizes
du -sh data/monitor/*.db
du -sh data/remediation/*.db
```

### Automated Health Monitoring

Create a simple cron job to alert if agents fail:

```bash
#!/bin/bash
# /opt/testlab-ai-agents/health-check.sh

# Check if container is running
if ! docker ps | grep -q testlab-monitor-agent; then
    echo "Monitor agent is not running!" | \
    curl -X POST -H "Content-Type: application/json" \
    -d '{"content":"⚠️ Monitor agent DOWN!"}' \
    $WEBHOOK_URL
    exit 1
fi

# Check if recent analysis exists (within last 10 minutes)
LAST_ANALYSIS=$(sqlite3 data/monitor/analysis_history.db \
  "SELECT timestamp FROM analyses ORDER BY timestamp DESC LIMIT 1;")

if [ -z "$LAST_ANALYSIS" ]; then
    echo "No analyses found!"
    exit 1
fi

# Calculate age in minutes
LAST_EPOCH=$(date -d "$LAST_ANALYSIS" +%s)
NOW_EPOCH=$(date +%s)
AGE_MINUTES=$(( ($NOW_EPOCH - $LAST_EPOCH) / 60 ))

if [ $AGE_MINUTES -gt 10 ]; then
    echo "Last analysis was ${AGE_MINUTES} minutes ago!" | \
    curl -X POST -H "Content-Type: application/json" \
    -d "{\"content\":\"⚠️ No analysis in ${AGE_MINUTES} minutes!\"}" \
    $WEBHOOK_URL
    exit 1
fi

echo "Health check passed"
```

Add to crontab:
```bash
chmod +x /opt/testlab-ai-agents/health-check.sh

# Run every 15 minutes
crontab -e
*/15 * * * * /opt/testlab-ai-agents/health-check.sh
```

## Troubleshooting Common Issues

### Issue: Agent keeps restarting

```bash
# Check logs for error
docker-compose logs --tail=100 monitor-agent

# Common causes:
# 1. Invalid API key
grep ANTHROPIC_API_KEY .env

# 2. Can't reach Prometheus
docker-compose exec monitor-agent curl -f $PROMETHEUS_URL/api/v1/status/config

# 3. Permission issues
ls -la data/monitor/
chmod 755 data/monitor
```

### Issue: No analyses being created

```bash
# Check if agent is running at all
docker-compose logs monitor-agent | tail -50

# Verify Prometheus connectivity
docker-compose exec monitor-agent python3 << 'EOF'
import requests
import os
url = os.environ['PROMETHEUS_URL']
r = requests.get(f"{url}/api/v1/query?query=up")
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")
EOF

# Check database permissions
ls -la data/monitor/analysis_history.db
```

### Issue: Remediation not working

```bash
# Verify remediation agent is running
docker-compose ps remediation-agent

# Check if it's in dry-run mode
grep DRY_RUN .env

# Check approved actions
grep APPROVED_ACTIONS .env

# Verify Docker socket access
docker-compose exec remediation-agent ls -la /var/run/docker.sock
```

### Issue: High API usage / costs

```bash
# Check interval setting
grep MONITOR_INTERVAL .env

# See how often analyses run
sqlite3 data/monitor/analysis_history.db \
  "SELECT 
     DATE(timestamp) as day,
     COUNT(*) as analyses,
     COUNT(*) * 0.003 as estimated_cost_usd
   FROM analyses 
   WHERE timestamp > datetime('now', '-7 days')
   GROUP BY day;"

# Consider increasing interval
# Edit .env: MONITOR_INTERVAL=600  (10 minutes instead of 5)
docker-compose restart monitor-agent
```

### Issue: Disk space growing

```bash
# Check database sizes
du -sh data/monitor/*.db data/remediation/*.db

# Archive old data
sqlite3 data/monitor/analysis_history.db \
  "DELETE FROM analyses WHERE timestamp < datetime('now', '-7 days');"

# Vacuum to reclaim space
sqlite3 data/monitor/analysis_history.db "VACUUM;"
```

### Issue: False positives

Common false positives to tune:

1. **Temporary CPU spikes**: Normal during backups
   - Solution: Adjust CPU threshold or ignore during backup windows

2. **Network blips**: Brief connectivity issues
   - Solution: Require multiple consecutive failures

3. **Expected restarts**: Containers restart during updates
   - Solution: Add maintenance mode flag

To tune, edit `monitor_agent.py` and adjust thresholds in the analysis prompt.

## Performance Optimization

### Reduce API Calls

If costs are high:

```bash
# Increase monitoring interval
MONITOR_INTERVAL=900  # 15 minutes instead of 5

# Use INFO severity less
# Edit monitor_agent.py to only alert on WARNING/CRITICAL
```

### Improve Response Time

```bash
# Run monitoring agent with more CPU
docker-compose up -d --scale monitor-agent=1 \
  --cpus="2.0" \
  --memory="512m"
```

### Optimize Database

```bash
# Add indexes for common queries
sqlite3 data/monitor/analysis_history.db << 'EOF'
CREATE INDEX IF NOT EXISTS idx_timestamp ON analyses(timestamp);
CREATE INDEX IF NOT EXISTS idx_severity ON analyses(severity);
CREATE INDEX IF NOT EXISTS idx_timestamp_severity ON analyses(timestamp, severity);
EOF
```

## Security Best Practices

### Protect API Keys

```bash
# Restrict .env permissions
chmod 600 .env
chown root:root .env

# Don't commit .env to git
echo ".env" >> .gitignore
```

### Limit Docker Socket Access

```bash
# Use read-only mount (already default)
# In docker-compose.yml:
# - /var/run/docker.sock:/var/run/docker.sock:ro
```

### Regular Security Updates

```bash
# Update base images monthly
docker-compose pull
docker-compose build --pull
docker-compose up -d
```

### Audit Logs

```bash
# Review what actions were taken
sqlite3 data/remediation/remediation_history.db \
  "SELECT timestamp, action_type, action_details, success 
   FROM remediations 
   WHERE dry_run = 0
   ORDER BY timestamp DESC 
   LIMIT 20;"
```

## Disaster Recovery

### Complete System Restore

1. Restore from backup:
```bash
tar -xzf testlab-agents-backup-YYYYMMDD.tar.gz
```

2. Verify configuration:
```bash
cat .env
```

3. Start services:
```bash
docker-compose up -d
```

4. Verify functionality:
```bash
docker-compose logs -f monitor-agent
```

### Rebuild from Scratch

If agents corrupted:

```bash
# Stop everything
docker-compose down

# Remove data (backup first!)
mv data data.backup

# Recreate directories
mkdir -p data/{monitor,remediation,shared}

# Restart
docker-compose up -d
```

## Monitoring Metrics

Track these KPIs:

1. **Availability**: Uptime of agents (target: 99%+)
2. **Detection Rate**: Critical issues caught (track manually)
3. **False Positive Rate**: Non-issues flagged as problems (target: <10%)
4. **Remediation Success**: Actions that resolve issues (target: >80%)
5. **MTTR**: Mean time to resolution (should decrease over time)

Generate monthly report:

```bash
echo "=== Monthly Report ==="
echo "Total Analyses:"
sqlite3 data/monitor/analysis_history.db \
  "SELECT COUNT(*) FROM analyses WHERE timestamp > datetime('now', '-30 days');"

echo "By Severity:"
sqlite3 data/monitor/analysis_history.db \
  "SELECT severity, COUNT(*) FROM analyses 
   WHERE timestamp > datetime('now', '-30 days')
   GROUP BY severity;"

echo "Remediations:"
sqlite3 data/remediation/remediation_history.db \
  "SELECT action_type, COUNT(*), 
   SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successful
   FROM remediations 
   WHERE timestamp > datetime('now', '-30 days')
   GROUP BY action_type;"
```

## Getting Help

1. Check logs first: `docker-compose logs`
2. Review database: `sqlite3 data/monitor/analysis_history.db`
3. Test Prometheus connectivity
4. Verify API key validity
5. Check GitHub issues (if using public version)

For Anthropic API issues: https://support.anthropic.com
For Prometheus issues: https://prometheus.io/docs/
For Docker issues: https://docs.docker.com/

Remember: These agents are tools to assist you, not replace you. Always review critical alerts before taking action!
