# testlab-ai-agents

AI-powered infrastructure monitoring and remediation for a Proxmox
testlab. Two Claude-backed agents watch your cluster, detect anomalies,
and optionally take corrective action — with a read-only Flask dashboard
and safety gates throughout.

## What It Does

**Agent 1 — Monitor** queries Prometheus and the Proxmox API every
5 minutes, sends a full infrastructure snapshot to Claude, and
classifies the response as INFO / WARNING / CRITICAL. Alerts post
to Slack on WARNING or above. All analyses stored in SQLite for
24-hour history context on subsequent calls.

**Agent 2 — Remediation** (off by default) receives the monitor's
analysis and uses Claude's native tool-use to take corrective action.
Four tools available: `restart_container`, `clean_disk_space`,
`scale_resources`, `send_alert`. Two independent safety gates:
- `DRY_RUN=true` (default) — logs what it would do, touches nothing
- `APPROVED_ACTIONS` allowlist (default: `send_alert` only)

**Dashboard** — read-only Flask app on port 8888 showing 24h severity
counts and the last 20 analyses and remediations.

## Architecture


## Quick Start

```bash
git clone https://github.com/toyedeji/testlab-ai-agents
cd testlab-ai-agents
cp .env.example .env
# Edit .env — add your Anthropic API key and Prometheus URL

# Monitor only (default — safe, no remediation):
docker compose up -d

# Monitor + dashboard:
docker compose --profile dashboard up -d

# Monitor + remediation (read DRY_RUN notes first):
docker compose --profile remediation up -d

# Full stack (includes Prometheus + node-exporter + cAdvisor):
docker compose --profile full-stack up -d
```

## Safety Model

Remediation is off by default. To enable it safely:

1. Start with `DRY_RUN=true` (default) — watch the logs to verify
   Claude is making sensible decisions before anything executes
2. Add actions to `APPROVED_ACTIONS` one at a time:
   `APPROVED_ACTIONS=send_alert,restart_container`
3. Only set `DRY_RUN=false` after you trust the decision pattern

The Docker socket is mounted read-write only for the remediation
container — monitor and dashboard never touch it.

## Prerequisites

- Docker + Docker Compose
- Prometheus instance with node-exporter and cAdvisor
  (or use `--profile full-stack` to deploy them)
- Anthropic API key
- Proxmox API token (optional — enables cluster health checks)
- Slack webhook URL (optional — enables alert posting)

## Configuration

All configuration via `.env` (copy from `.env.example`):

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API key | required |
| `PROMETHEUS_URL` | Prometheus base URL | required |
| `MONITOR_INTERVAL` | Seconds between monitor runs | 300 |
| `DRY_RUN` | Remediation dry-run mode | true |
| `APPROVED_ACTIONS` | Allowed remediation actions | send_alert |
| `SLACK_WEBHOOK_URL` | Slack alert destination | optional |
| `PROXMOX_HOST` | Proxmox API host | optional |

## Project Structure

