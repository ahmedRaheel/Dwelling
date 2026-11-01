from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_name: str = 'PropTech Intelligence API'
    environment: str = 'development'
    database_url: str = 'postgresql+asyncpg://proptech_app:local_app_password@localhost:5432/proptech'
    jwt_secret: str = Field(min_length=32)
    jwt_issuer: str = 'proptech-saas'
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    cors_origins: str = 'http://localhost:5173,http://localhost:8080'
    embeddings_enabled: bool = False
    embedding_model: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    min_training_samples: int = 20
    media_dir: str = './.media'
    max_property_photos: int = 24
    max_photo_upload_mb: int = 12

    @property
    def allowed_origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(',') if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
