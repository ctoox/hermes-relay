"""
Hermes Relay - 消息工厂
提供创建各种消息的便捷方法
"""

from __future__ import annotations

import uuid
import platform
import socket
from typing import Any, Dict, List, Optional

from .protocol import (
    MessageType,
    Message,
    CommandMessage,
    ResponseMessage,
    HeartbeatMessage,
    RegisterMessage,
    ApprovalMessage,
    ApprovalResponse,
    ErrorMessage,
    CommandPriority,
    ApprovalAction,
    DeviceStatus,
)


def create_command(
    command: str,
    device_id: str = "",
    device_group: str = "",
    working_dir: str = "",
    timeout: int = 30,
    priority: CommandPriority = CommandPriority.NORMAL,
    requires_approval: bool = False,
    approval_id: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
    source: str = "relay",
) -> CommandMessage:
    """创建命令消息"""
    return CommandMessage(
        command=command,
        device_id=device_id,
        device_group=device_group,
        working_dir=working_dir,
        timeout=timeout,
        priority=priority,
        requires_approval=requires_approval,
        approval_id=approval_id,
        env_vars=env_vars or {},
        source=source,
        target=device_id,
    )


def create_response(
    command_id: str,
    status: str = "success",
    output: str = "",
    error_output: str = "",
    exit_code: Optional[int] = None,
    execution_time: float = 0.0,
    device_id: str = "",
    source: str = "agent",
) -> ResponseMessage:
    """创建响应消息"""
    return ResponseMessage(
        command_id=command_id,
        status=status,
        output=output,
        error_output=error_output,
        exit_code=exit_code,
        execution_time=execution_time,
        device_id=device_id,
        source=source,
        target="relay",
    )


def create_heartbeat(
    device_id: str,
    device_name: str = "",
    device_group: str = "default",
    cpu_usage: float = 0.0,
    memory_usage: float = 0.0,
    disk_usage: float = 0.0,
    uptime: float = 0.0,
    active_commands: int = 0,
    source: str = "agent",
) -> HeartbeatMessage:
    """创建心跳消息"""
    return HeartbeatMessage(
        device_id=device_id,
        device_name=device_name,
        device_group=device_group,
        os_version=platform.platform(),
        ip_address=_get_local_ip(),
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        disk_usage=disk_usage,
        uptime=uptime,
        active_commands=active_commands,
        source=source,
        target="relay",
    )


def create_register(
    device_id: str,
    device_name: str,
    device_group: str = "default",
    capabilities: Optional[List[str]] = None,
    auth_token: str = "",
    source: str = "agent",
) -> RegisterMessage:
    """创建设备注册消息"""
    return RegisterMessage(
        device_id=device_id,
        device_name=device_name,
        device_group=device_group,
        os_version=platform.platform(),
        ip_address=_get_local_ip(),
        mac_address=_get_mac_address(),
        hostname=socket.gethostname(),
        capabilities=capabilities or ["command", "screenshot", "file_transfer"],
        auth_token=auth_token,
        source=source,
        target="relay",
    )


def create_approval_request(
    command: str,
    device_id: str,
    device_name: str = "",
    risk_level: str = "medium",
    reason: str = "",
    timeout: int = 300,
    source: str = "relay",
) -> ApprovalMessage:
    """创建审批请求"""
    approval_id = str(uuid.uuid4())
    preview = command[:200] + "..." if len(command) > 200 else command
    
    return ApprovalMessage(
        approval_id=approval_id,
        command=command,
        command_preview=preview,
        device_id=device_id,
        device_name=device_name,
        risk_level=risk_level,
        reason=reason,
        timeout=timeout,
        source=source,
        target="feishu",
    )


def create_approval_response(
    approval_id: str,
    action: ApprovalAction,
    approver: str = "",
    reason: str = "",
    source: str = "feishu",
) -> ApprovalResponse:
    """创建审批响应"""
    return ApprovalResponse(
        approval_id=approval_id,
        action=action,
        approver=approver,
        reason=reason,
        source=source,
        target="relay",
    )


def create_error(
    error_code: str,
    error_message: str,
    details: Optional[Dict[str, Any]] = None,
    original_message_id: str = "",
    source: str = "relay",
    target: str = "",
) -> ErrorMessage:
    """创建错误消息"""
    return ErrorMessage(
        error_code=error_code,
        error_message=error_message,
        details=details,
        original_message_id=original_message_id,
        source=source,
        target=target,
    )


def _get_local_ip() -> str:
    """获取本地IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _get_mac_address() -> str:
    """获取MAC地址"""
    try:
        mac = uuid.getnode()
        return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(0, 48, 8))
    except Exception:
        return "00:00:00:00:00:00"
