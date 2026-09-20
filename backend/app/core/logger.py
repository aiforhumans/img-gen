import logging
import sys
from pathlib import Path
from backend.app.core.config import PROJECT_ROOT

LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Standard logging formats
DEFAULT_FORMAT = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
JSON_FORMAT = logging.Formatter(
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
)

def setup_logger(name: str, log_file: Path, level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(DEFAULT_FORMAT)
        fh.setLevel(level)
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(DEFAULT_FORMAT)
        ch.setLevel(level)
        logger.addHandler(ch)

    return logger

# Primary loggers
app_logger = setup_logger("app", LOGS_DIR / "app.log")
gen_logger = setup_logger("generation", LOGS_DIR / "generation.log")

# Error logger captures WARNING and ERROR
error_logger = logging.getLogger("errors")
error_logger.setLevel(logging.WARNING)
error_logger.propagate = False
if not error_logger.handlers:
    efh = logging.FileHandler(LOGS_DIR / "errors.log", encoding="utf-8")
    efh.setFormatter(DEFAULT_FORMAT)
    efh.setLevel(logging.WARNING)
    error_logger.addHandler(efh)
