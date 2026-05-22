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

                # Будуємо payload одразу з DTO — zone_name вже є в повідомленні від AI сервісу,
                # тому не треба чекати запису в БД для відправки на фронтенд.
                # Broadcast і збереження в БД запускаються ПАРАЛЕЛЬНО через asyncio.gather.
                await asyncio.gather(
                    ws_manager.broadcast(self._dto_to_payload(dto)),
                    asyncio.to_thread(self._event_service.ingest_ai_event, dto),
                )
                logger.debug(
                    "Event broadcast+saved: %s camera=%s", dto.event_id, dto.camera_id
                )
            except Exception:
                logger.exception("Failed to process RabbitMQ event message")

    @staticmethod
    def _dto_to_payload(dto: AIEventDTO) -> dict:
        """Будує WS-payload прямо з DTO без звернення до БД.

        AI сервіс вже включає zone_name у повідомлення RabbitMQ,
        тому всі поля є одразу після парсингу.
        """
        return {
            "id": dto.event_id,
            "camera_id": dto.camera_id,
            "event_type": dto.event_type,
            "object_class": dto.object_class,
            "track_id": dto.track_id,
            "confidence": dto.confidence,
            "timestamp": dto.timestamp_as_datetime().isoformat(),
            "zone_id": dto.zone_id,
            "zone_name": dto.zone_name,
            "risk": dto.risk_level,
            "bbox": dto.bbox.model_dump() if dto.bbox else None,
            "metadata": dto.metadata,
        }


event_consumer = EventConsumer()
