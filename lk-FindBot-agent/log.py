
import logging
from logging import info, debug, warning, critical

logging.basicConfig(filename="logs", level=logging.DEBUG)

__all__ = [
    "info",
    "debug",
    "warning",
    "critical"
]


