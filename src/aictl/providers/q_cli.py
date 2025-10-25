"""Q CLI provider implementation."""

import re
import logging
from typing import List
from aictl.providers.base import BaseProvider
from aictl.models.terminal import TerminalStatus
from aictl.clients.tmux import tmux_client
from aictl.utils.terminal import wait_until_status, wait_for_shell

logger = logging.getLogger(__name__)

# Regex patterns for Q CLI output analysis (module-level constants)
GREEN_ARROW_PATTERN = r'\x1b\[38;5;10m>\s*\x1b\[39m'
ANSI_CODE_PATTERN = r'\x1b\[[0-9;]*m'
ESCAPE_SEQUENCE_PATTERN = r'\[[?0-9;]*[a-zA-Z]'
CONTROL_CHAR_PATTERN = r'[\x00-\x1f\x7f-\x9f]'
BELL_CHAR = '\x07'
GENERIC_PROMPT_PATTERN = r'\x1b\[38;5;13m>\s*\x1b\[39m\s*$'
IDLE_PROMPT_PATTERN_LOG = r'\x1b\[38;5;13m>\s*\x1b\[39m'

# Error indicators
ERROR_INDICATORS = ["Amazon Q is having trouble responding right now"]


class QCliProvider(BaseProvider):
    """Provider for Q CLI tool integration."""
    
    def __init__(self, terminal_id: str, session_name: str, window_name: str, agent_profile: str):
        super().__init__(terminal_id, session_name, window_name)
        # TODO: remove the ._initialized if it's not referenced anywhere
        self._initialized = False
        self._agent_profile = agent_profile
        # Create dynamic prompt pattern based on agent profile
        # Matches: [agent] !> or [agent] > or [agent] X% > with optional color reset and optional trailing whitespace/newlines
        # The percentage has its own ANSI color codes: \x1b[38;5;10m2% 
        self._idle_prompt_pattern = rf'\x1b\[38;5;14m\[{re.escape(self._agent_profile)}\]\s*(?:\x1b\[38;5;10m\d+%\s*)?(?:\x1b\[38;5;9m!\s*)?\x1b\[38;5;13m>\s*(?:\x1b\[39m)?[\s\n]*$'
        self._permission_prompt_pattern = r'Allow this action\?.*\[.*y.*\/.*n.*\/.*t.*\]:\x1b\[39m\s*' + self._idle_prompt_pattern
    
    
    def initialize(self) -> bool:
        """Initialize Q CLI provider by starting q chat command."""
        # Wait for shell to be ready first
        if not wait_for_shell(tmux_client, self.session_name, self.window_name, timeout=10.0):
            raise TimeoutError("Shell initialization timed out after 10 seconds")
        
        command = f"q chat --agent {self._agent_profile}"
        tmux_client.send_keys(self.session_name, self.window_name, command)
        
        if not wait_until_status(self, TerminalStatus.IDLE, timeout=30.0):
            raise TimeoutError("Q CLI initialization timed out after 30 seconds")
        
        self._initialized = True
        return True
    
    def get_status(self, tail_lines: int = None) -> TerminalStatus:
        """Get Q CLI status by analyzing terminal output."""
        logger.debug(f"get_status: tail_lines={tail_lines}")
        output = tmux_client.get_history(self.session_name, self.window_name, tail_lines=tail_lines)
        
        if not output:
            return TerminalStatus.ERROR
        
        # Check if we have the idle prompt (not processing)
        has_idle_prompt = re.search(self._idle_prompt_pattern, output)
        
        if not has_idle_prompt:
            return TerminalStatus.PROCESSING
        
        # Check for error indicators
        clean_output = re.sub(ANSI_CODE_PATTERN, '', output).lower()
        if any(indicator.lower() in clean_output for indicator in ERROR_INDICATORS):
            return TerminalStatus.ERROR
        
        # Check for permission prompt
        if re.search(self._permission_prompt_pattern, output, re.MULTILINE | re.DOTALL):
            return TerminalStatus.WAITING_USER_ANSWER
        
        # Check for completed state (has response + agent prompt)
        if re.search(GREEN_ARROW_PATTERN, output):
            logger.debug(f"get_status: returning COMPLETED")
            return TerminalStatus.COMPLETED
        
        # Just agent prompt, no response
        return TerminalStatus.IDLE
    
    def extract_last_message_from_script(self, script_output: str) -> str:
        """Extract agent's final response message using green arrow indicator."""
        # Find last green arrow and idle prompt
        green_arrows = list(re.finditer(GREEN_ARROW_PATTERN, script_output))
        idle_prompts = list(re.finditer(self._idle_prompt_pattern, script_output))
        
        if not green_arrows:
            raise ValueError("No Q CLI response found - no green arrow pattern detected")
        
        if not idle_prompts:
            raise ValueError("Incomplete Q CLI response - no final prompt detected")
        
        # Extract text between last green arrow and last idle prompt
        start_pos = green_arrows[-1].end()
        end_pos = idle_prompts[-1].start()
        
        final_answer = script_output[start_pos:end_pos].strip()
        
        if not final_answer:
            raise ValueError("Empty Q CLI response - no content found")
        
        # Clean up the message
        final_answer = re.sub(ANSI_CODE_PATTERN, '', final_answer)
        final_answer = re.sub(ESCAPE_SEQUENCE_PATTERN, '', final_answer)
        final_answer = re.sub(CONTROL_CHAR_PATTERN, '', final_answer)
        return final_answer.strip()
    
    def get_idle_pattern_for_log(self) -> str:
        """Return Q CLI IDLE prompt pattern for log files."""
        return IDLE_PROMPT_PATTERN_LOG
    
    # TODO: exit_cli should run the tmux.send_keys directly with /exit or ctrl-c twice
    def exit_cli(self) -> str:
        """Get the command to exit Q CLI."""
        return "/exit"

    def cleanup(self) -> None:
        """Clean up Q CLI provider."""
        # TODO: remove this cleanup method
        self._initialized = False
