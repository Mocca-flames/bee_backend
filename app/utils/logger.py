import logging
from logging.handlers import RotatingFileHandler
import os
from app.config import get_settings

def setup_logger(level: str = "INFO") -> logging.Logger:
    """
    Set up and configure the application logger.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create a logger
    logger = logging.getLogger("school_management")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Prevent adding multiple handlers if this function is called multiple times
    if not logger.handlers:
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Create file handler with rotation
        fh = RotatingFileHandler(
            "logs/school_management.log",
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=3
        )
        fh.setLevel(logging.DEBUG)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger