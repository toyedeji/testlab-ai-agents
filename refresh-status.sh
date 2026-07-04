#!/bin/bash
# Force agents to validate current status

echo "🔄 Forcing status validation..."

# 1. Restart monitor agent for immediate cycle
echo "1. Triggering immediate monitoring cycle..."
docker-compose restart monitor-agent

# 2. Wait for analysis to complete
echo "2. Waiting 30 seconds for analysis..."
sleep 30

# 3. Show latest result
echo "3. Latest analysis:"
sqlite3 /opt/testlab-ai-agents/data/monitor/analysis_history.db \
  "SELECT datetime(timestamp), severity, summary FROM analyses 
   ORDER BY timestamp DESC LIMIT 1;"

# 4. Restart dashboard to clear cache
echo "4. Refreshing dashboard..."
docker-compose restart dashboard

echo "✅ Done! Refresh your browser: http://<LAN_IP_REDACTED>:8888"
