from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI-PS Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_NAME: str = "ai_ps_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # WhatsApp Green API
    GREEN_API_INSTANCE_ID: str = ""
    GREEN_API_TOKEN: str = ""
    GREEN_API_BASE_URL: str = "https://api.green-api.com"

   # Remove Green API fields, add these:
    TWILIO_ACCOUNT_SID: str = "AC6002243f9f44b4306e22cc64eaf2d40c"
    TWILIO_AUTH_TOKEN: str = "5702fb61acc0a206fc92be0e05e10563"
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"

    # OpenAI
    OPENAI_API_KEY: str = "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"

    # Timing
    EOD_REMINDER_TIME: str = "17:45"
    EOD_DEADLINE_TIME: str = "18:00"
    EOD_SUMMARY_TIME: str = "19:00"
    DAILY_TODO_TIME: str = "07:00"




    # Super Admin
    SUPER_ADMIN_NAME: str = "Prakhar Bagora"
    SUPER_ADMIN_PHONE: str = "8827219873"
    SUPER_ADMIN_EMAIL: str = "prakhar@example.com"
    SUPER_ADMIN_PASSWORD: str = "Admin@123"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
