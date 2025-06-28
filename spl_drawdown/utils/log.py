import logging


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

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)

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
