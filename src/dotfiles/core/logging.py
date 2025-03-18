"""Logging configuration for dotfiles.

This module provides centralized logging configuration for the dotfiles
package, including console and file output with different log levels,
formatters, and handlers.

Example:
    ```python
    from dotfiles.core.logging import setup_logging

    # Basic setup with default settings
    setup_logging()

    # Setup with debug mode and custom log file
    setup_logging(
        debug=True,
        log_file="~/logs/dotfiles.log"
    )

    # Use logging in your code
    import logging
    logger = logging.getLogger(__name__)

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    ```
"""

import logging
import sys
from pathlib import Path
from types import TracebackType
from typing import Optional, Type

from rich.console import Console
from rich.logging import RichHandler

# Create console for rich output
console = Console()


def setup_logging(
    debug: bool = False,
    log_file: Optional[str] = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """Set up logging configuration.

    This function configures logging for both console and file output.
    Console output uses rich formatting for better readability, while
    file output uses a standard format for better parsing.

    The logging configuration includes:
    - Console handler with rich formatting
    - Optional file handler with rotation
    - Different log levels for console and file
    - Custom format for log messages
    - Module-level loggers

    Args:
        debug: Whether to enable debug logging (default: False).
        log_file: Optional path to log file. If provided, logs will be
                 written to this file in addition to console output.
                 The path is expanded to handle ~ for home directory.
        log_format: Format string for log messages (default: standard format
                   with timestamp, logger name, level, and message).

    Example:
        ```python
        from dotfiles.core.logging import setup_logging
        import logging

        # Setup logging with debug mode and file output
        setup_logging(
            debug=True,
            log_file="~/logs/dotfiles.log"
        )

        # Get logger for your module
        logger = logging.getLogger(__name__)

        # Log messages at different levels
        logger.debug("Detailed information")
        logger.info("General information")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical error")

        # Log exceptions with traceback
        try:
            raise ValueError("Something went wrong")
        except Exception as e:
            logger.exception("An error occurred")
        ```
    """
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler with rich formatting
    console_handler = RichHandler(
        console=console,
        show_path=debug,
        enable_link_path=debug,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=debug,
    )
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(console_handler)

    # Add file handler if log file specified
    if log_file:
        # Expand user path and create parent directories
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler with rotation
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # Always log debug to file
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)

    # Log initial configuration
    logger = logging.getLogger(__name__)
    logger.debug("Logging initialized (debug=%s)", debug)
    if log_file:
        logger.debug("Log file: %s", log_file)

    # Disable logging for some noisy modules
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Log uncaught exceptions
    def handle_exception(
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_traceback: Optional[TracebackType],
    ) -> None:
        """Handle uncaught exceptions by logging them.

        Args:
            exc_type: Type of the exception.
            exc_value: The exception instance.
            exc_traceback: Traceback object.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_exception
