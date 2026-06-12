"""Logging estruturado: uma linha JSON por evento, facil de grepar local
e de mandar pra qualquer agregador depois."""

import json
import logging
import sys


class FormatterJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        evento = {
            "nivel": record.levelname.lower(),
            "msg": record.getMessage(),
        }
        dados = getattr(record, "dados", None)
        if dados:
            evento.update(dados)
        return json.dumps(evento, ensure_ascii=False, default=str)


def configura_logging(debug: bool = False) -> logging.Logger:
    logger = logging.getLogger("balcao")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(FormatterJson())
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    return logger


def loga(logger: logging.Logger, msg: str, **dados) -> None:
    logger.info(msg, extra={"dados": dados})
