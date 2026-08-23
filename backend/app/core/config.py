"""Application configuration, loaded from environment variables / .env file."""
from __future__ import annotations

from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The exact placeholder shipped in .env.example. If this value is still in use outside
# development, startup fails rather than silently running with a guessable secret - the same
# lesson PropertyManager learned as a CRITICAL finding during its Prompt 27 security audit
# (that project's default JWT secret was the public placeholder with nothing stopping it
# running in production). Built in from day one here instead of retrofitted after deployment,
# per PROJECT_PLAN.md §12.2.
PLACEHOLDER_JWT_SECRET = "CHANGE_ME_INSECURE_DEFAULT_FOR_DEV_ONLY"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    # Explicit False default - PropertyManager's Prompt 27 audit found this defaulting True,
    # which enables SQLAlchemy's echo=True and logs full SQL + bound params (including tenant
    # PII) to stdout.
    APP_DEBUG: bool = False

    JWT_SECRET_KEY: str = PLACEHOLDER_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DB_SERVER: str
    DB_NAME: str = "InspectIQDb"
    DB_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_TRUSTED_CONNECTION: bool = True
    DB_USER: str | None = None
    DB_PASSWORD: str | None = None

    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.APP_ENV != "development" and (
            self.JWT_SECRET_KEY == PLACEHOLDER_JWT_SECRET or len(self.JWT_SECRET_KEY) < 32
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be a real, sufficiently long secret when APP_ENV is not "
                "'development'. Refusing to start with the placeholder or a short value."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.DB_TRUSTED_CONNECTION:
            odbc_str = (
                f"DRIVER={{{self.DB_DRIVER}}};SERVER={self.DB_SERVER};DATABASE={self.DB_NAME};"
                f"Trusted_Connection=yes;"
            )
        else:
            # Encrypt=yes is required for a SQL-auth connection to a real SQL Server (the
            # Windows-trusted-connection branch above doesn't need it) - PropertyManager's
            # deployment session found exactly this gap the hard way. Built in from the start
            # here instead of relearning it.
            odbc_str = (
                f"DRIVER={{{self.DB_DRIVER}}};SERVER={self.DB_SERVER};DATABASE={self.DB_NAME};"
                f"UID={self.DB_USER};PWD={self.DB_PASSWORD};Encrypt=yes;"
            )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"


settings = Settings()
