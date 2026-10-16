"""Logging setup for ETL pipeline."""
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from etl.config import config


def setup_logger(name: str) -> logging.Logger:
    """Configure and return logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(config.log_level)
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # File handler with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"etl_{timestamp}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(config.log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.log_level)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
