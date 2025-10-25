import logging
import os
from datetime import datetime
from aictl.constants import LOG_DIR

def setup_logging() -> None:
    """Setup logging configuration."""
    log_level = os.getenv("AICTL_LOG_LEVEL", "INFO").upper()
    
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = LOG_DIR / f"aictl_{timestamp}.log"
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file)
        ]
    )
    
    print(f"Server logs: {log_file}")
    print("For debug logs: export AICTL_LOG_LEVEL=DEBUG && aictl-server")
    logging.info(f"Logging to: {log_file}")
