"""
RabbitMQ сервіс — публікація SecurityEvent + слухання zone-updates.

Топологія exchanges:
  security.events (topic) — AI публікує сюди
    routing keys:
      events.person_detected.{camera_id}
      events.weapon_detected.{camera_id}
      events.zone_intrusion.{camera_id}
      ...

  security.zones (topic) — Backend публікує сюди коли зони змінюються
    routing keys:
      zones.updated.{camera_id}   → invalidate кеш конкретної камери
      zones.updated.*             → invalidate всі (рідко)

Переваги topic exchange:
  - db_service підписується на "events.*" → всі події
  - alert_service підписується на "events.weapon_detected.*" → тільки зброя
  - frontend підписується на "events.*.cam1" → тільки своя камера
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable, Optional

from config.settings import settings
from schemas.events import SecurityEvent, ZoneUpdateMessage

logger = logging.getLogger(__name__)


class RabbitMQService:
    def __init__(self) -> None:
        self._connection = None
        self._publish_channel = None
        self._consume_channel = None
        self._connected = False
        self._on_zone_update: Optional[Callable[[str], None]] = None
        self._reconnect_delay = 5

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_zone_update_callback(self, callback: Callable[[str], None]) -> None:
        """
        Встановлює callback що викликається при оновленні зон.
        callback(camera_id) → ZoneManager.invalidate(camera_id)
        """
        self._on_zone_update = callback

    async def connect(self) -> None:
        """Підключається до RabbitMQ з retry."""
        while True:
            try:
                await self._do_connect()
                return
            except Exception as e:
                logger.warning(
                    f"RabbitMQ connection failed: {e}. "
                    f"Retry in {self._reconnect_delay}s"
                )
                await asyncio.sleep(self._reconnect_delay)

    async def _do_connect(self) -> None:
        try:
            import aio_pika
        except ImportError:
            logger.error("aio_pika not installed: pip install aio_pika")
            return

        self._connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            reconnect_interval=self._reconnect_delay,
        )

        # Publish channel — для відправки подій
        self._publish_channel = await self._connection.channel()
        await self._publish_channel.declare_exchange(
            settings.EVENTS_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        # Consume channel — для отримання zone-updates
        self._consume_channel = await self._connection.channel()
        await self._consume_channel.set_qos(prefetch_count=10)

        zones_exchange = await self._consume_channel.declare_exchange(
            settings.ZONES_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        # Ексклюзивна черга (тільки для цього instance AI сервісу)
        queue = await self._consume_channel.declare_queue(
            "", exclusive=True, auto_delete=True
        )
        # Підписуємось на всі zone-updates
        await queue.bind(zones_exchange, routing_key="zones.updated.#")

        await queue.consume(self._on_zone_message)

        self._connected = True
        logger.info("RabbitMQ connected")

    async def disconnect(self) -> None:
        if self._connection:
            await self._connection.close()
        self._connected = False
        logger.info("RabbitMQ disconnected")

    async def publish_event(self, event: SecurityEvent) -> bool:
        """
        Публікує SecurityEvent в exchange security.events.
        Routing key: events.{event_type}.{camera_id}
        Returns True якщо успішно.
        """
        if not self._connected or self._publish_channel is None:
            logger.warning("RabbitMQ not connected, dropping event")
            return False
        try:
            import aio_pika
            exchange = await self._publish_channel.get_exchange(
                settings.EVENTS_EXCHANGE
            )
            body = event.model_dump_json().encode()
            await exchange.publish(
                aio_pika.Message(
                    body=body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                    headers={
                        "event_type": event.event_type,
                        "camera_id": event.camera_id,
                        "risk_level": event.risk_level,
                    },
                ),
                routing_key=event.routing_key,
            )
            return True
        except Exception:
            logger.exception(f"Failed to publish event {event.event_id}")
            return False

    async def publish_events(self, events: list[SecurityEvent]) -> int:
        """Публікує список подій. Повертає кількість успішно відправлених."""
        count = 0
        for event in events:
            if await self.publish_event(event):
                count += 1
        return count

    async def _on_zone_message(self, message) -> None:
        """Отримали zones.updated.{camera_id} → інвалідуємо кеш."""
        try:
            async with message.process():
                data = json.loads(message.body)
                msg = ZoneUpdateMessage(**data)
                camera_id = msg.camera_id

                logger.info(
                    f"Zone update received: camera={camera_id} action={msg.action}"
                )

                if self._on_zone_update:
                    self._on_zone_update(camera_id)

        except Exception:
            logger.exception("Error processing zone update message")


rabbitmq_service = RabbitMQService()
