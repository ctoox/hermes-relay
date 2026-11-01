"""
Hermes Relay - 配置模块
加载和管理配置
"""

from __future__ import annotations

import os
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeishuConfig:
    """飞书配置"""
    app_id: str = ""
    app_secret: str = ""
    domain: str = "feishu"
    encrypt_key: str = ""
    verification_token: str = ""


@dataclass
class RelayConfig:
    """中转站配置"""
    # WebSocket 配置
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765
    
    # 飞书配置
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    
    # 设备管理
    heartbeat_timeout: int = 60
    
    # 审批配置
    approval_timeout: int = 300
    
    # 日志配置
    log_level: str = "INFO"
    
    # 安全配置
    auth_token: str = ""
    enable_encryption: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "ws_host": self.ws_host,
            "ws_port": self.ws_port,
            "feishu": {
                "app_id": self.feishu.app_id,
                "app_secret": self.feishu.app_secret,
                "domain": self.feishu.domain,
            },
            "heartbeat_timeout": self.heartbeat_timeout,
            "approval_timeout": self.approval_timeout,
            "log_level": self.log_level,
        }


def load_config(config_path: Optional[str] = None) -> RelayConfig:
    """
    加载配置
    
    优先级: 配置文件 > 环境变量 > 默认值
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置对象
    """
    config = RelayConfig()
    
    # 从配置文件加载
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            _apply_dict(config, data)
            logger.info("Loaded config from %s", config_path)
        except Exception as e:
            logger.error("Failed to load config from %s: %s", config_path, e)
    
    # 从环境变量加载 (覆盖配置文件)
    _apply_env_vars(config)
    
    return config


def _apply_dict(config: RelayConfig, data: Dict[str, Any]) -> None:
    """从字典应用配置"""
    if "ws_host" in data:
        config.ws_host = data["ws_host"]
    if "ws_port" in data:
        config.ws_port = int(data["ws_port"])
    if "heartbeat_timeout" in data:
        config.heartbeat_timeout = int(data["heartbeat_timeout"])
    if "approval_timeout" in data:
        config.approval_timeout = int(data["approval_timeout"])
    if "log_level" in data:
        config.log_level = data["log_level"]
    if "auth_token" in data:
        config.auth_token = data["auth_token"]
    if "enable_encryption" in data:
        config.enable_encryption = bool(data["enable_encryption"])
    
    # 飞书配置
    feishu_data = data.get("feishu", {})
    if "app_id" in feishu_data:
        config.feishu.app_id = feishu_data["app_id"]
    if "app_secret" in feishu_data:
        config.feishu.app_secret = feishu_data["app_secret"]
    if "domain" in feishu_data:
        config.feishu.domain = feishu_data["domain"]
    if "encrypt_key" in feishu_data:
        config.feishu.encrypt_key = feishu_data["encrypt_key"]
    if "verification_token" in feishu_data:
        config.feishu.verification_token = feishu_data["verification_token"]


def _apply_env_vars(config: RelayConfig) -> None:
    """从环境变量应用配置"""
    # WebSocket
    if os.getenv("RELAY_WS_HOST"):
        config.ws_host = os.getenv("RELAY_WS_HOST")
    if os.getenv("RELAY_WS_PORT"):
        config.ws_port = int(os.getenv("RELAY_WS_PORT"))
    
    # 飞书
    if os.getenv("FEISHU_APP_ID"):
        config.feishu.app_id = os.getenv("FEISHU_APP_ID")
    if os.getenv("FEISHU_APP_SECRET"):
        config.feishu.app_secret = os.getenv("FEISHU_APP_SECRET")
    if os.getenv("FEISHU_DOMAIN"):
        config.feishu.domain = os.getenv("FEISHU_DOMAIN")
    if os.getenv("FEISHU_ENCRYPT_KEY"):
        config.feishu.encrypt_key = os.getenv("FEISHU_ENCRYPT_KEY")
    if os.getenv("FEISHU_VERIFICATION_TOKEN"):
        config.feishu.verification_token = os.getenv("FEISHU_VERIFICATION_TOKEN")
    
    # 其他
    if os.getenv("RELAY_HEARTBEAT_TIMEOUT"):
        config.heartbeat_timeout = int(os.getenv("RELAY_HEARTBEAT_TIMEOUT"))
    if os.getenv("RELAY_APPROVAL_TIMEOUT"):
        config.approval_timeout = int(os.getenv("RELAY_APPROVAL_TIMEOUT"))
    if os.getenv("RELAY_LOG_LEVEL"):
        config.log_level = os.getenv("RELAY_LOG_LEVEL")
    if os.getenv("RELAY_AUTH_TOKEN"):
        config.auth_token = os.getenv("RELAY_AUTH_TOKEN")


def save_config(config: RelayConfig, config_path: str) -> bool:
    """
    保存配置到文件
    
    Args:
        config: 配置对象
        config_path: 配置文件路径
    
    Returns:
        是否保存成功
    """
    try:
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        logger.info("Saved config to %s", config_path)
        return True
    except Exception as e:
        logger.error("Failed to save config to %s: %s", config_path, e)
        return False
