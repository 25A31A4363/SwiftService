import os
from pathlib import Path

# Root project paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = ROOT_DIR / "r5_operational.db"

class Settings:
    PROJECT_NAME: str = "R5 Operational Intelligence Platform"
    ROOT_DIR: Path = ROOT_DIR
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Database
    DATABASE_PATH: Path = DB_PATH
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "r5-super-secret-development-key-change-in-production-min-32-chars"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
