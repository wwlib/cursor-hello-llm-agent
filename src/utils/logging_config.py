# src/utils/logging_config.py
import os
from pathlib import Path
import logging
from typing import Optional

class LoggingConfig:
    """Centralized logging configuration"""
    PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def get_log_base_dir(cls, session_id: str) -> str:
        """Get the base directory for logs"""
        log_base_dir = os.path.join(cls.PROJECT_ROOT, "agent_memories",  "standard", session_id, "logs")
        os.makedirs(log_base_dir, exist_ok=True)
        return log_base_dir

    @classmethod
    def get_component_log_filename(cls, session_id: str, component_name: str) -> str:
        """Get the filename for a component log"""
        return os.path.join(cls.get_log_base_dir(session_id), f"{component_name}.log")
    
    @classmethod
    def get_component_file_logger(cls, session_id: str, component_name: str, level: int = logging.DEBUG, log_to_console: bool = False, propagate: bool = False,) -> logging.Logger:
        """Get a file logger for a component"""
        log_filename = cls.get_component_log_filename(session_id, component_name)
        os.makedirs(os.path.dirname(log_filename), exist_ok=True)
        handler = logging.FileHandler(log_filename)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(cls.FORMAT))
        logger = logging.getLogger(component_name)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = propagate
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(logging.Formatter(cls.FORMAT))
            logger.addHandler(console_handler)
        return logger

    @classmethod
    def list_log_files(cls, session_id: str) -> list:
        """
        Return a list of log files in the logs directory for a given session_id.
        """
        log_base_dir = cls.get_log_base_dir(session_id)
        if not os.path.exists(log_base_dir):
            return []
        return [
            f for f in os.listdir(log_base_dir)
            if os.path.isfile(os.path.join(log_base_dir, f))
        ]

    @classmethod
    def get_log_file_contents(cls, session_id: str, log_filename: str) -> str:
        """
        Return the contents of a specific log file for a given session_id.
        """
        log_base_dir = cls.get_log_base_dir(session_id)
        full_path = os.path.join(log_base_dir, log_filename)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Log file does not exist: {full_path}")
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

