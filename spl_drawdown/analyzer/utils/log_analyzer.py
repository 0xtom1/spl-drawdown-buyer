import logging
import os
from logging.handlers import TimedRotatingFileHandler


def get_logger(name: str = "spl-drawdown") -> logging.Logger:
    """
    Creates and configures a custom logger with the specified name.

    Args:
        name (str): Name of the logger (default: 'spl-drawdown').

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Get or create logger
    logger = logging.getLogger(name)

    # Prevent duplicate handlers if logger is already configured
    if logger.hasHandlers():
        return logger

    # Set default log level
    logger.setLevel(logging.INFO)

    # Formatter for console
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(module)s - %(funcName)s - %(message)s",
        # datefmt="%Y-%m-%d %H:%M:%S.%f",  # Use decimal for milliseconds
    )

    # Formatter for file (includes levelname)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        # datefmt="%Y-%m-%d %H:%M:%S.%f",  # Use decimal for milliseconds
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Create logs directory if it doesn't exist
    log_dir = "spl_drawdown/data/console_logs"
    os.makedirs(log_dir, exist_ok=True)

    # TimedRotatingFileHandler for daily text logs
    log_file = os.path.join(log_dir, "log")
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="D",  # Rotate daily
        interval=1,  # Every 1 day
        backupCount=0,  # No backup files
        delay=True,  # Delay file creation until first log
        utc=True,  # Use UTC time
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    return logger


# Example usage (for testing)
if __name__ == "__main__":
    logger = get_logger()

    def test_function():
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")

    test_function()
