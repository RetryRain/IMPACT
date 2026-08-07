from __future__ import annotations

import logging
import sys

logger = logging.getLogger("bytez.clustering")
_configured = False
_quiet = False


def configure_logging(*, quiet: bool = False) -> None:
    global _configured, _quiet
    _quiet = quiet
    if _configured:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    _configured = True


def info(message: str) -> None:
    if _quiet:
        return
    configure_logging()
    logger.info(message)


def stage(message: str) -> None:
    info(f"\n==> {message}")
