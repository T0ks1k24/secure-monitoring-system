import asyncio
import json
import logging

import aio_pika

from application.dto.ai_event_dto import AIEventDTO
from application.services.event_service import EventService
from core.config import settings
from core.websocket import ws_manager

logger = logging.getLogger(__name__)


class EventConsumer:
    def __init__(self, event_service: EventService | None = None) -> None:
        self._connection = None
        self._channel = None
        self._queue = None
        self._event_service = event_service or EventService()

    async def start(self) -> None:
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=20)

        exchange = await self._channel.declare_exchange(
            settings.EVENTS_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        self._queue = await self._channel.declare_queue(
            settings.EVENTS_QUEUE,
            durable=True,
        )
        await self._queue.bind(exchange, routing_key="events.#")
        await self._queue.consume(self._handle_message)
        logger.info("Backend event consumer subscribed to %s", settings.EVENTS_EXCHANGE)

    async def stop(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        self._connection = None
        self._channel = None
        self._queue = None

    async def _handle_message(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process():
            try:
                data = json.loads(message.body)
                dto = AIEventDTO(**data)
                stored_event = await asyncio.to_thread(
                    self._event_service.ingest_ai_event, dto
                )
                await ws_manager.broadcast(self._to_payload(stored_event))
                logger.debug("Event broadcast: %s camera=%s", stored_event.id, stored_event.camera_id)
            except Exception:
                logger.exception("Failed to process RabbitMQ event message")

    @staticmethod
    def _to_payload(event) -> dict:
        return {
            "id": event.id,
            "camera_id": event.camera_id,
            "event_type": event.event_type,
            "object_class": event.object_class,
            "track_id": event.track_id,
            "confidence": event.confidence,
            "timestamp": event.timestamp.isoformat(),
            "zone_id": event.zone_id,
            "zone_name": event.zone_name,
            "risk": event.risk.value,
            "bbox": event.bbox,
            "metadata": event.metadata,
        }


event_consumer = EventConsumer()
