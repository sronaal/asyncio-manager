"""Logging centralizado para asyncio-manager.

Proporciona un logger configurable con salida a consola y archivo rotativo.
Toda la librería usa este mismo logger bajo el nombre 'asyncio_manager'.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configura y retorna el logger centralizado de asyncio-manager.

    Crea o recupera el logger con nombre ``asyncio_manager``.
    Siempre agrega un handler de consola. Si se especifica ``log_file``,
    también agrega un handler de archivo rotativo (10 MB por archivo,
    máximo 5 respaldos).

    Args:
        level: Nivel de logging (default: ``logging.INFO``).
        log_file: Ruta opcional al archivo de log.

    Returns:
        El logger configurado para la librería.

    Example:
        >>> from asyncio_manager import setup_logging
        >>> logger = setup_logging(log_file="/var/log/asterisk/ami.log")
        >>> logger.info("Librería inicializada")
    """
    logger = logging.getLogger("asyncio_manager")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    )
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            str(log_path),
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
        )
        logger.addHandler(file_handler)

    return logger


# Logger por defecto para uso inmediato
logger = setup_logging()
