from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./pukankov.db"
    environment: str = "development"
    public_origin: str = "http://127.0.0.1:5173"
    hold_seconds: int = 300
    max_seats: int = 8
    payment_mode: str = "simulation"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
