from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    DEBUG: bool = False
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "hospitana_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    SECRET_KEY: str = "change-this-in-production"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = '["http://localhost:3000","http://localhost:3001"]'

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def origins(self) -> List[str]:
        return json.loads(self.ALLOWED_ORIGINS)

    class Config:
        env_file = ".env"


settings = Settings()
