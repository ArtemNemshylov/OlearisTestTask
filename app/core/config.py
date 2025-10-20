from pydantic import BaseModel, Field
import os


class Settings(BaseModel):
    app_name: str = "Mini-CRM Repair Requests"
    secret_key: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "dev-secret"))
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@db:5432/app",
        )
    )
    env: str = os.getenv("ENV", "dev")
    oauth_client_id: str = os.getenv("OAUTH_CLIENT_ID", "crm-client")
    oauth_client_secret: str = os.getenv("OAUTH_CLIENT_SECRET", "crm-secret")


settings = Settings()


