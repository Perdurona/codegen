"""
Logging utilities for PR Generation System.

This module provides logging utilities for the PR Generation System.
"""

import logging
import os
import sys
from typing import Optional, Dict, Any, Union

# Log levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def setup_logger(
    name: str,
    level: Union[str, int] = "INFO",
    log_format: str = DEFAULT_LOG_FORMAT,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up logger with consistent format.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format string
        log_file: Log file path (if None, log to stderr)
        
    Returns:
        Configured logger
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = LOG_LEVELS.get(level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Create handlers
    if log_file:
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get logger with default configuration.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger
    """
    # Get log level from environment or use default
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    
    # Get log file from environment or use default
    log_file = os.environ.get("LOG_FILE")
    
    return setup_logger(name, level=log_level, log_file=log_file)

# Create main logger
logger = get_logger("pr_generation")