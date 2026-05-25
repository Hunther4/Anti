"""
Unified Logger — ANSI-colored console + structured JSON file logging.

Usage:
    from src.logger import AppLogger

    log = AppLogger(__name__)
    log.info("System initialized")
    log.error("Something went wrong", exc_info=True)
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path


class Colors:
    """ANSI escape codes for colored terminal output."""
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"
    UNDERLINE = "\033[4m"
    BOLD = "\033[1m"
    END = "\033[0m"


# Map logging levels to color codes
LEVEL_COLORS = {
    logging.DEBUG: Colors.GRAY,
    logging.INFO: Colors.GREEN,
    logging.WARNING: Colors.YELLOW,
    logging.ERROR: Colors.RED,
    logging.CRITICAL: Colors.RED + Colors.BOLD,
}

LEVEL_LABELS = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARN",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRIT",
}


class ColoredConsoleHandler(logging.Handler):
    """Handler that outputs colored log messages to stderr."""

    def __init__(self, stream=None):
        super().__init__()
        self.stream = stream or sys.stderr

    def emit(self, record):
        try:
            level_color = LEVEL_COLORS.get(record.levelno, Colors.WHITE)
            level_label = LEVEL_LABELS.get(record.levelno, "????")
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            module_name = record.name if record.name != "__main__" else "root"

            # Format: [HH:MM:SS] [LEVEL] [module] message
            prefix = (
                f"{Colors.GRAY}[{timestamp}]{Colors.END} "
                f"{level_color}[{level_label}]{Colors.END} "
                f"{Colors.CYAN}[{module_name}]{Colors.END} "
            )
            msg = self.format(record)
            self.stream.write(f"{prefix}{msg}\n")
            self.stream.flush()
        except Exception:
            self.handleError(record)


class JsonFileHandler(logging.Handler):
    """Handler that writes structured JSON logs to a file."""

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    def emit(self, record):
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": LEVEL_LABELS.get(record.levelno, "????"),
                "module": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info and record.exc_info[0] is not None:
                import traceback
                log_entry["exception"] = "".join(
                    traceback.format_exception(*record.exc_info)
                ).strip()
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            self.handleError(record)


class AppLogger:
    """
    Unified application logger with colored console output and JSON file output.

    Usage:
        logger = AppLogger(__name__)
        logger.info("Hello world")
        logger.error("Boom!", exc_info=True)
    """

    _instances = {}
    _initialized = False

    def __new__(cls, name: str = "__main__", log_file: str = None):
        if name not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name: str = "__main__", log_file: str = None):
        if self._initialized:
            return
        self._initialized = True

        # Default log path: logs/anti.log relative to project root
        if log_file is None:
            # Heuristic: walk up from cwd looking for src/ or the project marker
            base = Path.cwd()
            if (base / "src").is_dir() or (base / "main.py").is_file():
                log_path = base / "logs" / "anti.log"
            else:
                log_path = Path("logs") / "anti.log"
            log_file = str(log_path)

        self.name = name
        self.log_file = log_file

        # Create the underlying Python logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()
        self._logger.propagate = False

        # Console handler (colored, stderr)
        console_handler = ColoredConsoleHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(console_handler)

        # File handler (JSON)
        file_handler = JsonFileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(file_handler)

        # Log first write to confirm the file is writable
        try:
            with open(log_file, "a"):
                pass
        except OSError:
            pass  # If we can't write, console still works

    # --- Public API ---

    def debug(self, msg: str, *args, **kwargs):
        """Log a debug message."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log an info message."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log a warning message."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log an error message."""
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log a critical message."""
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log an exception message with full traceback. Call from within an except block."""
        kwargs["exc_info"] = True
        self._logger.error(msg, *args, **kwargs)

    def get_log_file_path(self) -> str:
        """Return the path to the JSON log file."""
        return self.log_file
