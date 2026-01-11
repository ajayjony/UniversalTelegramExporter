"""Logging configuration setup."""

import logging
import logging.config
import os
from pathlib import Path
from typing import Optional

import yaml

from utils.log import LogFilter


def setup_logging(
    config_file: Optional[str] = None,
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> None:
    """
    Configure logging from YAML configuration file.

    Parameters
    ----------
    config_file : Optional[str]
        Path to logging configuration YAML file.
        If None, uses default config/logging.yaml
    log_level : Optional[str]
        Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_dir : Optional[str]
        Override log directory. Creates if it doesn't exist.
    """
    # Determine config file path
    if config_file is None:
        config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "config", "logging.yaml"
        )

    # Load configuration
    if not os.path.exists(config_file):
        _setup_default_logging(log_level, log_dir)
        return

    try:
        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Create log directory if needed
        if log_dir is None:
            log_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "Output", "logs"
            )

        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Update log file paths in config
        for handler_name, handler_config in config.get("handlers", {}).items():
            if "filename" in handler_config:
                filename = handler_config["filename"]
                # Make relative paths absolute relative to log_dir
                if not os.path.isabs(filename):
                    handler_config["filename"] = os.path.join(log_dir, os.path.basename(filename))
                else:
                    handler_config["filename"] = filename
                # Create parent directory
                Path(handler_config["filename"]).parent.mkdir(parents=True, exist_ok=True)

        # Apply configuration
        logging.config.dictConfig(config)

        # Override log level if provided
        if log_level:
            logging.getLogger().setLevel(log_level)

        # Apply LogFilter to telethon loggers
        logging.getLogger("telethon.client.downloads").addFilter(LogFilter())
        logging.getLogger("telethon.network").addFilter(LogFilter())

        logger = logging.getLogger(__name__)
        logger.debug(f"Logging configured from {config_file}")

    except Exception as e:
        # Fall back to basic logging
        _setup_default_logging(log_level, log_dir)


def _setup_default_logging(log_level: Optional[str] = None, log_dir: Optional[str] = None) -> None:
    """
    Setup basic logging configuration (fallback).

    Parameters
    ----------
    log_level : Optional[str]
        Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_dir : Optional[str]
        Directory for log files
    """
    from rich.logging import RichHandler

    if log_dir is None:
        log_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "Output", "logs"
        )

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper()) if log_level else logging.INFO

    # Console handler with Rich formatting
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_level=True,
        show_path=False,
    )
    console_handler.setLevel(level)

    # File handler
    log_file = os.path.join(log_dir, "exporter.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Filter telethon noise
    logging.getLogger("telethon.client.downloads").addFilter(LogFilter())
    logging.getLogger("telethon.network").addFilter(LogFilter())


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Parameters
    ----------
    name : Optional[str]
        Logger name. If None, uses calling module's __name__

    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    return logging.getLogger(name or __name__)
