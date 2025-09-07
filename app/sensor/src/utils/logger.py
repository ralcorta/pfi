"""Structured logging configuration for the ransomware sensor."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
import yaml


def setup_logging(config: Dict[str, Any]) -> structlog.BoundLogger:
    """Configure structured logging for the sensor.
    
    Args:
        config: Logging configuration dictionary
        
    Returns:
        Configured structured logger
    """
    # Create logs directory if it doesn't exist
    log_file = config.get("file", "logs/sensor.log")
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure standard library logging
    log_level = getattr(logging, config.get("level", "INFO").upper())
    log_format = config.get("format", "json")
    
    # Set up file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=config.get("backup_count", 5)
    )
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Configure formatters
    if log_format == "json":
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if log_format == "json" 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger("ransomware_sensor")


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)
