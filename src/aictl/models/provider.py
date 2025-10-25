from enum import Enum


class ProviderType(str, Enum):
    """Provider type enumeration."""
    Q_CLI = "q_cli"
    CLAUDE_CODE = "claude_code"
