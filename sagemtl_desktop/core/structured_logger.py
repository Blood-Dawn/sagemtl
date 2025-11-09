"""
Structured logging with JSON formatting and rotation.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """Structured JSON logger with rotation"""

    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize structured logger.

        Args:
            log_dir: Directory for log files (default: ~/.sagemtl/logs)
        """
        # Determine log directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / ".sagemtl" / "logs"

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup loggers
        self.logger = logging.getLogger("sagemtl")
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup file and console handlers"""
        # File handler - JSON format with rotation
        log_file = self.log_dir / "sagemtl.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)

        # JSON formatter for file
        json_formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
            rename_fields={
                'asctime': 'ts',
                'levelname': 'level',
                'name': 'logger'
            }
        )
        file_handler.setFormatter(json_formatter)

        self.logger.addHandler(file_handler)

        # Console handler - Pretty format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Pretty formatter for console
        console_formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(console_handler)

    def log(
        self,
        level: str,
        message: str,
        job_id: Optional[str] = None,
        file: Optional[str] = None,
        stage: Optional[str] = None,
        exc_info: Optional[Exception] = None,
        **extra
    ):
        """
        Log a structured message.

        Args:
            level: Log level (debug, info, warn, error)
            message: Log message
            job_id: Associated job ID
            file: Associated file
            stage: Processing stage (import, translate, epub, crawl)
            exc_info: Exception object if applicable
            **extra: Additional fields
        """
        # Build extra fields
        extra_fields = {}
        if job_id:
            extra_fields['job_id'] = job_id
        if file:
            extra_fields['file'] = file
        if stage:
            extra_fields['stage'] = stage

        # Add any additional fields
        extra_fields.update(extra)

        # Get log method
        log_method = getattr(self.logger, level.lower(), self.logger.info)

        # Log with extra fields
        log_method(
            message,
            exc_info=exc_info,
            extra=extra_fields
        )

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.log('debug', message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log('info', message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log('warning', message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self.log('error', message, **kwargs)

    def get_logger(self) -> logging.Logger:
        """Get underlying logger"""
        return self.logger


# Global logger instance
_global_logger: Optional[StructuredLogger] = None


def get_logger() -> StructuredLogger:
    """
    Get global logger instance (singleton).

    Returns:
        Global StructuredLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger()
    return _global_logger
