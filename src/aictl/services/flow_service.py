"""Flow service for scheduled agent sessions."""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import frontmatter
from apscheduler.triggers.cron import CronTrigger

from aictl.clients.database import (
    create_flow as db_create_flow,
    get_flow as db_get_flow,
    list_flows as db_list_flows,
    delete_flow as db_delete_flow,
    update_flow_enabled as db_update_flow_enabled,
    update_flow_run_times as db_update_flow_run_times,
    get_flows_to_run as db_get_flows_to_run
)
from aictl.models.flow import Flow
from aictl.services.terminal_service import create_terminal, send_input
from aictl.utils.template import render_template
from aictl.utils.terminal import generate_session_name

logger = logging.getLogger(__name__)


def _get_next_run_time(cron_expression: str) -> datetime:
    """Calculate next run time from cron expression."""
    trigger = CronTrigger.from_crontab(cron_expression)
    return trigger.get_next_fire_time(None, datetime.now())


def _parse_flow_file(file_path: Path) -> Tuple[Dict, str]:
    """Parse flow file and return metadata and prompt template.
    
    Returns:
        Tuple of (metadata dict, prompt template string)
    """
    if not file_path.exists():
        raise ValueError(f"Flow file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        post = frontmatter.load(f)
    
    return post.metadata, post.content


def add_flow(file_path: str) -> Flow:
    """Add flow from file."""
    try:
        path = Path(file_path).resolve()
        metadata, _ = _parse_flow_file(path)
        
        # Validate required fields
        required_fields = ['name', 'schedule', 'agent_profile']
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Missing required field: {field}")
        
        name = metadata['name']
        schedule = metadata['schedule']
        agent_profile = metadata['agent_profile']
        script = metadata.get('script', '')  # Optional
        
        # Validate cron expression and calculate next run
        try:
            next_run = _get_next_run_time(schedule)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{schedule}': {e}")
        
        # Create flow in database
        flow = db_create_flow(
            name=name,
            file_path=str(path),
            schedule=schedule,
            agent_profile=agent_profile,
            script=script,
            next_run=next_run
        )
        
        logger.info(f"Added flow: {name}")
        return flow
        
    except Exception as e:
        logger.error(f"Failed to add flow from {file_path}: {e}")
        raise


def list_flows() -> List[Flow]:
    """List all flows."""
    return db_list_flows()


def get_flow(name: str) -> Flow:
    """Get flow by name."""
    flow = db_get_flow(name)
    if not flow:
        raise ValueError(f"Flow '{name}' not found")
    return flow


def remove_flow(name: str) -> bool:
    """Remove flow."""
    if not db_delete_flow(name):
        raise ValueError(f"Flow '{name}' not found")
    logger.info(f"Removed flow: {name}")
    return True


def disable_flow(name: str) -> bool:
    """Disable flow."""
    if not db_update_flow_enabled(name, enabled=False):
        raise ValueError(f"Flow '{name}' not found")
    logger.info(f"Disabled flow: {name}")
    return True


def enable_flow(name: str) -> bool:
    """Enable flow and recalculate next_run."""
    flow = get_flow(name)
    
    # Recalculate next_run from now
    next_run = _get_next_run_time(flow.schedule)
    
    if not db_update_flow_enabled(name, enabled=True, next_run=next_run):
        raise ValueError(f"Failed to enable flow '{name}'")
    
    logger.info(f"Enabled flow: {name}")
    return True


def execute_flow(name: str) -> bool:
    """Execute flow: run script, render prompt, launch session."""
    try:
        logger.info(f"Executing flow: {name}")
        flow = get_flow(name)
        
        # Read flow file
        file_path = Path(flow.file_path)
        _, prompt_template = _parse_flow_file(file_path)
        
        # If no script, always execute with empty output
        if not flow.script:
            output = {"execute": True, "output": {}}
        else:
            # Execute script
            script_path = Path(flow.script)
            if not script_path.is_absolute():
                script_path = file_path.parent / script_path
            
            if not script_path.exists():
                raise ValueError(f"Script not found: {script_path}")
            
            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Script failed: {result.stderr}")
                raise ValueError(f"Script failed with exit code {result.returncode}: {result.stderr}")
            
            # Parse JSON output
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise ValueError(f"Script output is not valid JSON: {e}")
            
            if 'execute' not in output:
                raise ValueError("Script output missing 'execute' field")
            
            if 'output' not in output:
                raise ValueError("Script output missing 'output' field")
        
        # Update last_run and calculate next_run
        now = datetime.now()
        next_run = _get_next_run_time(flow.schedule)
        db_update_flow_run_times(name, last_run=now, next_run=next_run)
        
        # Check if we should execute
        if not output['execute']:
            logger.info(f"Flow {name}: skipped (execute=false)")
            return False
        
        # Render prompt template
        rendered_prompt = render_template(prompt_template, output['output'])
        
        # Launch session
        session_name = generate_session_name()
        terminal = create_terminal(
            session_name=session_name,
            provider='q_cli',
            agent_profile=flow.agent_profile,
            new_session=True
        )
        
        # Send rendered prompt to terminal
        send_input(terminal.id, rendered_prompt)
        
        logger.info(f"Flow {name}: launched session {session_name}")
        return True
        
    except Exception as e:
        logger.error(f"Flow {name} failed: {e}", exc_info=True)
        raise


def get_flows_to_run() -> List[Flow]:
    """Get flows that should run now."""
    return db_get_flows_to_run()
