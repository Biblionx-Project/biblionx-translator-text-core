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
    """Creates a Pika `BlockingConnection`.
    Args:
        host: Pika host
        username: Username for authenticating with the Pika host
        password: Password for authenticating with the Pika host
        port: Port of the Pika host
        connection_attempts: Number of channel attempts before giving up
        retry_delay_in_seconds: Delay in seconds between channel attempts
        heartbeat: Heartbeat delay in seconds
    Returns:
        A Pika `BlockingConnection` with the provided parameters
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
    """Builds Pika connection `Parameters`.
    Args:
        host: Pika host
        username: Username for authenticating with the Pika host
        password: Password for authenticating with the Pika host
        port: Port of the Pika host
        connection_attempts: Number of channel attempts before giving up
        retry_delay_in_seconds: Delay in seconds between channel attempts
        heartbeat: Heartbeat delay in seconds
    Returns:
        Pika `Parameters` that can be used to create a new connection to a broker.
    """

    import pika

    if host.startswith("amqp"):
        # The user provided an amqp URL containing all the info
        parameters = pika.URLParameters(host)
        parameters.connection_attempts = connection_attempts
        parameters.retry_delay = retry_delay_in_seconds
        parameters.heartbeat = heartbeat
        if username:
            parameters.credentials = pika.PlainCredentials(username, password)
    else:
        # The host looks like just a hostname, so we use our own parameters
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
    """Attempts to close the Pika channel."""

    try:
        channel.close()
        logger.debug("Pika channel closed successfully.")
    except AMQPError:
        logger.exception("Error closing the Pika channel.")


def close_pika_connection(connection: pika.BlockingConnection) -> None:
    """Attempts to close the Pika connection."""

    try:
        connection.close()
        logger.debug("Pika connection to the host closed successfully.")
    except (AMQPError, ConnectionWrongStateError):
        logger.exception("Error closing the Pika connection to the host.")


class QueueWrapper:
    """A Pika-based RabbitMQ client."""

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
            raise ValueError("Could not convert the port to an integer.")

        self._connection = None

    def _configure_blocking_connection(self):
        """Initializes the RabbitMQ connection"""

        logger.debug("Creating a new blocking connection.")
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
        logger.debug("Closing the blocking connection.")
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
            logger.debug("Opening a new publishing channel.")
            self._channel = self._connection.channel()

    @retry(
        retry=retry_if_exception_type(AMQPConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
    )
    def publish_to_queue(self, route: str, payload: dict[str, Any], id: str) -> None:
        if self._connection is None or self._connection.is_closed:
            # Try to re-establish the connection
            logger.debug("Opening a new publishing connection.")
            self._configure_blocking_connection()

        # If we have an open connection, process the data events
        # to make sure the connection stays alive
        try:
            self._connection.process_data_events(0)
        except ConnectionClosedByBroker as error:
            logger.debug(
                f"The broker closed the connection: {error}. Retrying...")
            self._configure_blocking_connection()
        except AMQPConnectionError as error:
            logger.debug(f"The connection was closed: {error}. Retrying...")
            self._configure_blocking_connection()

        self._configure_blocking_channel()

        logger.debug(f"Publishing message to route '{route}'.")
        try:
            self._channel.basic_publish(
                exchange="",
                routing_key=route,
                body=payload,
                properties=pika.BasicProperties(correlation_id=id)
            )

        except AssertionError:
            logger.error("Error publishing the message.")
