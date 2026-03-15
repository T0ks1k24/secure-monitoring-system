import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from schemas.events import SecurityEvent, EventType, RiskLevel, ZoneUpdateMessage
from config.settings import settings
from services.rabbitmq_service import RabbitMQService

@pytest.fixture
def rabbitmq_service():
    return RabbitMQService()

@pytest.fixture
def mock_aio_pika():
    with patch("aio_pika.connect_robust") as mock_connect_robust:
        mock_connection = AsyncMock()
        mock_publish_channel = AsyncMock()
        mock_consume_channel = AsyncMock()
        
        mock_connect_robust.return_value = mock_connection
        mock_connection.channel.side_effect = [mock_publish_channel, mock_consume_channel]
        
        mock_exchange = AsyncMock()
        mock_publish_channel.declare_exchange.return_value = mock_exchange
        mock_publish_channel.get_exchange.return_value = mock_exchange
        
        mock_consume_exchange = AsyncMock()
        mock_consume_channel.declare_exchange.return_value = mock_consume_exchange
        
        mock_queue = AsyncMock()
        mock_consume_channel.declare_queue.return_value = mock_queue
        
        yield {
            "connect_robust": mock_connect_robust,
            "connection": mock_connection,
            "publish_channel": mock_publish_channel,
            "consume_channel": mock_consume_channel,
            "exchange": mock_exchange,
            "queue": mock_queue,
        }

def test_initial_state(rabbitmq_service):
    assert rabbitmq_service.is_connected is False
    assert rabbitmq_service._on_zone_update is None

def test_set_zone_update_callback(rabbitmq_service):
    callback = MagicMock()
    rabbitmq_service.set_zone_update_callback(callback)
    assert rabbitmq_service._on_zone_update == callback

@pytest.mark.asyncio
async def test_connect_disconnect(rabbitmq_service, mock_aio_pika):
    await rabbitmq_service._do_connect()
    assert rabbitmq_service.is_connected is True
    
    mock_aio_pika["connect_robust"].assert_called_once()
    mock_aio_pika["publish_channel"].declare_exchange.assert_called_once()
    mock_aio_pika["queue"].consume.assert_called_once()
    
    await rabbitmq_service.disconnect()
    assert rabbitmq_service.is_connected is False
    mock_aio_pika["connection"].close.assert_called_once()

@pytest.mark.asyncio
async def test_publish_event_when_disconnected(rabbitmq_service):
    event = SecurityEvent(
        event_id="test-1", camera_id="cam1", timestamp=123.0,
        event_type=EventType.PERSON_DETECTED, risk_level=RiskLevel.LOW
    )
    result = await rabbitmq_service.publish_event(event)
    assert result is False

@pytest.mark.asyncio
async def test_publish_event_success(rabbitmq_service, mock_aio_pika):
    await rabbitmq_service._do_connect()
    
    event = SecurityEvent(
        event_id="test-1", camera_id="cam1", timestamp=123.0,
        event_type=EventType.PERSON_DETECTED, risk_level=RiskLevel.LOW
    )
    
    result = await rabbitmq_service.publish_event(event)
    assert result is True
    
    mock_exchange = mock_aio_pika["exchange"]
    mock_exchange.publish.assert_called_once()
    
    # Check routing key
    call_args = mock_exchange.publish.call_args
    assert call_args.kwargs["routing_key"] == "events.person_detected.cam1"

@pytest.mark.asyncio
async def test_publish_events_batch(rabbitmq_service, mock_aio_pika):
    await rabbitmq_service._do_connect()
    
    events = [
        SecurityEvent(
            event_id=f"test-{i}", camera_id="cam1", timestamp=123.0,
            event_type=EventType.PERSON_DETECTED, risk_level=RiskLevel.LOW
        ) for i in range(3)
    ]
    
    count = await rabbitmq_service.publish_events(events)
    assert count == 3
    assert mock_aio_pika["exchange"].publish.call_count == 3

@pytest.mark.asyncio
async def test_on_zone_message(rabbitmq_service):
    callback = MagicMock()
    rabbitmq_service.set_zone_update_callback(callback)
    
    mock_message = MagicMock()
    mock_process_cm = AsyncMock()
    mock_message.process.return_value = mock_process_cm
    
    msg_data = {"camera_id": "cam1", "action": "reload"}
    mock_message.body = json.dumps(msg_data).encode()
    
    # Process the message
    await rabbitmq_service._on_zone_message(mock_message)
    
    mock_message.process.assert_called_once()
    callback.assert_called_once_with("cam1")

@pytest.mark.asyncio
async def test_on_zone_message_invalid_json(rabbitmq_service, caplog):
    callback = MagicMock()
    rabbitmq_service.set_zone_update_callback(callback)
    
    mock_message = AsyncMock()
    mock_message.body = b"invalid json"
    
    # Should not raise exception
    await rabbitmq_service._on_zone_message(mock_message)
    assert callback.call_count == 0
