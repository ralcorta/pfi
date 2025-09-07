"""Configuration management for the ransomware sensor."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, validator


class ModelConfig(BaseModel):
    """Model configuration."""
    path: str = Field(..., description="Path to the trained model")
    input_shape: list[int] = Field(default=[10, 32, 32, 1], description="Model input shape")


class DetectionConfig(BaseModel):
    """Detection configuration."""
    threshold: float = Field(default=0.80, ge=0.0, le=1.0, description="Detection threshold")
    window_size: int = Field(default=10, ge=1, description="Number of packets per window")
    packet_size: int = Field(default=1024, ge=1, description="Packet size for processing")


class CaptureConfig(BaseModel):
    """Packet capture configuration."""
    interface: str = Field(default="en0", description="Network interface")
    filter: str = Field(default="", description="BPF filter")
    timeout: float = Field(default=1.0, ge=0.1, description="Capture timeout in seconds")
    buffer_size: int = Field(default=1000, ge=100, description="Packet buffer size")


class SQSConfig(BaseModel):
    """AWS SQS configuration."""
    enabled: bool = Field(default=False, description="Enable SQS alerts")
    queue_url: str = Field(default="", description="SQS queue URL")
    region: str = Field(default="us-east-1", description="AWS region")


class SNSConfig(BaseModel):
    """AWS SNS configuration."""
    enabled: bool = Field(default=False, description="Enable SNS alerts")
    topic_arn: str = Field(default="", description="SNS topic ARN")
    region: str = Field(default="us-east-1", description="AWS region")


class AlertsConfig(BaseModel):
    """Alerts configuration."""
    stdout: bool = Field(default=True, description="Enable stdout alerts")
    sqs: SQSConfig = Field(default_factory=SQSConfig)
    sns: SNSConfig = Field(default_factory=SNSConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    file: str = Field(default="logs/sensor.log", description="Log file path")
    format: str = Field(default="json", description="Log format")
    max_size: str = Field(default="10MB", description="Maximum log file size")
    backup_count: int = Field(default=5, description="Number of backup files")


class PerformanceConfig(BaseModel):
    """Performance configuration."""
    max_memory_mb: int = Field(default=500, description="Maximum memory usage in MB")
    gc_interval: int = Field(default=1000, description="Garbage collection interval")
    batch_timeout: float = Field(default=5.0, description="Batch processing timeout")


class SensorConfig(BaseModel):
    """Main sensor configuration."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    @validator('model')
    def validate_model_path(cls, v):
        """Validate model path exists."""
        if not Path(v.path).exists():
            raise ValueError(f"Model file not found: {v.path}")
        return v

    @validator('logging')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v.level}")
        return v


def load_config(config_path: Optional[str] = None) -> SensorConfig:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Loaded configuration object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid
        ValueError: If config validation fails
    """
    if config_path is None:
        config_path = "configs/sensor.yaml"
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config_data = yaml.safe_load(f)
    
    return SensorConfig(**config_data)


def save_config(config: SensorConfig, config_path: str) -> None:
    """Save configuration to YAML file.
    
    Args:
        config: Configuration object to save
        config_path: Path to save configuration
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w') as f:
        yaml.dump(config.dict(), f, default_flow_style=False, indent=2)
