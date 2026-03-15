from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    PROJECT_NAME: str = "Security Monitoring System"

    # DATABASE
    DATABASE_URL: str = "sqlite:///./local.db"

    # JWT
    JWT_SECRET: str = "SUPER_SECRET_KEY"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # REDIS
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # RABBITMQ
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    ZONES_EXCHANGE: str = "security.zones"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


settings = Settings()
