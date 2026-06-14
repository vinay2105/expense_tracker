from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from pydantic_settings import BaseSettings
from sqlalchemy.orm import declarative_base, sessionmaker




from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()

engine = create_engine(settings.DATABASE_URL)

Base = declarative_base()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)