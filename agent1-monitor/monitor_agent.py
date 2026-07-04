#!/usr/bin/env python3
"""
Testlab AI Monitoring Agent (Agent 1)
Continuously monitors Proxmox cluster, containers, and services for anomalies
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import requests
from anthropic import Anthropic
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PrometheusClient:
    """Client for querying Prometheus metrics"""
    
    def __init__(self, url: str):
        self.url = url.rstrip('/')
        
    def query(self, query: str) -> Dict:
        """Execute a PromQL query"""
        try:
            response = requests.get(
                f"{self.url}/api/v1/query",
                params={"query": query},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def query_range(self, query: str, start: datetime, end: datetime, step: str = "1m") -> Dict:
        """Execute a PromQL range query"""
        try:
            response = requests.get(
                f"{self.url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "step": step
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Prometheus range query failed: {e}")
            return {"status": "error", "error": str(e)}


class ProxmoxClient:
    """Client for Proxmox API"""
    
    def __init__(self, url: str, token_id: str, token_secret: str):
        self.url = url.rstrip('/')
        self.headers = {
            "Authorization": f"PVEAPIToken={token_id}={token_secret}"
        }
    
    def get_cluster_status(self) -> Dict:
        """Get cluster status"""
        try:
            response = requests.get(
                f"{self.url}/api2/json/cluster/status",
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Proxmox cluster status failed: {e}")
            return {"error": str(e)}
    
    def get_nodes(self) -> Dict:
        """Get all nodes in cluster"""
        try:
            response = requests.get(
                f"{self.url}/api2/json/nodes",
                headers=self.headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Proxmox nodes query failed: {e}")
            return {"error": str(e)}


class MetricsCollector:
    """Collects metrics from various sources"""
    
    def __init__(self, prometheus: PrometheusClient, proxmox: ProxmoxClient = None):
        self.prometheus = prometheus
        self.proxmox = proxmox
        
    def collect_node_metrics(self) -> Dict[str, Any]:
        """Collect node-level metrics"""
        metrics = {}
        
        # CPU metrics
        cpu_query = '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
        cpu_result = self.prometheus.query(cpu_query)
        metrics['cpu_usage'] = cpu_result
        
        # Memory metrics
        mem_query = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
        mem_result = self.prometheus.query(mem_query)
        metrics['memory_usage'] = mem_result
        
        # Disk I/O
        disk_read_query = 'rate(node_disk_read_bytes_total[5m])'
        disk_write_query = 'rate(node_disk_written_bytes_total[5m])'
        metrics['disk_read'] = self.prometheus.query(disk_read_query)
        metrics['disk_write'] = self.prometheus.query(disk_write_query)
        
        # Network
        net_rx_query = 'rate(node_network_receive_bytes_total{device!~"lo|veth.*"}[5m])'
        net_tx_query = 'rate(node_network_transmit_bytes_total{device!~"lo|veth.*"}[5m])'
        metrics['network_rx'] = self.prometheus.query(net_rx_query)
        metrics['network_tx'] = self.prometheus.query(net_tx_query)
        
        # Disk space
        disk_space_query = '(1 - (node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.*"} / node_filesystem_size_bytes{fstype!~"tmpfs|fuse.*"})) * 100'
        metrics['disk_usage'] = self.prometheus.query(disk_space_query)
        
        return metrics
    
    def collect_container_metrics(self) -> Dict[str, Any]:
        """Collect container-level metrics"""
        metrics = {}
        
        # Container CPU
        container_cpu_query = 'rate(container_cpu_usage_seconds_total{container!=""}[5m]) * 100'
        metrics['container_cpu'] = self.prometheus.query(container_cpu_query)
        
        # Container Memory
        container_mem_query = 'container_memory_usage_bytes{container!=""}'
        metrics['container_memory'] = self.prometheus.query(container_mem_query)
        
        # Container status
        container_status_query = 'container_last_seen{container!=""}'
        metrics['container_status'] = self.prometheus.query(container_status_query)
        
        return metrics
    
    def collect_service_metrics(self) -> Dict[str, Any]:
        """Collect service availability metrics"""
        metrics = {}
        
        # Service up/down status
        up_query = 'up'
        metrics['services_up'] = self.prometheus.query(up_query)
        
        # Response times (if available)
        response_time_query = 'probe_duration_seconds'
        metrics['response_times'] = self.prometheus.query(response_time_query)
        
        return metrics
    
    def collect_proxmox_metrics(self) -> Dict[str, Any]:
        """Collect Proxmox-specific metrics"""
        if not self.proxmox:
            return {}
        
        metrics = {
            'cluster_status': self.proxmox.get_cluster_status(),
            'nodes': self.proxmox.get_nodes()
        }
        
        return metrics


class AnalysisDatabase:
    """SQLite database for storing analysis history"""
    
    def __init__(self, db_path: str = "/data/analysis_history.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                severity TEXT,
                category TEXT,
                summary TEXT,
                full_analysis TEXT,
                metrics_snapshot TEXT,
                actions_taken TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                severity TEXT,
                title TEXT,
                description TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_analysis(self, severity: str, category: str, summary: str, 
                      full_analysis: str, metrics: Dict, actions: List[str] = None):
        """Store an analysis result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analyses (severity, category, summary, full_analysis, metrics_snapshot, actions_taken)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            severity,
            category,
            summary,
            full_analysis,
            json.dumps(metrics),
            json.dumps(actions or [])
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_analyses(self, hours: int = 24, severity: str = None) -> List[Dict]:
        """Get recent analyses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM analyses 
            WHERE timestamp > datetime('now', '-{} hours')
        '''.format(hours)
        
        if severity:
            query += f" AND severity = '{severity}'"
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': r[0],
                'timestamp': r[1],
                'severity': r[2],
                'category': r[3],
                'summary': r[4],
                'full_analysis': r[5]
            }
            for r in results
        ]


class AIMonitoringAgent:
    """Main AI monitoring agent"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.anthropic = Anthropic(api_key=config['anthropic_api_key'])
        
        self.prometheus = PrometheusClient(config['prometheus_url'])
        
        proxmox_config = config.get('proxmox')
        self.proxmox = None
        if proxmox_config:
            self.proxmox = ProxmoxClient(
                proxmox_config['url'],
                proxmox_config['token_id'],
                proxmox_config['token_secret']
            )
        
        self.collector = MetricsCollector(self.prometheus, self.proxmox)
        self.db = AnalysisDatabase(config.get('db_path', '/data/analysis_history.db'))
        
    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all metrics from all sources"""
        logger.info("Collecting metrics from all sources...")
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'nodes': self.collector.collect_node_metrics(),
            'containers': self.collector.collect_container_metrics(),
            'services': self.collector.collect_service_metrics(),
        }
        
        if self.proxmox:
            metrics['proxmox'] = self.collector.collect_proxmox_metrics()
        
        return metrics
    
    def format_metrics_for_analysis(self, metrics: Dict) -> str:
        """Format metrics into a readable string for AI analysis"""
        
        def extract_values(prom_result: Dict) -> List[Dict]:
            """Extract values from Prometheus result"""
            if prom_result.get('status') == 'success':
                return prom_result.get('data', {}).get('result', [])
            return []
        
        output = []
        output.append(f"=== Testlab Metrics Snapshot: {metrics['timestamp']} ===\n")
        
        # Node metrics
        output.append("## Node Metrics ##")
        
        cpu_data = extract_values(metrics['nodes'].get('cpu_usage', {}))
        if cpu_data:
            output.append("CPU Usage:")
            for item in cpu_data:
                instance = item['metric'].get('instance', 'unknown')
                value = float(item['value'][1])
                output.append(f"  - {instance}: {value:.2f}%")
        
        mem_data = extract_values(metrics['nodes'].get('memory_usage', {}))
        if mem_data:
            output.append("\nMemory Usage:")
            for item in mem_data:
                instance = item['metric'].get('instance', 'unknown')
                value = float(item['value'][1])
                output.append(f"  - {instance}: {value:.2f}%")
        
        disk_usage_data = extract_values(metrics['nodes'].get('disk_usage', {}))
        if disk_usage_data:
            output.append("\nDisk Usage:")
            for item in disk_usage_data:
                instance = item['metric'].get('instance', 'unknown')
                mountpoint = item['metric'].get('mountpoint', 'unknown')
                value = float(item['value'][1])
                output.append(f"  - {instance}:{mountpoint}: {value:.2f}%")
        
        # Container metrics
        output.append("\n## Container Metrics ##")
        
        container_cpu = extract_values(metrics['containers'].get('container_cpu', {}))
        if container_cpu:
            output.append("Container CPU Usage (top 10):")
            sorted_containers = sorted(container_cpu, key=lambda x: float(x['value'][1]), reverse=True)[:10]
            for item in sorted_containers:
                name = item['metric'].get('name', 'unknown')
                value = float(item['value'][1])
                output.append(f"  - {name}: {value:.2f}%")
        
        # Service status
        output.append("\n## Service Status ##")
        
        services = extract_values(metrics['services'].get('services_up', {}))
        if services:
            down_services = [s for s in services if float(s['value'][1]) == 0]
            if down_services:
                output.append("Services DOWN:")
                for item in down_services:
                    job = item['metric'].get('job', 'unknown')
                    instance = item['metric'].get('instance', 'unknown')
                    output.append(f"  - {job} ({instance})")
            else:
                output.append("All monitored services are UP")
        
        # Proxmox status
        if 'proxmox' in metrics:
            output.append("\n## Proxmox Cluster ##")
            cluster_status = metrics['proxmox'].get('cluster_status', {})
            if 'data' in cluster_status:
                quorum = any(item.get('type') == 'cluster' for item in cluster_status['data'])
                output.append(f"Cluster Quorum: {'OK' if quorum else 'LOST'}")
        
        return "\n".join(output)
    
    def analyze_with_ai(self, metrics: Dict, context: str = None) -> Dict[str, Any]:
        """Send metrics to Claude for analysis"""
        logger.info("Analyzing metrics with AI...")
        
        formatted_metrics = self.format_metrics_for_analysis(metrics)
        
        # Get recent history for context
        recent_issues = self.db.get_recent_analyses(hours=24, severity='CRITICAL')
        history_context = ""
        if recent_issues:
            history_context = "\n\nRecent Critical Issues (last 24h):\n"
            for issue in recent_issues[:5]:
                history_context += f"- {issue['timestamp']}: {issue['summary']}\n"
        
        prompt = f"""You are an expert testlab infrastructure monitoring AI. Analyze the following metrics from a 2-node Proxmox cluster running various containerized services.

{formatted_metrics}
{history_context}

Additional Context:
- This is a production testlab used for client consulting work and personal services
- The cluster runs Prometheus, Grafana, n8n, Home Assistant, Pi-hole, and various other services
- Previous issues have included Tailscale subnet routing causing network disruptions
- Critical services must maintain high availability

Your analysis should include:

1. **Severity Level**: INFO, WARNING, or CRITICAL
2. **Issues Detected**: List specific problems found
3. **Root Cause Analysis**: What's causing these issues?
4. **Impact Assessment**: What services or operations are affected?
5. **Recommended Actions**: Prioritized steps to resolve issues
6. **Preventive Measures**: How to avoid this in the future
7. **Trend Analysis**: Any concerning patterns developing?

Be specific with thresholds and values. Flag anything that could lead to service disruption."""

        try:
            message = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            analysis_text = message.content[0].text
            
            # Parse severity from response
            severity = "INFO"
            if "CRITICAL" in analysis_text[:200]:
                severity = "CRITICAL"
            elif "WARNING" in analysis_text[:200]:
                severity = "WARNING"
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'severity': severity,
                'analysis': analysis_text,
                'metrics': metrics
            }
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'severity': 'ERROR',
                'analysis': f"Analysis failed: {str(e)}",
                'metrics': metrics
            }
    
    def send_notification(self, analysis: Dict):
        """Send notification based on severity"""
        severity = analysis['severity']
        
        # Extract summary (first paragraph)
        analysis_text = analysis['analysis']
        summary = analysis_text.split('\n\n')[0] if '\n\n' in analysis_text else analysis_text[:200]
        
        # Store in database
        self.db.store_analysis(
            severity=severity,
            category='infrastructure',
            summary=summary,
            full_analysis=analysis_text,
            metrics=analysis['metrics']
        )
        
        # Send webhook notification if configured
        webhook_url = self.config.get('webhook_url')
        if webhook_url and severity in ['WARNING', 'CRITICAL']:
            try:
                color = 0xFF0000 if severity == 'CRITICAL' else 0xFFA500
                
                payload = {
                    "embeds": [{
                        "title": f"🚨 {severity}: Testlab Alert",
                        "description": summary,
                        "color": color,
                        "timestamp": datetime.now().isoformat(),
                        "fields": [
                            {
                                "name": "Full Analysis",
                                "value": analysis_text[:1000] + "..." if len(analysis_text) > 1000 else analysis_text
                            }
                        ]
                    }]
                }
                
                requests.post(webhook_url, json=payload, timeout=5)
                logger.info(f"Notification sent for {severity} alert")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
    
    def run_once(self):
        """Run one monitoring cycle"""
        logger.info("Starting monitoring cycle...")
        
        try:
            # Collect metrics
            metrics = self.collect_all_metrics()
            
            # Analyze with AI
            analysis = self.analyze_with_ai(metrics)
            
            # Handle results
            self.send_notification(analysis)
            
            logger.info(f"Monitoring cycle complete. Severity: {analysis['severity']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Monitoring cycle failed: {e}")
            return None
    
    def run_continuous(self, interval_seconds: int = 300):
        """Run continuous monitoring"""
        logger.info(f"Starting continuous monitoring (interval: {interval_seconds}s)...")
        
        while True:
            try:
                self.run_once()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying


def main():
    """Main entry point"""
    
    # Load configuration
    config = {
        'anthropic_api_key': os.environ.get('ANTHROPIC_API_KEY'),
        'prometheus_url': os.environ.get('PROMETHEUS_URL', 'http://prometheus:9090'),
        'webhook_url': os.environ.get('WEBHOOK_URL'),
        'db_path': os.environ.get('DB_PATH', '/data/analysis_history.db'),
        'interval': int(os.environ.get('MONITOR_INTERVAL', '300'))
    }
    
    # Optional Proxmox configuration
    if os.environ.get('PROXMOX_URL'):
        config['proxmox'] = {
            'url': os.environ['PROXMOX_URL'],
            'token_id': os.environ.get('PROXMOX_TOKEN_ID'),
            'token_secret': os.environ.get('PROXMOX_TOKEN_SECRET')
        }
    
    if not config['anthropic_api_key']:
        logger.error("ANTHROPIC_API_KEY environment variable is required")
        return
    
    # Create and run agent
    agent = AIMonitoringAgent(config)
    
    # Check if we should run once or continuously
    if os.environ.get('RUN_ONCE') == 'true':
        agent.run_once()
    else:
        agent.run_continuous(config['interval'])


if __name__ == '__main__':
    main()
