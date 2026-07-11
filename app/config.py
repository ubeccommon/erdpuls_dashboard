"""
Erdpuls Collective Threshold Model - Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App
    app_name: str = "Erdpuls Collective Threshold"
    debug: bool = False
    base_url: str = "https://erdpuls.ubec.eu"

    # Path (outside the repo) for dashboard-created per-initiative folders.
    # Deploy-by-pull safe: never write into the version-controlled tree.
    initiatives_data_dir: str = "/srv/ubec/erdpuls-data/initiatives"
    
    # Database
    database_url: str = "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls"
    db_schema: str = "erdpuls_threshold"
    
    # Security
    secret_key: str = "change-this-in-production"
    
    # Token exchange rate (UBECrc per EUR)
    default_token_rate: float = 70.0  # 7 UBECrc = €0.10, so 70 UBECrc = €1.00
    
    # SMTP Email Settings
    smtp_host: str = "localhost"
    smtp_port: int = 465
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = False  # False for port 465 (implicit SSL)
    smtp_use_ssl: bool = True   # True for port 465
    smtp_from_email: str = "noreply@ubec.network"
    smtp_from_name: str = "Erdpuls"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()
