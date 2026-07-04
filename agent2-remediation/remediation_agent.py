#!/usr/bin/env python3
"""
Testlab AI Remediation Agent (Agent 2)
Analyzes issues and executes approved remediation actions
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from anthropic import Anthropic
import sqlite3
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RemediationTools:
    """Safe remediation tools for common issues"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.dry_run = config.get('dry_run', True)
        self.approved_actions = config.get('approved_actions', [])
        
    def is_action_approved(self, action_type: str) -> bool:
        """Check if action type is approved for automatic execution"""
        return action_type in self.approved_actions or '*' in self.approved_actions
    
    def restart_container(self, container_name: str) -> Dict[str, Any]:
        """Restart a Docker container"""
        action_type = 'restart_container'
        
        if not self.is_action_approved(action_type):
            return {
                'success': False,
                'message': f'Action {action_type} not approved for automatic execution',
                'requires_approval': True
            }
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would restart container: {container_name}")
            return {
                'success': True,
                'dry_run': True,
                'message': f'Would restart container {container_name}'
            }
        
        try:
            result = subprocess.run(
                ['docker', 'restart', container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully restarted container: {container_name}")
                return {
                    'success': True,
                    'message': f'Container {container_name} restarted successfully'
                }
            else:
                logger.error(f"Failed to restart container: {result.stderr}")
                return {
                    'success': False,
                    'message': f'Failed to restart: {result.stderr}'
                }
        except Exception as e:
            logger.error(f"Error restarting container: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def clear_logs(self, service_name: str) -> Dict[str, Any]:
        """Clear logs for a service (Docker logs)"""
        action_type = 'clear_logs'
        
        if not self.is_action_approved(action_type):
            return {
                'success': False,
                'message': f'Action {action_type} not approved',
                'requires_approval': True
            }
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would clear logs for: {service_name}")
            return {
                'success': True,
                'dry_run': True,
                'message': f'Would clear logs for {service_name}'
            }
        
        try:
            # Truncate Docker logs
            result = subprocess.run(
                ['truncate', '-s', '0', f'/var/lib/docker/containers/*{service_name}*/*-json.log'],
                capture_output=True,
                text=True,
                timeout=10,
                shell=True
            )
            
            return {
                'success': True,
                'message': f'Logs cleared for {service_name}'
            }
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def clean_disk_space(self, target_path: str = None) -> Dict[str, Any]:
        """Clean up disk space using Docker system prune"""
        action_type = 'clean_disk_space'
        
        if not self.is_action_approved(action_type):
            return {
                'success': False,
                'message': f'Action {action_type} not approved',
                'requires_approval': True
            }
        
        if self.dry_run:
            logger.info("[DRY RUN] Would run Docker system prune")
            return {
                'success': True,
                'dry_run': True,
                'message': 'Would run Docker system prune to free space'
            }
        
        try:
            # Run Docker system prune
            result = subprocess.run(
                ['docker', 'system', 'prune', '-af', '--volumes'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Disk cleanup completed: {result.stdout}'
                }
            else:
                return {
                    'success': False,
                    'message': f'Cleanup failed: {result.stderr}'
                }
        except Exception as e:
            logger.error(f"Error cleaning disk: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def scale_container_resources(self, container_name: str, cpu_limit: str = None, 
                                 memory_limit: str = None) -> Dict[str, Any]:
        """Update container resource limits"""
        action_type = 'scale_resources'
        
        if not self.is_action_approved(action_type):
            return {
                'success': False,
                'message': f'Action {action_type} not approved',
                'requires_approval': True
            }
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update resources for {container_name}")
            return {
                'success': True,
                'dry_run': True,
                'message': f'Would update resources: CPU={cpu_limit}, Memory={memory_limit}'
            }
        
        try:
            cmd = ['docker', 'update']
            if cpu_limit:
                cmd.extend(['--cpus', cpu_limit])
            if memory_limit:
                cmd.extend(['--memory', memory_limit])
            cmd.append(container_name)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Resources updated for {container_name}'
                }
            else:
                return {
                    'success': False,
                    'message': f'Update failed: {result.stderr}'
                }
        except Exception as e:
            logger.error(f"Error updating resources: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def send_alert(self, title: str, message: str, severity: str = 'INFO') -> Dict[str, Any]:
        """Send alert notification"""
        webhook_url = self.config.get('webhook_url')
        
        if not webhook_url:
            logger.warning("No webhook URL configured for alerts")
            return {
                'success': False,
                'message': 'No webhook configured'
            }
        
        try:
            color_map = {
                'INFO': 0x0099FF,
                'WARNING': 0xFFA500,
                'CRITICAL': 0xFF0000
            }
            
            payload = {
                "embeds": [{
                    "title": f"🤖 Remediation Agent: {title}",
                    "description": message,
                    "color": color_map.get(severity, 0x0099FF),
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=5)
            
            if response.status_code == 204:
                return {
                    'success': True,
                    'message': 'Alert sent successfully'
                }
            else:
                return {
                    'success': False,
                    'message': f'Alert failed: HTTP {response.status_code}'
                }
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }


class RemediationDatabase:
    """Database for tracking remediation actions"""
    
    def __init__(self, db_path: str = "/data/remediation_history.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS remediations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                issue_id TEXT,
                action_type TEXT,
                action_details TEXT,
                success BOOLEAN,
                result_message TEXT,
                approved_by TEXT,
                dry_run BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                issue_summary TEXT,
                proposed_action TEXT,
                action_details TEXT,
                severity TEXT,
                approved BOOLEAN DEFAULT 0,
                approved_at DATETIME,
                approved_by TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_remediation(self, action_type: str, details: Dict, success: bool, 
                       result: str, dry_run: bool = False):
        """Log a remediation action"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO remediations 
            (action_type, action_details, success, result_message, dry_run)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            action_type,
            json.dumps(details),
            success,
            result,
            dry_run
        ))
        
        conn.commit()
        conn.close()
    
    def create_approval_request(self, issue: str, action: str, details: Dict, severity: str):
        """Create a pending approval request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO pending_approvals 
            (issue_summary, proposed_action, action_details, severity)
            VALUES (?, ?, ?, ?)
        ''', (
            issue,
            action,
            json.dumps(details),
            severity
        ))
        
        approval_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return approval_id


class AIRemediationAgent:
    """AI-powered remediation agent"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.anthropic = Anthropic(api_key=config['anthropic_api_key'])
        self.tools = RemediationTools(config)
        self.db = RemediationDatabase(config.get('db_path', '/data/remediation_history.db'))
        
    def analyze_issue_for_remediation(self, issue_analysis: str, metrics: Dict) -> Dict[str, Any]:
        """Use AI to determine appropriate remediation actions"""
        logger.info("Analyzing issue for remediation options...")
        
        # Define available tools for Claude
        tools = [
            {
                "name": "restart_container",
                "description": "Restart a Docker container that is unresponsive or misbehaving. Use when a service is down or not responding properly.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "container_name": {
                            "type": "string",
                            "description": "Name of the container to restart"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why this container needs to be restarted"
                        }
                    },
                    "required": ["container_name", "reason"]
                }
            },
            {
                "name": "clean_disk_space",
                "description": "Clean up disk space by removing unused Docker images, containers, and volumes. Use when disk usage is above 85%.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Why disk cleanup is needed"
                        }
                    },
                    "required": ["reason"]
                }
            },
            {
                "name": "send_alert",
                "description": "Send an alert notification for issues that require human attention. Use when automatic remediation is not possible or recommended.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Alert title"
                        },
                        "message": {
                            "type": "string",
                            "description": "Detailed alert message"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["INFO", "WARNING", "CRITICAL"],
                            "description": "Severity level"
                        }
                    },
                    "required": ["title", "message", "severity"]
                }
            },
            {
                "name": "scale_resources",
                "description": "Adjust CPU or memory limits for a container experiencing resource constraints.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "container_name": {
                            "type": "string",
                            "description": "Container to modify"
                        },
                        "cpu_limit": {
                            "type": "string",
                            "description": "New CPU limit (e.g., '2.0' for 2 CPUs)"
                        },
                        "memory_limit": {
                            "type": "string",
                            "description": "New memory limit (e.g., '2g' for 2GB)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why resources need adjustment"
                        }
                    },
                    "required": ["container_name", "reason"]
                }
            }
        ]
        
        prompt = f"""You are a remediation agent for a testlab infrastructure. Based on the following issue analysis, determine what actions should be taken.

Issue Analysis:
{issue_analysis}

Configuration:
- Dry Run Mode: {self.config.get('dry_run', True)}
- Auto-approved actions: {self.config.get('approved_actions', [])}

Guidelines:
1. Only suggest actions that directly address the identified issues
2. Prefer conservative actions (restart > resource scaling > disk cleanup)
3. Always send alerts for CRITICAL issues even if taking automatic action
4. Consider the impact on running services
5. If uncertain or the issue is complex, only send an alert for human review

Use the available tools to propose remediation actions. You can call multiple tools if needed."""

        try:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                tools=tools,
                messages=[{"role": "user", "content": prompt}]
            )
            
            actions_taken = []
            requires_approval = []
            
            # Process tool calls
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    
                    logger.info(f"AI recommends: {tool_name} with {tool_input}")
                    
                    # Execute the tool
                    result = self.execute_tool(tool_name, tool_input)
                    
                    # Log the action
                    self.db.log_remediation(
                        action_type=tool_name,
                        details=tool_input,
                        success=result.get('success', False),
                        result=result.get('message', ''),
                        dry_run=result.get('dry_run', False)
                    )
                    
                    if result.get('requires_approval'):
                        approval_id = self.db.create_approval_request(
                            issue=issue_analysis[:500],
                            action=tool_name,
                            details=tool_input,
                            severity='CRITICAL'
                        )
                        requires_approval.append({
                            'approval_id': approval_id,
                            'action': tool_name,
                            'details': tool_input
                        })
                    
                    actions_taken.append({
                        'action': tool_name,
                        'input': tool_input,
                        'result': result
                    })
            
            return {
                'timestamp': datetime.now().isoformat(),
                'actions_taken': actions_taken,
                'requires_approval': requires_approval,
                'ai_response': response.content
            }
            
        except Exception as e:
            logger.error(f"Remediation analysis failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'actions_taken': []
            }
    
    def execute_tool(self, tool_name: str, tool_input: Dict) -> Dict[str, Any]:
        """Execute a remediation tool"""
        
        if tool_name == "restart_container":
            return self.tools.restart_container(tool_input['container_name'])
        
        elif tool_name == "clean_disk_space":
            return self.tools.clean_disk_space()
        
        elif tool_name == "send_alert":
            return self.tools.send_alert(
                title=tool_input['title'],
                message=tool_input['message'],
                severity=tool_input.get('severity', 'INFO')
            )
        
        elif tool_name == "scale_resources":
            return self.tools.scale_container_resources(
                container_name=tool_input['container_name'],
                cpu_limit=tool_input.get('cpu_limit'),
                memory_limit=tool_input.get('memory_limit')
            )
        
        else:
            return {
                'success': False,
                'message': f'Unknown tool: {tool_name}'
            }
    
    def process_monitoring_alert(self, alert_file: str):
        """Process an alert from the monitoring agent"""
        logger.info(f"Processing alert from: {alert_file}")
        
        try:
            with open(alert_file, 'r') as f:
                alert_data = json.load(f)
            
            # Only process WARNING and CRITICAL alerts
            severity = alert_data.get('severity', 'INFO')
            if severity not in ['WARNING', 'CRITICAL']:
                logger.info(f"Skipping {severity} alert")
                return
            
            # Analyze and remediate
            result = self.analyze_issue_for_remediation(
                issue_analysis=alert_data.get('analysis', ''),
                metrics=alert_data.get('metrics', {})
            )
            
            logger.info(f"Remediation complete: {len(result.get('actions_taken', []))} actions taken")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            return None


def main():
    """Main entry point"""
    
    config = {
        'anthropic_api_key': os.environ.get('ANTHROPIC_API_KEY'),
        'webhook_url': os.environ.get('WEBHOOK_URL'),
        'db_path': os.environ.get('DB_PATH', '/data/remediation_history.db'),
        'dry_run': os.environ.get('DRY_RUN', 'true').lower() == 'true',
        'approved_actions': os.environ.get('APPROVED_ACTIONS', '').split(',')
    }
    
    if not config['anthropic_api_key']:
        logger.error("ANTHROPIC_API_KEY environment variable is required")
        return
    
    agent = AIRemediationAgent(config)
    
    # Check for alert file to process
    alert_file = os.environ.get('ALERT_FILE')
    if alert_file and os.path.exists(alert_file):
        agent.process_monitoring_alert(alert_file)
    else:
        logger.info("Remediation agent started in standby mode")
        logger.info("Provide ALERT_FILE environment variable to process alerts")


if __name__ == '__main__':
    main()
