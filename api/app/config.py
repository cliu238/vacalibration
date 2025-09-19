#!/usr/bin/env python3
"""
Configuration settings for VA-Calibration API job management
"""

import os
from pydantic import BaseSettings, Field
from typing import Optional


class RedisConfig(BaseSettings):
    """Redis configuration for caching and job storage"""

    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = Field(default=0, env="REDIS_DB")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    ssl: bool = Field(default=False, env="REDIS_SSL")
    max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")

    @property
    def url(self) -> str:
        """Get Redis connection URL"""
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class CeleryConfig(BaseSettings):
    """Celery configuration for background job processing"""

    broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    task_serializer: str = Field(default="json", env="CELERY_TASK_SERIALIZER")
    result_serializer: str = Field(default="json", env="CELERY_RESULT_SERIALIZER")
    accept_content: list = Field(default=["json"], env="CELERY_ACCEPT_CONTENT")
    timezone: str = Field(default="UTC", env="CELERY_TIMEZONE")
    enable_utc: bool = Field(default=True, env="CELERY_ENABLE_UTC")

    # Task routing and execution
    task_routes: dict = Field(default={
        "api.app.job_endpoints.run_calibration_task": {"queue": "calibration"}
    })

    # Worker configuration
    worker_prefetch_multiplier: int = Field(default=1, env="CELERY_WORKER_PREFETCH_MULTIPLIER")
    task_acks_late: bool = Field(default=True, env="CELERY_TASK_ACKS_LATE")
    worker_max_tasks_per_child: int = Field(default=1000, env="CELERY_WORKER_MAX_TASKS_PER_CHILD")

    # Task timeouts
    task_soft_time_limit: int = Field(default=7200, env="CELERY_TASK_SOFT_TIME_LIMIT")  # 2 hours
    task_time_limit: int = Field(default=7800, env="CELERY_TASK_TIME_LIMIT")  # 2.17 hours


class JobConfig(BaseSettings):
    """Job management configuration"""

    # Cache settings
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    max_log_entries: int = Field(default=1000, env="MAX_LOG_ENTRIES")

    # Batch processing
    batch_max_size: int = Field(default=50, env="BATCH_MAX_SIZE")
    default_parallel_limit: int = Field(default=5, env="DEFAULT_PARALLEL_LIMIT")

    # Job timeouts
    default_timeout_minutes: int = Field(default=30, env="DEFAULT_TIMEOUT_MINUTES")
    max_timeout_minutes: int = Field(default=120, env="MAX_TIMEOUT_MINUTES")

    # Retry settings
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay: int = Field(default=60, env="RETRY_DELAY")  # seconds

    # Priority settings
    min_priority: int = Field(default=1, env="MIN_PRIORITY")
    max_priority: int = Field(default=10, env="MAX_PRIORITY")
    default_priority: int = Field(default=5, env="DEFAULT_PRIORITY")


class APIConfig(BaseSettings):
    """API server configuration"""

    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=False, env="API_DEBUG")

    # CORS settings
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    cors_methods: list = Field(default=["*"], env="CORS_METHODS")
    cors_headers: list = Field(default=["*"], env="CORS_HEADERS")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=False, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds


class RConfig(BaseSettings):
    """R environment configuration"""

    r_executable: str = Field(default="Rscript", env="R_EXECUTABLE")
    r_timeout: int = Field(default=3600, env="R_TIMEOUT")  # seconds

    # Data paths
    data_dir: str = Field(default="../data", env="DATA_DIR")
    temp_dir: Optional[str] = Field(default=None, env="TEMP_DIR")

    # Package requirements
    required_packages: list = Field(default=["vacalibration", "jsonlite"])


class AppConfig(BaseSettings):
    """Main application configuration"""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Service configurations
    redis: RedisConfig = RedisConfig()
    celery: CeleryConfig = CeleryConfig()
    jobs: JobConfig = JobConfig()
    api: APIConfig = APIConfig()
    r: RConfig = RConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global configuration instance
config = AppConfig()


def get_redis_config() -> RedisConfig:
    """Get Redis configuration"""
    return config.redis


def get_celery_config() -> CeleryConfig:
    """Get Celery configuration"""
    return config.celery


def get_job_config() -> JobConfig:
    """Get job management configuration"""
    return config.jobs


def get_api_config() -> APIConfig:
    """Get API configuration"""
    return config.api


def get_r_config() -> RConfig:
    """Get R configuration"""
    return config.r


def get_app_config() -> AppConfig:
    """Get complete application configuration"""
    return config


# Environment-specific configurations
def is_development() -> bool:
    """Check if running in development environment"""
    return config.environment.lower() in ["development", "dev"]


def is_production() -> bool:
    """Check if running in production environment"""
    return config.environment.lower() in ["production", "prod"]


def is_testing() -> bool:
    """Check if running in testing environment"""
    return config.environment.lower() in ["testing", "test"]


# Configuration validation
def validate_config():
    """Validate configuration settings"""
    errors = []

    # Validate Redis connection
    try:
        import redis
        r = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            socket_connect_timeout=5
        )
        r.ping()
    except Exception as e:
        errors.append(f"Redis connection failed: {e}")

    # Validate R environment
    import subprocess
    try:
        result = subprocess.run(
            [config.r.r_executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            errors.append("R executable not found or not working")
    except Exception as e:
        errors.append(f"R validation failed: {e}")

    # Validate required packages
    try:
        check_cmd = [
            config.r.r_executable, "-e",
            f"if(!all(sapply(c{tuple(config.r.required_packages)}, require, quietly=TRUE, character.only=TRUE))) stop('Missing packages')"
        ]
        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            errors.append(f"R packages missing: {result.stderr}")
    except Exception as e:
        errors.append(f"R package validation failed: {e}")

    # Validate data directory
    if not os.path.exists(config.r.data_dir):
        errors.append(f"Data directory not found: {config.r.data_dir}")

    return errors


if __name__ == "__main__":
    # Print current configuration
    print("VA-Calibration API Configuration")
    print("=" * 40)
    print(f"Environment: {config.environment}")
    print(f"Redis: {config.redis.host}:{config.redis.port}")
    print(f"Celery Broker: {config.celery.broker_url}")
    print(f"API: {config.api.host}:{config.api.port}")
    print(f"R Executable: {config.r.r_executable}")
    print(f"Data Directory: {config.r.data_dir}")

    # Validate configuration
    print("\nValidating configuration...")
    errors = validate_config()

    if errors:
        print("✗ Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ Configuration is valid")