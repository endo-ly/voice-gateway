"""Application logger."""

import logging

logger = logging.getLogger("voice-gateway")


def setup_logging(level: int | str = logging.INFO) -> None:
    resolved_level = (
        logging.getLevelName(level.upper())
        if isinstance(level, str)
        else level
    )
    if not isinstance(resolved_level, int):
        resolved_level = logging.INFO
    if logger.handlers:
        logger.setLevel(resolved_level)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(resolved_level)
