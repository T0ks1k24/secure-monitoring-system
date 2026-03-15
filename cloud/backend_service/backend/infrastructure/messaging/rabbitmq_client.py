import json
import logging
import aio_pika
from core.config import settings

logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        if self.connection and not self.connection.is_closed:
            return

        try:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel()
            
            # Declare the zones exchange as a topic exchange
            await self.channel.declare_exchange(
                settings.ZONES_EXCHANGE,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info(f"Connected to RabbitMQ at {settings.RABBITMQ_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def publish_zone_update(self, camera_id: str, action: str = "reload"):
        """
        Publishes a zone update message to the security.zones exchange.
        Routing key: zones.updated.{camera_id}
        """
        try:
            await self.connect()
            
            exchange = await self.channel.get_exchange(settings.ZONES_EXCHANGE)
            
            message_body = {
                "camera_id": camera_id,
                "action": action
            }
            
            message = aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            
            routing_key = f"zones.updated.{camera_id}"
            await exchange.publish(message, routing_key=routing_key)
            
            logger.info(f"Published zone update for camera {camera_id}: {action}")
        except Exception as e:
            logger.error(f"Failed to publish zone update for camera {camera_id}: {e}")

    async def close(self):
        if self.connection:
            await self.connection.close()

rabbitmq_client = RabbitMQClient()
