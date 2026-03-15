import asyncio
import sys
import os

# Add backend path to sys.path to resolve imports within the test
backend_path = os.path.abspath(os.path.join(os.getcwd(), "cloud/backend_service/backend"))
sys.path.append(backend_path)

from infrastructure.messaging.rabbitmq_client import rabbitmq_client
from core.config import settings

# Explicitly override RabbitMQ URL to localhost for host-based test
# Since we started RMQ via docker, it's mapped to localhost:5672
settings.RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"

async def test_publish():
    print(f"Testing RabbitMQ publication to {settings.RABBITMQ_URL}...")
    camera_id = "test_camera_uv"
    try:
        await rabbitmq_client.publish_zone_update(camera_id, action="reload")
        print(f"Successfully published update for {camera_id}")
    except Exception as e:
        print(f"Failed to publish: {e}")
        sys.exit(1)
    finally:
        await rabbitmq_client.close()

if __name__ == "__main__":
    asyncio.run(test_publish())
