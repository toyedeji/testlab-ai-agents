#!/usr/bin/env python3
"""
Simple web dashboard for viewing AI agent reports
"""

from flask import Flask, render_template, jsonify
import sqlite3
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)

MONITOR_DB = '/data/monitor/analysis_history.db'
REMEDIATION_DB = '/data/remediation/remediation_history.db'


def get_monitor_stats():
    """Get monitoring statistics"""
    if not os.path.exists(MONITOR_DB):
        return None
    
    conn = sqlite3.connect(MONITOR_DB)
    cursor = conn.cursor()
    
    # Get stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical,
            SUM(CASE WHEN severity = 'WARNING' THEN 1 ELSE 0 END) as warning,
            SUM(CASE WHEN severity = 'INFO' THEN 1 ELSE 0 END) as info
        FROM analyses
        WHERE timestamp > datetime('now', '-24 hours')
    """)
    
    stats = cursor.fetchone()
    
    # Get recent analyses
    cursor.execute("""
        SELECT timestamp, severity, category, summary
        FROM analyses
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    
    recent = cursor.fetchall()
    conn.close()
    
    return {
        'stats': {
            'total': stats[0],
            'critical': stats[1],
            'warning': stats[2],
            'info': stats[3]
        },
        'recent': [
            {
                'timestamp': r[0],
                'severity': r[1],
                'category': r[2],
                'summary': r[3]
            }
            for r in recent
        ]
    }


def get_remediation_stats():
    """Get remediation statistics"""
    if not os.path.exists(REMEDIATION_DB):
        return None
    
    conn = sqlite3.connect(REMEDIATION_DB)
    cursor = conn.cursor()
    
    # Get stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN dry_run = 1 THEN 1 ELSE 0 END) as dry_run
        FROM remediations
        WHERE timestamp > datetime('now', '-24 hours')
    """)
    
    stats = cursor.fetchone()
    
    # Get recent actions
    cursor.execute("""
        SELECT timestamp, action_type, success, result_message, dry_run
        FROM remediations
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    
    recent = cursor.fetchall()
    conn.close()
    
    return {
        'stats': {
            'total': stats[0],
            'successful': stats[1],
            'dry_run': stats[2]
        },
        'recent': [
            {
                'timestamp': r[0],
                'action': r[1],
                'success': bool(r[2]),
                'message': r[3],
                'dry_run': bool(r[4])
            }
            for r in recent
        ]
    }


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/monitor')
def api_monitor():
    """API endpoint for monitoring data"""
    data = get_monitor_stats()
    return jsonify(data if data else {'error': 'No data available'})


@app.route('/api/remediation')
def api_remediation():
    """API endpoint for remediation data"""
    data = get_remediation_stats()
    return jsonify(data if data else {'error': 'No data available'})


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'monitor_db': os.path.exists(MONITOR_DB),
        'remediation_db': os.path.exists(REMEDIATION_DB)
    })


if __name__ == '__main__':
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    
    # Simple HTML template
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Testlab AI Agents Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #16c79a; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-card { background: #0f3460; padding: 20px; border-radius: 8px; flex: 1; }
        .stat-value { font-size: 2em; font-weight: bold; color: #16c79a; }
        .severity-critical { color: #ff4757; }
        .severity-warning { color: #ffa502; }
        .severity-info { color: #1e90ff; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; background: #0f3460; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #1a1a2e; }
        th { background: #16213e; color: #16c79a; }
        .timestamp { color: #888; font-size: 0.9em; }
        .refresh { background: #16c79a; color: #1a1a2e; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .refresh:hover { background: #1dd1a1; }
    </style>
    <script>
        async function loadData() {
            try {
                const monitorRes = await fetch('/api/monitor');
                const monitorData = await monitorRes.json();
                
                if (monitorData.stats) {
                    document.getElementById('total-analyses').textContent = monitorData.stats.total;
                    document.getElementById('critical-count').textContent = monitorData.stats.critical;
                    document.getElementById('warning-count').textContent = monitorData.stats.warning;
                    
                    const tbody = document.getElementById('monitor-table');
                    tbody.innerHTML = monitorData.recent.map(r => `
                        <tr>
                            <td class="timestamp">${r.timestamp}</td>
                            <td class="severity-${r.severity.toLowerCase()}">${r.severity}</td>
                            <td>${r.summary}</td>
                        </tr>
                    `).join('');
                }
                
                const remRes = await fetch('/api/remediation');
                const remData = await remRes.json();
                
                if (remData.stats) {
                    document.getElementById('total-actions').textContent = remData.stats.total;
                    document.getElementById('successful-actions').textContent = remData.stats.successful;
                    
                    const tbody = document.getElementById('remediation-table');
                    tbody.innerHTML = remData.recent.map(r => `
                        <tr>
                            <td class="timestamp">${r.timestamp}</td>
                            <td>${r.action}</td>
                            <td>${r.success ? '✓' : '✗'}</td>
                            <td>${r.dry_run ? '(DRY RUN)' : ''} ${r.message}</td>
                        </tr>
                    `).join('');
                }
                
                document.getElementById('last-update').textContent = new Date().toLocaleString();
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }
        
        setInterval(loadData, 30000); // Refresh every 30 seconds
        window.onload = loadData;
    </script>
</head>
<body>
    <div class="container">
        <h1>🤖 Testlab AI Agents Dashboard</h1>
        <p>Last updated: <span id="last-update">Loading...</span> 
           <button class="refresh" onclick="loadData()">Refresh Now</button></p>
        
        <h2>Monitoring Agent (Last 24h)</h2>
        <div class="stats">
            <div class="stat-card">
                <div>Total Analyses</div>
                <div class="stat-value" id="total-analyses">-</div>
            </div>
            <div class="stat-card">
                <div>Critical Issues</div>
                <div class="stat-value severity-critical" id="critical-count">-</div>
            </div>
            <div class="stat-card">
                <div>Warnings</div>
                <div class="stat-value severity-warning" id="warning-count">-</div>
            </div>
        </div>
        
        <h3>Recent Analyses</h3>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Severity</th>
                    <th>Summary</th>
                </tr>
            </thead>
            <tbody id="monitor-table">
                <tr><td colspan="3">Loading...</td></tr>
            </tbody>
        </table>
        
        <h2>Remediation Agent (Last 24h)</h2>
        <div class="stats">
            <div class="stat-card">
                <div>Total Actions</div>
                <div class="stat-value" id="total-actions">-</div>
            </div>
            <div class="stat-card">
                <div>Successful</div>
                <div class="stat-value" id="successful-actions">-</div>
            </div>
        </div>
        
        <h3>Recent Actions</h3>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Success</th>
                    <th>Message</th>
                </tr>
            </thead>
            <tbody id="remediation-table">
                <tr><td colspan="4">Loading...</td></tr>
            </tbody>
        </table>
    </div>
</body>
</html>
    """
    
    with open('templates/dashboard.html', 'w') as f:
        f.write(html_template)
    
    app.run(host='0.0.0.0', port=8080, debug=False)
