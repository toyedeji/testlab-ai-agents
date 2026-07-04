#!/bin/bash
# Quick deployment script for Testlab AI Agents

set -e

echo "🤖 Testlab AI Agents - Quick Setup"
echo "===================================="
echo ""

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script should be run as root or with sudo"
   exit 1
fi

# Check for required commands
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Install Docker first."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

echo "✅ Prerequisites check passed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit the .env file with your configuration"
    echo "    Required:"
    echo "    - ANTHROPIC_API_KEY"
    echo "    - PROMETHEUS_URL"
    echo ""
    echo "    Optional:"
    echo "    - WEBHOOK_URL (Discord/Slack)"
    echo "    - PROXMOX_* (for cluster monitoring)"
    echo ""
    read -p "Press Enter after you've edited .env, or Ctrl+C to exit..."
fi

# Validate required environment variables
source .env

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_api_key_here" ]; then
    echo "❌ ANTHROPIC_API_KEY not set in .env file"
    exit 1
fi

if [ -z "$PROMETHEUS_URL" ]; then
    echo "⚠️  PROMETHEUS_URL not set, using default: http://prometheus:9090"
fi

echo "✅ Configuration validated"
echo ""

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/{monitor,remediation,shared}
chmod 755 data data/*

echo "✅ Directories created"
echo ""

# Build images
echo "🔨 Building Docker images..."
docker-compose build

echo "✅ Images built"
echo ""

# Deployment options
echo "Select deployment mode:"
echo "1) Monitor agent only (recommended for first time)"
echo "2) Monitor + Remediation (dry-run mode)"
echo "3) Full stack with dashboard"
echo "4) Custom"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo "🚀 Starting monitoring agent only..."
        docker-compose up -d monitor-agent
        SERVICES="monitor-agent"
        ;;
    2)
        echo "🚀 Starting monitoring + remediation (dry-run)..."
        export DRY_RUN=true
        docker-compose --profile remediation up -d monitor-agent remediation-agent
        SERVICES="monitor-agent remediation-agent"
        ;;
    3)
        echo "🚀 Starting full stack with dashboard..."
        docker-compose --profile remediation --profile dashboard up -d
        SERVICES="all services"
        ;;
    4)
        echo "Run docker-compose commands manually"
        echo "Example: docker-compose up -d monitor-agent"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Deployment complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Monitoring:"
echo "   View logs:    docker-compose logs -f monitor-agent"
echo "   Status:       docker-compose ps"
echo ""
if [ "$choice" = "3" ]; then
    echo "🌐 Dashboard:"
    echo "   URL:          http://$(hostname -I | awk '{print $1}'):8888"
    echo ""
fi
echo "🔧 Management:"
echo "   Stop:         docker-compose down"
echo "   Restart:      docker-compose restart"
echo "   Update:       docker-compose pull && docker-compose up -d"
echo ""
echo "📝 Data locations:"
echo "   Monitor DB:   ./data/monitor/analysis_history.db"
echo "   Remediation:  ./data/remediation/remediation_history.db"
echo ""
echo "⚠️  Important notes:"
echo "   - First analysis runs in ~5 minutes (MONITOR_INTERVAL)"
echo "   - Check logs if no activity after 10 minutes"
echo "   - Remediation runs in DRY_RUN mode by default"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 All set! Your AI agents are now monitoring your testlab."
echo ""
