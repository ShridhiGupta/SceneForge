from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI Service Configuration
    openai_api_key: Optional[str] = None
    stability_api_key: Optional[str] = None
    
    # Decision Engine Configuration
    decision_engine_enabled: bool = True
    decision_engine_min_retries: int = 1
    decision_engine_confidence_threshold: float = 0.7
    
    # File Storage
    upload_dir: str = "./uploads"
    max_file_size: str = "100MB"
    
    # Celery Configuration
    celery_broker_url: str
    celery_result_backend: str
    
    class Config:
        env_file = ".env"

settings = Settings()
