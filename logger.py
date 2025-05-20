# logger.py

import logging
import sys

def setup_logger():
    """
    Configure and return a logger that writes INFO+ messages to stdout.
    """
    logger = logging.getLogger("solanabot")
    logger.setLevel(logging.INFO)

    # Prevent adding multiple handlers if called more than once
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = "%(asctime)s %(levelname)s %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

    return logger
