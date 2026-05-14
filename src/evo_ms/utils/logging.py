"""Logging helpers for command-line experiment entry points."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a logger with a default stream handler if none exists."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
