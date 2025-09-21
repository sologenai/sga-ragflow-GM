"""
GraphRAG SDK Configuration Management

This module provides configuration management for the GraphRAG SDK,
including environment-based configuration, validation, and factory methods.

Author: RAGFlow Team
Version: 1.0.0
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 3600
    max_memory: str = "256mb"
    eviction_policy: str = "allkeys-lru"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    enabled: bool = True
    max_requests: int = 100
    window_seconds: int = 60
    burst_limit: int = 10


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: str = "10MB"
    backup_count: int = 5


@dataclass
class SecurityConfig:
    """Security configuration"""
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer"
    verify_ssl: bool = True
    timeout: int = 30
    max_connections: int = 100
    max_connections_per_host: int = 30


@dataclass
class GraphRAGConfig:
    """Main GraphRAG SDK configuration"""
    base_url: str
    api_key: str
    cache: CacheConfig = field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self.validate()
    
    def validate(self):
        """Validate configuration values"""
        if not self.base_url:
            raise ValueError("base_url is required")
        
        if not self.api_key:
            raise ValueError("api_key is required")
        
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("base_url must start with http:// or https://")
        
        if self.retry.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        
        if self.retry.initial_delay <= 0:
            raise ValueError("initial_delay must be > 0")
        
        if self.rate_limit.max_requests <= 0:
            raise ValueError("max_requests must be > 0")
        
        if self.rate_limit.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        
        if self.security.timeout <= 0:
            raise ValueError("timeout must be > 0")


class ConfigManager:
    """Configuration manager for GraphRAG SDK"""
    
    DEFAULT_CONFIG_PATHS = [
        "graphrag_config.json",
        "~/.graphrag/config.json",
        "/etc/graphrag/config.json"
    ]
    
    ENV_PREFIX = "GRAPHRAG_"
    
    @classmethod
    def from_env(cls) -> GraphRAGConfig:
        """Create configuration from environment variables"""
        env_config = {}
        
        # Basic configuration
        env_config['base_url'] = os.getenv(f"{cls.ENV_PREFIX}BASE_URL", "")
        env_config['api_key'] = os.getenv(f"{cls.ENV_PREFIX}API_KEY", "")
        
        # Cache configuration
        cache_config = {}
        cache_config['enabled'] = os.getenv(f"{cls.ENV_PREFIX}CACHE_ENABLED", "true").lower() == "true"
        cache_config['redis_url'] = os.getenv(f"{cls.ENV_PREFIX}REDIS_URL", "redis://localhost:6379")
        cache_config['default_ttl'] = int(os.getenv(f"{cls.ENV_PREFIX}CACHE_TTL", "3600"))
        
        # Rate limit configuration
        rate_limit_config = {}
        rate_limit_config['enabled'] = os.getenv(f"{cls.ENV_PREFIX}RATE_LIMIT_ENABLED", "true").lower() == "true"
        rate_limit_config['max_requests'] = int(os.getenv(f"{cls.ENV_PREFIX}RATE_LIMIT_MAX_REQUESTS", "100"))
        rate_limit_config['window_seconds'] = int(os.getenv(f"{cls.ENV_PREFIX}RATE_LIMIT_WINDOW", "60"))
        
        # Retry configuration
        retry_config = {}
        retry_config['max_retries'] = int(os.getenv(f"{cls.ENV_PREFIX}MAX_RETRIES", "3"))
        retry_config['initial_delay'] = float(os.getenv(f"{cls.ENV_PREFIX}INITIAL_DELAY", "1.0"))
        retry_config['backoff_factor'] = float(os.getenv(f"{cls.ENV_PREFIX}BACKOFF_FACTOR", "2.0"))
        
        # Logging configuration
        logging_config = {}
        logging_config['level'] = os.getenv(f"{cls.ENV_PREFIX}LOG_LEVEL", "INFO")
        logging_config['file_path'] = os.getenv(f"{cls.ENV_PREFIX}LOG_FILE")
        
        # Security configuration
        security_config = {}
        security_config['verify_ssl'] = os.getenv(f"{cls.ENV_PREFIX}VERIFY_SSL", "true").lower() == "true"
        security_config['timeout'] = int(os.getenv(f"{cls.ENV_PREFIX}TIMEOUT", "30"))
        
        return GraphRAGConfig(
            base_url=env_config['base_url'],
            api_key=env_config['api_key'],
            cache=CacheConfig(**cache_config),
            rate_limit=RateLimitConfig(**rate_limit_config),
            retry=RetryConfig(**retry_config),
            logging=LoggingConfig(**logging_config),
            security=SecurityConfig(**security_config)
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> GraphRAGConfig:
        """Create configuration from JSON file"""
        config_path = Path(config_path).expanduser()
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        
        return cls._create_config_from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> GraphRAGConfig:
        """Create configuration from dictionary"""
        return cls._create_config_from_dict(config_dict)
    
    @classmethod
    def auto_discover(cls) -> GraphRAGConfig:
        """Auto-discover configuration from multiple sources"""
        # Try environment variables first
        try:
            config = cls.from_env()
            if config.base_url and config.api_key:
                logger.info("Configuration loaded from environment variables")
                return config
        except Exception as e:
            logger.debug(f"Failed to load from environment: {e}")
        
        # Try configuration files
        for config_path in cls.DEFAULT_CONFIG_PATHS:
            try:
                config = cls.from_file(config_path)
                logger.info(f"Configuration loaded from file: {config_path}")
                return config
            except (FileNotFoundError, ValueError) as e:
                logger.debug(f"Failed to load from {config_path}: {e}")
                continue
        
        raise ValueError(
            "No valid configuration found. Please set environment variables or create a config file."
        )
    
    @classmethod
    def _create_config_from_dict(cls, config_data: Dict[str, Any]) -> GraphRAGConfig:
        """Create configuration from dictionary data"""
        # Extract nested configurations
        cache_data = config_data.get('cache', {})
        rate_limit_data = config_data.get('rate_limit', {})
        retry_data = config_data.get('retry', {})
        logging_data = config_data.get('logging', {})
        security_data = config_data.get('security', {})
        
        return GraphRAGConfig(
            base_url=config_data.get('base_url', ''),
            api_key=config_data.get('api_key', ''),
            cache=CacheConfig(**cache_data),
            rate_limit=RateLimitConfig(**rate_limit_data),
            retry=RetryConfig(**retry_data),
            logging=LoggingConfig(**logging_data),
            security=SecurityConfig(**security_data)
        )
    
    @staticmethod
    def save_config(config: GraphRAGConfig, config_path: str):
        """Save configuration to JSON file"""
        config_path = Path(config_path).expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = {
            'base_url': config.base_url,
            'api_key': config.api_key,
            'cache': {
                'enabled': config.cache.enabled,
                'redis_url': config.cache.redis_url,
                'default_ttl': config.cache.default_ttl,
                'max_memory': config.cache.max_memory,
                'eviction_policy': config.cache.eviction_policy
            },
            'rate_limit': {
                'enabled': config.rate_limit.enabled,
                'max_requests': config.rate_limit.max_requests,
                'window_seconds': config.rate_limit.window_seconds,
                'burst_limit': config.rate_limit.burst_limit
            },
            'retry': {
                'max_retries': config.retry.max_retries,
                'initial_delay': config.retry.initial_delay,
                'backoff_factor': config.retry.backoff_factor,
                'max_delay': config.retry.max_delay
            },
            'logging': {
                'level': config.logging.level,
                'format': config.logging.format,
                'file_path': config.logging.file_path,
                'max_file_size': config.logging.max_file_size,
                'backup_count': config.logging.backup_count
            },
            'security': {
                'api_key_header': config.security.api_key_header,
                'api_key_prefix': config.security.api_key_prefix,
                'verify_ssl': config.security.verify_ssl,
                'timeout': config.security.timeout,
                'max_connections': config.security.max_connections,
                'max_connections_per_host': config.security.max_connections_per_host
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration saved to: {config_path}")


def setup_logging(config: LoggingConfig):
    """Setup logging based on configuration"""
    import logging.handlers
    
    # Set logging level
    level = getattr(logging, config.level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(config.format)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if config.file_path:
        file_path = Path(config.file_path).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse max file size
        max_bytes = _parse_size(config.max_file_size)
        
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def _parse_size(size_str: str) -> int:
    """Parse size string like '10MB' to bytes"""
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)
