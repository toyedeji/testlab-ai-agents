# Deployment Checklist

## Pre-Deployment

- [ ] Anthropic API key obtained from https://console.anthropic.com
- [ ] Prometheus installed and accessible
- [ ] Node exporter running on all nodes (port 9100)
- [ ] cAdvisor running for container metrics (port 8080)
- [ ] Docker and Docker Compose installed on deployment host
- [ ] Optional: Discord/Slack webhook created for notifications
- [ ] Optional: Proxmox API token created (if using Proxmox features)

## Initial Setup

- [ ] Files copied to `/opt/testlab-ai-agents/` (or your preferred location)
- [ ] `.env` file created from `.env.example`
- [ ] ANTHROPIC_API_KEY set in `.env`
- [ ] PROMETHEUS_URL configured in `.env`
- [ ] WEBHOOK_URL configured (if using notifications)
- [ ] File permissions set: `chmod 600 .env`
- [ ] Deploy script made executable: `chmod +x deploy.sh`

## Configuration Review

- [ ] Prometheus scraping your nodes correctly
- [ ] Test Prometheus query: `curl http://prometheus:9090/api/v1/query?query=up`
- [ ] Verify metrics visible in Prometheus UI
- [ ] Review MONITOR_INTERVAL (default: 300 seconds / 5 minutes)
- [ ] Confirm DRY_RUN=true for safe testing
- [ ] Review APPROVED_ACTIONS (start with just 'send_alert')

## First Deployment

- [ ] Run: `./deploy.sh` (option 1: Monitor only)
- [ ] OR manually: `docker-compose up -d monitor-agent`
- [ ] Check logs: `docker-compose logs -f monitor-agent`
- [ ] Wait 5-10 minutes for first analysis
- [ ] Verify analysis created: `ls -la data/monitor/`
- [ ] Check database: `sqlite3 data/monitor/analysis_history.db "SELECT * FROM analyses LIMIT 1;"`

## Validation

- [ ] First monitoring cycle completed without errors
- [ ] Analysis appears in database
- [ ] If webhook configured, notification received
- [ ] No error messages in logs
- [ ] Container status healthy: `docker-compose ps`

## Optional: Remediation Agent

- [ ] Review remediation examples in EXAMPLES.md
- [ ] Understand available actions and safety implications
- [ ] Keep DRY_RUN=true for testing
- [ ] Start: `docker-compose --profile remediation up -d remediation-agent`
- [ ] Test with sample alert (see EXAMPLES.md)
- [ ] Verify dry-run actions logged correctly
- [ ] Review logs before enabling actual execution

## Optional: Dashboard

- [ ] Start: `docker-compose --profile dashboard up -d dashboard`
- [ ] Access: `http://your-host:8888`
- [ ] Verify data displays correctly
- [ ] Bookmark URL for easy access

## Post-Deployment

- [ ] Add health check to cron (see OPERATIONS.md)
- [ ] Schedule weekly database maintenance
- [ ] Document any custom configurations
- [ ] Set calendar reminder for monthly review
- [ ] Add to your infrastructure documentation
- [ ] Share webhook URL with team (if applicable)

## Week 1 Review

After running for one week:

- [ ] Review all analyses: severity distribution
- [ ] Check false positive rate
- [ ] Verify API usage at console.anthropic.com
- [ ] Tune MONITOR_INTERVAL if needed
- [ ] Adjust severity thresholds if needed
- [ ] Consider enabling more approved actions
- [ ] Update team on findings

## Production Readiness

Before going to production with auto-remediation:

- [ ] Minimum 1 week successful monitoring in dry-run
- [ ] False positive rate < 10%
- [ ] All team members familiar with system
- [ ] Rollback procedure documented
- [ ] Backup strategy in place
- [ ] Set DRY_RUN=false
- [ ] Enable approved actions gradually
- [ ] Monitor closely for first 48 hours

## Ongoing Maintenance

Schedule these tasks:

- [ ] Daily: Quick status check (5 min)
- [ ] Weekly: Review alerts and tune (15 min)
- [ ] Monthly: Full review and optimization (30 min)
- [ ] Quarterly: Update agents and dependencies

## Emergency Procedures

Know how to:

- [ ] Stop all agents: `docker-compose down`
- [ ] View recent logs: `docker-compose logs --tail=100`
- [ ] Disable auto-remediation: Set DRY_RUN=true and restart
- [ ] Restore from backup: See OPERATIONS.md
- [ ] Contact support channels

## Documentation

- [ ] Team trained on system
- [ ] README.md reviewed
- [ ] EXAMPLES.md scenarios understood
- [ ] OPERATIONS.md procedures familiar
- [ ] Custom configurations documented
- [ ] Access credentials secured

## Success Criteria

You'll know it's working when:

- ✅ Analyses run every MONITOR_INTERVAL without errors
- ✅ Real issues are detected and alerted
- ✅ False positives are rare (< 10%)
- ✅ Remediation actions resolve issues (when enabled)
- ✅ You catch issues before they impact services
- ✅ Time to resolution decreases over time

## Troubleshooting

If issues arise, see:

- README.md → Troubleshooting section
- OPERATIONS.md → Troubleshooting Common Issues
- Docker logs: `docker-compose logs`
- Database contents: Query SQLite DBs

## Notes

Use this space for environment-specific notes:

```
Deployment date: _______________
Deployed by: _______________
Custom configurations:



Known issues/quirks:



Team contacts:


```

---

**Remember**: Start conservative, monitor closely, tune gradually. The agents are designed to assist you, not replace your judgment. Always review CRITICAL alerts before relying on auto-remediation.

Good luck! 🚀
