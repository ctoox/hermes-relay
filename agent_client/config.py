"""
Hermes Relay - 被控端配置
"""

from __future__ import annotations

import os
import uuid
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """被控端配置"""
    # 设备信息
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_name: str = ""
    device_group: str = "default"
    
    # 服务端连接
    server_url: str = "ws://localhost:8765"
    auth_token: str = ""
    
    # 心跳配置
    heartbeat_interval: int = 30
    
    # 命令配置
    command_timeout: int = 60
    max_concurrent_commands: int = 5
    
    # 日志配置
    log_level: str = "INFO"
    
    # 重连配置
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 0  # 0 = 无限重试
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_group": self.device_group,
            "server_url": self.server_url,
            "heartbeat_interval": self.heartbeat_interval,
            "command_timeout": self.command_timeout,
            "max_concurrent_commands": self.max_concurrent_commands,
            "log_level": self.log_level,
        }


def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """
    加载配置
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置对象
    """
    config = AgentConfig()
    
    # 设置默认设备名称
    if not config.device_name:
        import socket
        config.device_name = socket.gethostname()
    
    # 从配置文件加载
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            _apply_dict(config, data)
            logger.info("Loaded config from %s", config_path)
        except Exception as e:
            logger.error("Failed to load config from %s: %s", config_path, e)
    
    # 从环境变量加载
    _apply_env_vars(config)
    
    # 确保 device_id 存在
    if not config.device_id:
        config.device_id = str(uuid.uuid4())
    
    return config


def _apply_dict(config: AgentConfig, data: Dict[str, Any]) -> None:
    """从字典应用配置"""
    if "device_id" in data:
        config.device_id = data["device_id"]
    if "device_name" in data:
        config.device_name = data["device_name"]
    if "device_group" in data:
        config.device_group = data["device_group"]
    if "server_url" in data:
        config.server_url = data["server_url"]
    if "auth_token" in data:
        config.auth_token = data["auth_token"]
    if "heartbeat_interval" in data:
        config.heartbeat_interval = int(data["heartbeat_interval"])
    if "command_timeout" in data:
        config.command_timeout = int(data["command_timeout"])
    if "max_concurrent_commands" in data:
        config.max_concurrent_commands = int(data["max_concurrent_commands"])
    if "log_level" in data:
        config.log_level = data["log_level"]
    if "reconnect_interval" in data:
        config.reconnect_interval = int(data["reconnect_interval"])
    if "max_reconnect_attempts" in data:
        config.max_reconnect_attempts = int(data["max_reconnect_attempts"])


def _apply_env_vars(config: AgentConfig) -> None:
    """从环境变量应用配置"""
    if os.getenv("RELAY_DEVICE_ID"):
        config.device_id = os.getenv("RELAY_DEVICE_ID")
    if os.getenv("RELAY_DEVICE_NAME"):
        config.device_name = os.getenv("RELAY_DEVICE_NAME")
    if os.getenv("RELAY_DEVICE_GROUP"):
        config.device_group = os.getenv("RELAY_DEVICE_GROUP")
    if os.getenv("RELAY_SERVER_URL"):
        config.server_url = os.getenv("RELAY_SERVER_URL")
    if os.getenv("RELAY_AUTH_TOKEN"):
        config.auth_token = os.getenv("RELAY_AUTH_TOKEN")
    if os.getenv("RELAY_HEARTBEAT_INTERVAL"):
        config.heartbeat_interval = int(os.getenv("RELAY_HEARTBEAT_INTERVAL"))
    if os.getenv("RELAY_COMMAND_TIMEOUT"):
        config.command_timeout = int(os.getenv("RELAY_COMMAND_TIMEOUT"))
    if os.getenv("RELAY_LOG_LEVEL"):
        config.log_level = os.getenv("RELAY_LOG_LEVEL")


def save_config(config: AgentConfig, config_path: str) -> bool:
    """保存配置到文件"""
    try:
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        logger.info("Saved config to %s", config_path)
        return True
    except Exception as e:
        logger.error("Failed to save config to %s: %s", config_path, e)
        return False
