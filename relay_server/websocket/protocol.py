"""
Hermes Relay - WebSocket 协议
定义 WebSocket 通信的消息格式
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class MessageType(str, Enum):
    """消息类型"""
    # 连接管理
    REGISTER = "register"          # 设备注册
    REGISTER_ACK = "register_ack"  # 注册确认
    
    # 心跳
    HEARTBEAT = "heartbeat"        # 心跳请求
    PONG = "pong"                  # 心跳响应
    
    # 命令
    COMMAND = "command"            # 命令下发
    RESPONSE = "response"          # 命令响应
    
    # 审批
    APPROVAL = "approval"          # 审批通知
    APPROVAL_RESULT = "approval_result"  # 审批结果
    
    # 设备管理
    DEVICE_LIST = "device_list"    # 设备列表
    DEVICE_STATUS = "device_status"  # 设备状态
    
    # 控制
    CANCEL = "cancel"              # 取消命令
    INTERRUPT = "interrupt"        # 中断执行
    
    # 文件传输
    FILE_START = "file_start"      # 文件传输开始
    FILE_DATA = "file_data"        # 文件数据
    FILE_END = "file_end"          # 文件传输结束
    
    # 系统
    ACK = "ack"                    # 确认
    ERROR = "error"                # 错误
    PING = "ping"                  # Ping


@dataclass
class WSMessage:
    """WebSocket 消息"""
    type: MessageType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "id": self.id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WSMessage':
        """从字典创建"""
        return cls(
            type=MessageType(data.get("type", "error")),
            id=data.get("id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            payload=data.get("payload", {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WSMessage':
        """从 JSON 字符串创建"""
        return cls.from_dict(json.loads(json_str))


class WSProtocol:
    """WebSocket 协议工具类"""
    
    @staticmethod
    def create_register_message(
        device_id: str,
        device_name: str,
        device_group: str = "default",
        os_version: str = "",
        ip_address: str = "",
        capabilities: Optional[List[str]] = None,
        auth_token: str = "",
    ) -> WSMessage:
        """创建设备注册消息"""
        return WSMessage(
            type=MessageType.REGISTER,
            payload={
                "device_id": device_id,
                "device_name": device_name,
                "device_group": device_group,
                "os_version": os_version,
                "ip_address": ip_address,
                "capabilities": capabilities or ["command", "screenshot"],
                "auth_token": auth_token,
            }
        )
    
    @staticmethod
    def create_register_ack(
        device_id: str,
        status: str = "ok",
        server_time: Optional[float] = None,
    ) -> WSMessage:
        """创建注册确认消息"""
        return WSMessage(
            type=MessageType.REGISTER_ACK,
            payload={
                "device_id": device_id,
                "status": status,
                "server_time": server_time or time.time(),
            }
        )
    
    @staticmethod
    def create_heartbeat_message(
        device_id: str,
        device_name: str = "",
        device_group: str = "",
        cpu_usage: float = 0.0,
        memory_usage: float = 0.0,
        disk_usage: float = 0.0,
        uptime: float = 0.0,
        active_commands: int = 0,
    ) -> WSMessage:
        """创建心跳消息"""
        return WSMessage(
            type=MessageType.HEARTBEAT,
            payload={
                "device_id": device_id,
                "device_name": device_name,
                "device_group": device_group,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": disk_usage,
                "uptime": uptime,
                "active_commands": active_commands,
            }
        )
    
    @staticmethod
    def create_command_message(
        command_id: str,
        command: str,
        working_dir: str = "",
        timeout: int = 30,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> WSMessage:
        """创建命令消息"""
        return WSMessage(
            type=MessageType.COMMAND,
            payload={
                "command_id": command_id,
                "command": command,
                "working_dir": working_dir,
                "timeout": timeout,
                "env_vars": env_vars or {},
            }
        )
    
    @staticmethod
    def create_response_message(
        command_id: str,
        status: str = "success",
        output: str = "",
        error_output: str = "",
        exit_code: Optional[int] = None,
        execution_time: float = 0.0,
    ) -> WSMessage:
        """创建响应消息"""
        return WSMessage(
            type=MessageType.RESPONSE,
            payload={
                "command_id": command_id,
                "status": status,
                "output": output,
                "error_output": error_output,
                "exit_code": exit_code,
                "execution_time": execution_time,
            }
        )
    
    @staticmethod
    def create_approval_message(
        approval_id: str,
        command: str,
        device_id: str,
        device_name: str = "",
        risk_level: str = "medium",
        reason: str = "",
    ) -> WSMessage:
        """创建审批消息"""
        return WSMessage(
            type=MessageType.APPROVAL,
            payload={
                "approval_id": approval_id,
                "command": command,
                "device_id": device_id,
                "device_name": device_name,
                "risk_level": risk_level,
                "reason": reason,
            }
        )
    
    @staticmethod
    def create_approval_result(
        approval_id: str,
        approved: bool,
        approver: str = "",
    ) -> WSMessage:
        """创建审批结果消息"""
        return WSMessage(
            type=MessageType.APPROVAL_RESULT,
            payload={
                "approval_id": approval_id,
                "approved": approved,
                "approver": approver,
            }
        )
    
    @staticmethod
    def create_cancel_message(command_id: str) -> WSMessage:
        """创建取消命令消息"""
        return WSMessage(
            type=MessageType.CANCEL,
            payload={
                "command_id": command_id,
            }
        )
    
    @staticmethod
    def create_error_message(
        error_code: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> WSMessage:
        """创建错误消息"""
        return WSMessage(
            type=MessageType.ERROR,
            payload={
                "error_code": error_code,
                "error_message": error_message,
                "details": details or {},
            }
        )
    
    @staticmethod
    def create_ack_message(
        reference_id: str,
        status: str = "ok",
    ) -> WSMessage:
        """创建确认消息"""
        return WSMessage(
            type=MessageType.ACK,
            payload={
                "reference_id": reference_id,
                "status": status,
            }
        )
    
    @staticmethod
    def create_ping_message() -> WSMessage:
        """创建 Ping 消息"""
        return WSMessage(
            type=MessageType.PING,
            payload={
                "timestamp": time.time(),
            }
        )
    
    @staticmethod
    def create_pong_message(timestamp: float) -> WSMessage:
        """创建 Pong 消息"""
        return WSMessage(
            type=MessageType.PONG,
            payload={
                "timestamp": timestamp,
                "server_time": time.time(),
            }
        )
