"""Constants for AICTL application."""

from pathlib import Path

# Session configuration
SESSION_PREFIX = "aictl-"

# Available providers
PROVIDERS = ['q_cli', 'claude_code']
DEFAULT_PROVIDER = "q_cli"

# Tmux capture limits
TMUX_HISTORY_LINES = 200

# TODO: remove the terminal history lines and status check lines if they aren't used anywhere
# Terminal output capture limits
TERMINAL_HISTORY_LINES = 200
STATUS_CHECK_LINES = 100

# Application directories
AICTL_HOME_DIR = Path.home() / ".aws" / "aictl"
DB_DIR = AICTL_HOME_DIR / "db"
LOG_DIR = AICTL_HOME_DIR / "logs"
TERMINAL_LOG_DIR = LOG_DIR / "terminal"
TERMINAL_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Terminal log configuration
INBOX_POLLING_INTERVAL = 5  # Seconds between polling for log file changes
INBOX_SERVICE_TAIL_LINES = 5  # Number of lines to check in get_status for inbox service

# Cleanup configuration
RETENTION_DAYS = 14  # Days to keep terminals, messages, and logs

AGENT_CONTEXT_DIR = AICTL_HOME_DIR / "agent-context"

# Agent store directories
LOCAL_AGENT_STORE_DIR = AICTL_HOME_DIR / "agent-store"

# Q CLI directories
Q_AGENTS_DIR = Path.home() / ".aws" / "amazonq" / "cli-agents"

# Database configuration
DATABASE_FILE = DB_DIR / "aictl.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Server configuration
SERVER_HOST = "localhost"
SERVER_PORT = 9889
SERVER_VERSION = "0.1.0"
API_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
