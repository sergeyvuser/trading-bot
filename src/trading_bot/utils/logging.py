import logging
import sys

from loguru import logger

from trading_bot.config.settings import BASE_DIR, settings


class InterceptHandler(logging.Handler):
    """Intercept handler for logging to loguru"""

    def emit(self, record):
        # Get level from record (loguru)
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    logger.info("Setting up logging for strategy...")
    cfg = settings.logging
    strategy_name = settings.ACTIVE_STRATEGY

    logs_dir = BASE_DIR / "logs"
    # Create logs directory if it doesn't exist
    # parents=True creates parent directories if needed, exist_ok=True allows existing directory
    logs_dir.mkdir(exist_ok=True, parents=True)

    # File path for strategy logs
    file_path = logs_dir / f"{strategy_name}.log"

    # Remove default handler
    logger.remove()

    # Console
    logger.add(
        sys.stdout,
        level=cfg.level,
        format=cfg.format,
        colorize=True,
        enqueue=True,  # Thread-safe for asyncio
    )

    # File logging (if enabled)
    if cfg.to_file:
        logger.add(
            str(file_path),
            level=cfg.level,
            format=cfg.format,
            enqueue=True,  # Thread-safe for asyncio
            compression="zip",  # Compress log files
            rotation=cfg.rotation,  # Rotate log files
            retention=cfg.retention,  # Retain for 7 days
        )

    # Intercept logging (for standard logging, e.g. from libraries like requests, urllib3, ccxt, etc.)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    logger.info(f"Logging configured for strategy: {strategy_name}")

    # Disable asyncio logging (if needed)
    # E.g. if asyncio is logging too much
    # logging.getLogger("asyncio").setLevel(logging.WARNING)
