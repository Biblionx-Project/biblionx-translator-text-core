import json
import logging
import threading

from vlibras_translator import translate

from config import settings
from exceptionhandler import handle_exception
from healthcheck import run_healthcheck_thread
from queuewrapper import QueueConsumer, QueuePublisher

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Worker:
    """Worker principal"""

    def __init__(self, translator_queue: str, neural: bool = True):
        """Constructor."""
        self.consumer = QueueConsumer()
        self.publisher = QueuePublisher()

        self.translator_queue = translator_queue

        self.translator = translate.Translator()

        self.translate = lambda text: self.translator.translate(
            text,
            neural=neural
        )

        self.version = None

        try:
            self.version = self.translator.version
        # Para compatibilidad con versiones anteriores de vlibras_translator
        except Exception:
            import importlib.metadata
            self.version = importlib.metadata.version("vlibras_translator")
        finally:
            logger.info(
                f'El núcleo del traductor VLibras utiliza vlibras_translator v{self.version}')

        self.threads = []

    def ack_message(self, channel, delivery_tag):
        self.consumer._connection.add_callback_threadsafe(
            lambda: channel.basic_ack(delivery_tag),
        )

    def reply_message(self, route, message, id):
        logger.info("Enviando respuesta a la solicitud.")

        if id is None:
            logger.error("La solicitud no tiene correlation_id.")

        if route is None:
            logger.error("La solicitud no tiene la ruta reply_to.")
        else:
            self.publisher.publish_to_queue(route, message, id)

    def on_message(self, channel, delivery_tag, properties, body):
        """Realiza la tarea del worker"""

        logger.debug("Procesando una nueva solicitud en un hilo separado")

        try:
            logger.info("Procesando una nueva solicitud de traducción.")
            payload = json.loads(body)
            gloss = self.translate(payload.get("text", ""))

            message = json.dumps({
                'translation': gloss,
                'version': self.version
            })

            self.reply_message(
                route=properties.reply_to,
                message=message,
                id=properties.correlation_id
            )

        except Exception as ex:
            handle_exception(ex)

            self.reply_message(
                route=properties.reply_to,
                message=json.dumps({"error": "Error interno del traductor."}),
                id=properties.correlation_id
            )

        finally:
            if channel.is_open:
                self.ack_message(channel, delivery_tag)

    def process_message(self, channel, method, properties, body):
        """
        La tarea potencialmente toma mucho tiempo para finalizar. Por lo tanto, ejecutamos
        la tarea en un hilo separado asegurándonos de que el bucle I/O
        de RabbitMQ no se bloquee.
        """

        # Limpiar la lista de hilos para que no siga acumulando
        for t in self.threads:
            if not t.is_alive():
                t.handled = True
        self.threads = [t for t in self.threads if not t.handled]

        thread = threading.Thread(
            target=self.on_message,
            args=(channel, method.delivery_tag, properties, body),
        )
        thread.handled = False
        thread.start()
        self.threads.append(thread)

    def start(self):
        """Inicia el consumidor de la cola de mensajes"""
        logger.debug("Iniciando el consumidor de la cola")
        self.consumer.consume_from_queue(
            self.translator_queue,
            self.process_message,
        )

        for thread in self.threads:
            thread.join()

        self.consumer._connection.process_data_events()
        self.consumer.close_connection()

    def exit_gracefully(self, signum, frame):
        """Detiene el consumo de la cola pero finaliza los mensajes actuales."""
        self.consumer.stop_consuming()

    def stop(self):
        """Detiene los consumidores de la cola de mensajes."""
        logger.debug("Deteniendo el consumidor de la cola")
        self.consumer.close_connection()
        logger.debug("Deteniendo el publicador de la cola")
        self.publisher.close_connection()


if __name__ == "__main__":

    from signal import SIGTERM, signal

    worker = None

    try:
        logger.info("Intentando crear el worker de traducción")

        run_healthcheck_thread(settings.HEALTHCHECK_PORT)

        worker = Worker(
            translator_queue=settings.TRANSLATOR_QUEUE,
            neural=settings.ENABLE_DL_TRANSLATION
        )

        logger.info("Iniciando el worker de traducción")

        signal(SIGTERM, worker.exit_gracefully)
        worker.start()

    except KeyboardInterrupt:
        logger.error("KeyboardInterrupt: deteniendo el worker de traducción")
    except Exception:
        logger.exception("Ha ocurrido un error inesperado en el worker de traducción")
    finally:
        if worker:
            worker.stop()
            SystemExit(1)
