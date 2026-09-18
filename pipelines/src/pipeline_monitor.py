"""Pipeline monitoring with logging and ntfy notifications"""

import logging
import traceback
from datetime import datetime
from pathlib import Path
import requests


class PipelineMonitor:
    """Singleton pipeline monitor with dual logging and ntfy notifications"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        log_file: str = "data/pipeline.log",
        ntfy_topic: str | None = None,
        ntfy_server: str = "https://ntfy.sh"
    ):
        """
        Initialize pipeline monitor (singleton pattern).

        Args:
            log_file: Path to log file
            ntfy_topic: ntfy topic for notifications (None = disabled)
            ntfy_server: ntfy server URL (default: https://ntfy.sh)
        """
        if self._initialized:
            return

        self.log_file = Path(log_file)
        self.ntfy_topic = ntfy_topic
        self.ntfy_server = ntfy_server.rstrip('/')

        # Setup logging with unique logger name
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use class-specific logger to avoid name collisions
        logger_name = f"{__name__}.PipelineMonitor"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # Clear any existing handlers (safety for singleton)
        self.logger.handlers.clear()

        # File handler: all levels (INFO, WARNING, ERROR)
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        self.logger.addHandler(file_handler)

        # Stream handler: warnings and errors only
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.WARNING)
        stream_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        self.logger.addHandler(stream_handler)

        self._initialized = True

    def log_info(self, message: str):
        """Log info message (file only, silent on terminal)"""
        self.logger.info(message)

    def log_warning(self, message: str):
        """Log warning message (file + terminal)"""
        self.logger.warning(message)

    def log_error(self, message: str, exc: Exception | None = None):
        """Log error message with optional exception traceback"""
        self.logger.error(message)
        if exc:
            self.logger.error(traceback.format_exc())

    def send_ntfy(
        self,
        title: str,
        message: str,
        priority: str = "default",
        tags: list[str] | None = None
    ):
        """
        Send ntfy notification.

        Args:
            title: Notification title
            message: Notification body
            priority: urgent, high, default, low, min
            tags: List of emoji tags (e.g., ["warning", "x"])
        """
        if not self.ntfy_topic:
            return

        try:
            url = f"{self.ntfy_server}/{self.ntfy_topic}"
            headers = {
                "Title": title,
                "Priority": priority,
            }
            if tags:
                headers["Tags"] = ",".join(tags)

            requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)
        except Exception as e:
            self.logger.error(f"Failed to send ntfy notification: {e}")

    def notify_failure(self, stage: str, error: Exception):
        """Send failure notification with error details"""
        title = f"Pipeline Failed: {stage}"
        timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        message = f"Stage: {stage}\nError: {str(error)}\nTime: {timestamp}"

        self.log_error(f"Pipeline failure in {stage}: {error}", error)
        self.send_ntfy(title, message, priority="high", tags=["warning", "x"])

    def notify_warning(self, title: str, message: str):
        """Send warning notification (non-fatal)"""
        self.log_warning(f"{title}: {message}")
        self.send_ntfy(title, message, priority="default", tags=["warning"])

    def notify_success(self, stats: dict[str, str | int | float]):
        """Send success notification with pipeline stats"""
        title = "Pipeline Completed"
        message = "\n".join([f"{k}: {v}" for k, v in stats.items()])

        self.log_info(f"Pipeline completed successfully: {stats}")
        self.send_ntfy(title, message, priority="low", tags=["white_check_mark"])

    def validate_or_abort(self, condition: bool, error_message: str, stage: str):
        """
        Validate condition or abort pipeline with notification.

        Args:
            condition: Validation condition (True = pass)
            error_message: Error message if validation fails
            stage: Pipeline stage name

        Raises:
            RuntimeError: If validation fails
        """
        if not condition:
            error = RuntimeError(error_message)
            self.notify_failure(stage, error)
            raise error
