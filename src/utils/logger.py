"""
Structured logging setup — one call, consistent format everywhere.

Every module does:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)

Format includes the timestamp, level, module name (so you know which
agent/client logged it), and the message — important once 6 agents are all
logging during a single pipeline run and you need to trace what happened.
"""

import logging
import sys

_CONFIGURED = False


def _configure_root_logger() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure_root_logger()
    return logging.getLogger(name)
