"""
Configuration - 配置管理
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # Redis 配置
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # 服务配置
    service_port: int = int(os.getenv("SERVICE_PORT", "8080"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 记忆配置
    short_term_memory_size: int = int(os.getenv("SHORT_TERM_MEMORY_SIZE", "20"))
    retrieve_top_n: int = int(os.getenv("RETRIEVE_TOP_N", "5"))
    summary_max_tags: int = int(os.getenv("SUMMARY_MAX_TAGS", "30"))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
