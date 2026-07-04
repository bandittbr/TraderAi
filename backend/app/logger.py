"""
TradeAI - Sistema de Logs Centralizado
Configura logging estruturado com rotação de arquivos.
Todos os módulos devem importar o logger daqui.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from app.config import settings


def _ensure_log_dir() -> None:
    """Garante que o diretório de logs existe."""
    log_path = Path(settings.log_file).parent
    log_path.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    """
    Configura e retorna o logger principal da aplicação.
    - Saída no console (stdout) com formatação colorida em desenvolvimento.
    - Arquivo de log com rotação diária (mantém 30 dias).
    """
    _ensure_log_dir()

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Formato padrão dos registros
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=date_fmt)

    # Handler: console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Handler: arquivo com rotação diária
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=settings.log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Logger raiz da aplicação
    logger = logging.getLogger("tradeai")
    logger.setLevel(log_level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger filho do logger principal.
    Uso: logger = get_logger(__name__)
    """
    return logging.getLogger(f"tradeai.{name}")


# Logger principal — inicializado na importação do módulo
logger = setup_logging()
