from sqlalchemy import create_engine
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    class Config:
        env_file = ".env"


settings = Settings()

engine = create_engine(settings.DATABASE_URL)

try:
    with engine.connect() as conn:
        print("Database connected successfully")
except Exception as e:
    print("Database connection failed")
    print(e)