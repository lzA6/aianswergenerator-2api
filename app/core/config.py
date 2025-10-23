# aianswergenerator-2api/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "aianswergenerator-2api"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "一个将 aianswergenerator.pro 的后端 API (pollinations.ai) 转换为兼容 OpenAI 格式的代理。"

    API_MASTER_KEY: Optional[str] = "1"
    
    API_REQUEST_TIMEOUT: int = 120
    NGINX_PORT: int = 8090

    # 伪流式输出的字间延迟（秒）
    PSEUDO_STREAM_DELAY: float = 0.01

    DEFAULT_MODEL: str = "aianswergenerator-openai"
    KNOWN_MODELS: List[str] = ["aianswergenerator-openai"]
    UPSTREAM_MODEL_PARAM: str = "openai"

settings = Settings()
