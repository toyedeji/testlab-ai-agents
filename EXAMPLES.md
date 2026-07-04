# Example Scenarios & Use Cases

This document shows real-world examples of how the AI agents detect and remediate common testlab issues.

## Scenario 1: Container Memory Leak

**What Happens:**
A container (e.g., n8n) gradually consumes more memory over days until it impacts system performance.

**Detection (Agent 1):**
```
=== Analysis ===
Severity: WARNING

Issues Detected:
- Container 'n8n' memory usage has increased 300% over 48 hours
- Current usage: 1.8GB (was 600MB)
- Rate of increase: ~50MB/hour
- System memory utilization: 78%

Root Cause:
Likely memory leak in application or inefficient workflow processing.

Recommended Actions:
1. Restart n8n container to clear memory
2. Review recent workflow changes
3. Monitor for recurrence
4. Consider resource limits if issue persists
```

**Remediation (Agent 2):**
```
Action Taken: restart_container
Container: n8n
Reason: Memory usage abnormally high and increasing
Result: SUCCESS - Container restarted, memory normalized to 650MB
```

---

## Scenario 2: Disk Space Critical

**What Happens:**
Docker images and logs fill up disk space, approaching critical levels.

**Detection (Agent 1):**
```
=== Analysis ===
Severity: CRITICAL

Issues Detected:
- Disk usage on /dev/sda1: 92%
- Rate of increase: 2% per day
- Estimated time to full: 4 days
- Docker volume usage: 45GB
- Log files in /var/log/containers: 12GB

Impact:
- New containers cannot start
- Database writes may fail
- Risk of service disruption

Recommended Actions:
1. IMMEDIATE: Clean unused Docker resources
2. Rotate/truncate old log files
3. Review container retention policies
4. Consider volume expansion
```

**Remediation (Agent 2):**
```
Action Taken: clean_disk_space
Reason: Disk usage exceeded 90% threshold
Result: SUCCESS - Freed 18GB
  - Removed 23 unused images
  - Removed 47 stopped containers
  - Removed 12 unused volumes
New disk usage: 76%
```

---

## Scenario 3: Service Outage

**What Happens:**
Home Assistant becomes unresponsive after an update.

**Detection (Agent 1):**
```
=== Analysis ===
Severity: CRITICAL

Issues Detected:
- Service 'homeassistant' is DOWN (status: 0)
- Last seen: 15 minutes ago
- Health check failures: 5 consecutive
- Container status: running but not responding
- CPU usage: 0.1% (abnormally low)

Impact:
- Home automation not functioning
- No access to smart home controls
- Automations not executing
- Mobile app cannot connect

Root Cause:
Container appears stuck after recent update. Process running but not accepting connections.

Recommended Actions:
1. Restart Home Assistant container
2. Check logs for errors
3. Verify configuration files
4. Consider rollback if restart fails
```

**Remediation (Agent 2):**
```
Action 1: send_alert
Title: CRITICAL - Home Assistant Down
Severity: CRITICAL
Message: Home Assistant unresponsive for 15 minutes. Attempting restart.

Action 2: restart_container
Container: homeassistant
Result: SUCCESS - Container restarted and responding
Health check: PASSED
Response time: 1.2s (normal)
```

---

## Scenario 4: Network Connectivity Issue

**What Happens:**
Tailscale subnet routing causes local network communication problems (similar to your recent issue).

**Detection (Agent 1):**
```
=== Analysis ===
Severity: CRITICAL

Issues Detected:
- Node 'proxmox-node2' unreachable from monitoring
- Last successful scrape: 8 minutes ago
- Prometheus target status: DOWN
- Network metrics show 100% packet loss to <LAN_IP_REDACTED>
- Other services on same node also unreachable
- Cluster quorum: OK (1 of 2 nodes visible)

Impact:
- Half of cluster capacity unavailable for monitoring
- Cannot assess node health
- Risk of blind spot in infrastructure
- Possible quorum loss if node1 also fails

Root Cause Analysis:
Network connectivity issue. Given recent Tailscale changes, likely routing table conflict.

Recommended Actions:
1. IMMEDIATE: Alert human operator (network issue)
2. Check Tailscale routing configuration
3. Verify local network routing tables
4. Test connectivity from node1 to node2
5. Review recent network changes
```

**Remediation (Agent 2):**
```
Action: send_alert
Title: CRITICAL - Network Connectivity Issue
Severity: CRITICAL
Message: Node proxmox-node2 unreachable. Possible routing conflict.
Requires immediate human attention - network issue cannot be auto-remediated.

Recommended steps:
1. SSH to node2 directly: ssh root@<LAN_IP_REDACTED>
2. Check routing: ip route
3. Check Tailscale: tailscale status
4. Review recent changes: journalctl -u tailscale -n 50

This requires manual intervention due to network infrastructure impact.
```

---

## Scenario 5: CPU Spike

**What Happens:**
A container suddenly maxes out CPU, impacting other services.

**Detection (Agent 1):**
```
=== Analysis ===
Severity: WARNING

Issues Detected:
- Container 'pihole' CPU usage: 280% (2.8 cores)
- Normal baseline: 15%
- Started 4 minutes ago
- Correlates with DNS query spike: 15,000 queries/min (normal: 2,000)
- Possible DNS amplification attack or misconfigured device

Impact:
- System load increased to 8.5 (4 core system)
- Other services experiencing latency
- Web interfaces sluggish

Root Cause:
Abnormal DNS query pattern. Check for:
- Compromised device on network
- Misconfigured service making recursive queries
- External DNS amplification attempt

Recommended Actions:
1. Review Pi-hole query logs for source
2. Temporarily block offending client if identified
3. Scale resources if legitimate traffic
4. Monitor for attack patterns
```

**Remediation (Agent 2):**
```
Action: send_alert
Title: WARNING - Abnormal DNS Activity
Message: Pi-hole experiencing unusual load. Check for compromised devices.

[DRY RUN - Would scale resources]
Proposed: Increase CPU limit from 2 cores to 4 cores
Reason: Legitimate service struggling with load

Human review required to:
1. Identify source of DNS queries
2. Determine if scaling appropriate
3. Check for security issues
```

---

## Scenario 6: Backup Failure

**What Happens:**
Duplicati backup service fails but isn't immediately noticed.

**Detection (Agent 1):**
```
=== Analysis ===
Severity: WARNING

Issues Detected:
- Container 'duplicati' exit status: error (code 1)
- Last successful backup: 72 hours ago
- Backup schedule: daily at 2 AM
- Disk space on backup destination: sufficient
- Container logs show authentication failure

Impact:
- No recent backups available
- Risk of data loss if incident occurs
- RPO (Recovery Point Objective) violated

Root Cause:
Authentication credentials to backup destination likely expired or changed.

Recommended Actions:
1. Alert operator immediately
2. Check backup destination credentials
3. Verify network connectivity to backup target
4. Restart backup job after fixing credentials
5. Perform manual backup once resolved
```

**Remediation (Agent 2):**
```
Action: send_alert
Title: WARNING - Backup Failure
Severity: WARNING
Message: Duplicati backups failing for 72 hours. 
Authentication error to backup destination.

URGENT: No backups being created!

Action required:
1. Log into Duplicati web UI
2. Re-enter backup credentials
3. Test connection
4. Run manual backup
5. Verify automated schedule resumes

This requires immediate human attention - backup failure is a critical risk.
```

---

## Scenario 7: Temperature Alert

**What Happens:**
Server room temperature increases, risking hardware.

**Detection (Agent 1):**
```
=== Analysis ===
Severity: CRITICAL

Issues Detected:
- Node temperature: 72°C (threshold: 70°C)
- Ambient temperature: 28°C (from Home Assistant)
- CPU thermal throttling detected
- Fan speed: 4500 RPM (max: 5000 RPM)
- Temperature trend: +2°C per hour

Impact:
- Risk of hardware damage
- Performance degradation due to throttling
- Potential emergency shutdown if continues
- Cluster stability at risk

Root Cause:
Environmental: Room temperature elevated.
Possible causes:
- HVAC failure
- Blocked airflow
- Seasonal temperature increase
- Dust buildup

Recommended Actions:
1. IMMEDIATE: Check room HVAC system
2. Verify server cooling fans operational
3. Check for blocked vents
4. Consider workload reduction if temp continues rising
5. Prepare for graceful shutdown if critical temp reached
```

**Remediation (Agent 2):**
```
Action 1: send_alert
Title: CRITICAL - Temperature Alert
Severity: CRITICAL
Message: Server temperature 72°C and rising. 
Check HVAC and cooling systems immediately.

Action 2: Home Assistant Integration (if available)
Command: Adjust thermostat to 68°F
Command: Turn on auxiliary cooling
Result: Thermostat adjusted, aux cooling enabled

Monitoring: Will re-check in 10 minutes
If temperature reaches 80°C, will recommend service shutdown.
```

---

## Scenario 8: Database Performance

**What Happens:**
PostgreSQL database queries slow down over time.

**Detection (Agent 1):**
```
=== Analysis ===
Severity: WARNING

Issues Detected:
- Container 'postgres' showing high I/O wait times
- Query response times increased 400%
- Disk I/O: 85% utilization
- Database size increased 35% in 7 days
- No VACUUM operations detected in logs

Impact:
- Applications experiencing slow responses
- n8n workflows timing out
- User-facing services degraded
- Risk of cascading failures

Root Cause:
Database maintenance not performed:
- Table bloat from updates/deletes
- Indexes not optimized
- Statistics outdated
- No recent VACUUM operations

Recommended Actions:
1. Schedule maintenance window
2. Run VACUUM ANALYZE
3. Reindex large tables
4. Review query patterns
5. Consider automated maintenance schedule
```

**Remediation (Agent 2):**
```
Action: send_alert
Title: WARNING - Database Maintenance Required
Message: PostgreSQL performance degraded. Manual maintenance needed.

Recommended maintenance commands:
docker exec postgres psql -U postgres -d your_db -c "VACUUM ANALYZE;"
docker exec postgres psql -U postgres -d your_db -c "REINDEX DATABASE your_db;"

Schedule during low-usage window.
Expected duration: 15-30 minutes.

Auto-remediation not configured for database operations to prevent data risk.
```

---

## Best Practices from These Scenarios

1. **Start Conservative**: Notice how Agent 2 sends alerts for complex issues rather than auto-fixing
2. **Context Matters**: Agents consider your specific setup (Tailscale, Home Assistant, etc.)
3. **Safety First**: Network and database issues always require human review
4. **Preventive**: Agents detect trends before they become critical
5. **Actionable**: Recommendations are specific and immediately usable

## Tuning for Your Environment

After running for a week, review patterns:
- Adjust MONITOR_INTERVAL based on how quickly issues develop
- Add more APPROVED_ACTIONS as you gain confidence
- Customize thresholds in the agent code for your normal baselines
- Integrate with your specific tools (n8n workflows, Home Assistant automations)
