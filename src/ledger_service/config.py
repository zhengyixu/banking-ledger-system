from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads from environment variables, falling back to .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://ledger:ledger@localhost:5455/ledger"
    test_database_url: str = "postgresql+psycopg://ledger:ledger@localhost:5455/ledger_test"


settings = Settings()
