import logging
from json import JSONDecodeError


def handle_exception(ex):
    logger = logging.getLogger(__name__)

    try:
        if isinstance(ex, JSONDecodeError):
            logger.exception("Se recibió una solicitud de traducción no válida.")
        else:
            logger.exception("Ocurrió una excepción inesperada.")

    except TypeError:
        logger.exception("Ocurrió un error al manejar una excepción.")
