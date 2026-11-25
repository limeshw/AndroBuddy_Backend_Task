from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = "123456789987654321"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    DATABASE_URL: str = "sqlite:///./shopsphere.db"

    # seed credentials
    ADMIN_EMAIL: str = "admin@shopsphere.com"
    ADMIN_PASSWORD: str = "Admin123!"
    ADMIN_FULL_NAME: str = "System Admin"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

