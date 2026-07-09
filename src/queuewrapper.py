import logging
from typing import Any, Callable

import pika
from pika.exceptions import (
    AMQPConnectionError,
    AMQPError,
    ConnectionClosedByBroker,
    ConnectionWrongStateError,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential, wait_fixed

from config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def initialise_pika_connection(
    host: str,
    username: str,
    password: str,
    port: str | int = 5672,
    connection_attempts: int = 20,
    retry_delay_in_seconds: float = 5,
    heartbeat: int = 60,
) -> pika.BlockingConnection:
    """Crea una `BlockingConnection` de Pika.
    Args:
        host: Host de Pika
        username: Nombre de usuario para la autenticación con el host de Pika
        password: Contraseña para la autenticación con el host de Pika
        port: Puerto del host de Pika
        connection_attempts: Número de intentos del canal antes de rendirse
        retry_delay_in_seconds: Retraso en segundos entre intentos del canal
        heartbeat: Retraso del heartbeat en segundos
    Returns:
        `BlockingConnection` de Pika con los parámetros proporcionados
    """

    import pika

    parameters = _get_pika_parameters(
        host,
        username,
        password,
        port,
        connection_attempts,
        retry_delay_in_seconds,
    )
    return pika.BlockingConnection(parameters)


def _get_pika_parameters(
    host: str,
    username: str,
    password: str,
    port: str | int = 5672,
    connection_attempts: int = 20,
    retry_delay_in_seconds: float = 5,
    heartbeat: int = 60,
) -> pika.ConnectionParameters | pika.URLParameters:
    """Crea los parámetros `Parameters` de Pika.
    Args:
        host: Host de Pika
        username: Nombre de usuario para la autenticación con el host de Pika
        password: Contraseña para la autenticación con el host de Pika
        port: Puerto del host de Pika
        connection_attempts: Número de intentos del canal antes de rendirse
        retry_delay_in_seconds: Retraso en segundos entre intentos del canal
        heartbeat: Retraso del heartbeat en segundos
    Returns:
        Parámetros `Parameters` de Pika que se pueden usar para crear una nueva conexión a un broker.
    """

    import pika

    if host.startswith("amqp"):
        # El usuario proporcionó una URL amqp que contiene toda la información
        parameters = pika.URLParameters(host)
        parameters.connection_attempts = connection_attempts
        parameters.retry_delay = retry_delay_in_seconds
        parameters.heartbeat = heartbeat
        if username:
            parameters.credentials = pika.PlainCredentials(username, password)
    else:
        # El host parece ser solo el host, por lo que usamos nuestros parámetros
        parameters = pika.ConnectionParameters(
            host,
            port=port,
            credentials=pika.PlainCredentials(username, password),
            connection_attempts=connection_attempts,
            retry_delay=retry_delay_in_seconds,
            heartbeat=heartbeat,
        )

    return parameters


def close_pika_channel(channel) -> None:
    """Intenta cerrar el canal Pika."""

    try:
        channel.close()
        logger.debug("Canal Pika cerrado correctamente.")
    except AMQPError:
        logger.exception("Error al cerrar el canal Pika.")


def close_pika_connection(connection: pika.BlockingConnection) -> None:
    """Intenta cerrar la conexión Pika."""

    try:
        connection.close()
        logger.debug("Conexión Pika con el host cerrada correctamente.")
    except (AMQPError, ConnectionWrongStateError):
        logger.exception("Error al cerrar la conexión Pika con el host.")


class QueueWrapper:
    """Un cliente rabbitmq basado en Pika."""

    def __init__(
        self,
        host: str = settings.AMQP_HOST,
        username: str = settings.AMQP_USER,
        password: str = settings.AMQP_PASS,
        port: str | int = settings.AMQP_PORT,
        heartbeat: int = settings.AMQP_HEART_BEAT,
        connection_attempts: int = 20,
        retry_delay_in_seconds: int = 5,
        prefetch: int = settings.AMQP_PREFETCH_COUNT,
        **kwargs: Any,
    ):

        self._host = host
        self._username = username
        self._password = password
        self._heartbeat = heartbeat
        self._connection_attempts = connection_attempts
        self._retry_delay_in_seconds = retry_delay_in_seconds
        self._prefetch = prefetch

        try:
            self._port = int(port)
        except ValueError:
            raise ValueError("El puerto no se pudo convertir a entero.")

        self._connection = None

    def _configure_blocking_connection(self):
        """Inicializa la conexión de RabbitMQ"""

        logger.debug("Creando una nueva conexión bloqueante.")
        self._connection = initialise_pika_connection(
            host=self._host,
            username=self._username,
            password=self._password,
            port=self._port,
            connection_attempts=self._connection_attempts,
            retry_delay_in_seconds=self._retry_delay_in_seconds,
            heartbeat=self._heartbeat,
        )

    def close_connection(self):
        logger.debug("Cerrando la conexión bloqueante.")
        if self._connection is not None:
            close_pika_connection(self._connection)


class QueueConsumer(QueueWrapper):
    def __init__(self):
        super().__init__()
        self._channel = None

    def _configure_blocking_channel(self, queue: str) -> None:
        self._channel = self._connection.channel()
        self._channel.queue_declare(queue, durable=False)
        self._channel.basic_qos(prefetch_count=self._prefetch)

    @retry(
        retry=retry_if_exception_type(AMQPConnectionError),
        wait=wait_exponential(multiplier=1, max=5),
        reraise=True,
    )
    def consume_from_queue(self, queue: str, callback: Callable) -> None:
        if self._connection is not None:
            if self._connection.is_open:
                close_pika_connection(self._connection)

        self._configure_blocking_connection()
        self._configure_blocking_channel(queue)

        self._channel.basic_consume(queue, on_message_callback=callback)
        self._channel.start_consuming()


class QueuePublisher(QueueWrapper):
    def __init__(self):
        super().__init__()
        self._channel = None

    def _configure_blocking_channel(self) -> None:
        if self._channel is None or self._channel.is_closed:
            logger.debug("Abriendo un nuevo canal de publicación.")
            self._channel = self._connection.channel()

    @retry(
        retry=retry_if_exception_type(AMQPConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
    )
    def publish_to_queue(self, route: str, payload: dict[str, Any], id: str) -> None:
        if self._connection is None or self._connection.is_closed:
            # Intentar restablecer la conexión
            logger.debug("Abriendo una nueva conexión de publicación.")
            self._configure_blocking_connection()

        # Si tenemos una conexión abierta, procesamos los eventos de datos
        # para asegurarnos de que la conexión siga viva
        try:
            self._connection.process_data_events(0)
        except ConnectionClosedByBroker as error:
            logger.debug(
                f"El broker cerró la conexión: {error}. Reintentando...")
            self._configure_blocking_connection()
        except AMQPConnectionError as error:
            logger.debug(f"La conexión fue cerrada: {error}. Reintentando...")
            self._configure_blocking_connection()

        self._configure_blocking_channel()

        logger.debug(f"Publicando mensaje en la ruta '{route}'.")
        try:
            self._channel.basic_publish(
                exchange="",
                routing_key=route,
                body=payload,
                properties=pika.BasicProperties(correlation_id=id)
            )

        except AssertionError:
            logger.error("Error al publicar el mensaje.")
