"""
Hermes Relay - 通信协议定义
定义所有消息类型和数据结构
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union


class MessageType(str, Enum):
    """消息类型枚举"""
    # 命令相关
    COMMAND = "command"              # 执行命令
    RESPONSE = "response"            # 命令响应
    
    # 设备管理
    REGISTER = "register"            # 设备注册
    HEARTBEAT = "heartbeat"          # 心跳检测
    DEVICE_LIST = "device_list"      # 设备列表查询
    DEVICE_STATUS = "device_status"  # 设备状态
    
    # 审批相关
    APPROVAL_REQUEST = "approval_request"    # 审批请求
    APPROVAL_RESPONSE = "approval_response"  # 审批响应
    
    # 控制
    INTERRUPT = "interrupt"          # 中断命令
    CANCEL = "cancel"                # 取消操作
    
    # 文件传输
    FILE_UPLOAD = "file_upload"      # 文件上传
    FILE_DOWNLOAD = "file_download"  # 文件下载
    FILE_DATA = "file_data"          # 文件数据
    
    # 系统
    ERROR = "error"                  # 错误
    ACK = "ack"                      # 确认
    PING = "ping"                    # Ping
    PONG = "pong"                    # Pong


class DeviceStatus(str, Enum):
    """设备状态枚举"""
    ONLINE = "online"        # 在线
    OFFLINE = "offline"      # 离线
    BUSY = "busy"            # 忙碌 (执行命令中)
    ERROR = "error"          # 错误
    MAINTENANCE = "maintenance"  # 维护模式


class CommandPriority(str, Enum):
    """命令优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ApprovalAction(str, Enum):
    """审批动作"""
    ALLOW_ONCE = "allow_once"          # 允许一次
    ALLOW_SESSION = "allow_session"    # 本次会话允许
    ALLOW_ALWAYS = "allow_always"      # 永久允许
    DENY = "deny"                      # 拒绝


@dataclass
class Message:
    """基础消息类"""
    type: MessageType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    source: str = ""                   # 发送方标识
    target: str = ""                   # 目标方标识
    version: str = "1.0"               # 协议版本
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建"""
        data['type'] = MessageType(data['type'])
        return cls(**data)


@dataclass
class CommandMessage(Message):
    """命令消息"""
    type: MessageType = field(default=MessageType.COMMAND, init=False)
    command: str = ""                  # 要执行的命令
    working_dir: str = ""              # 工作目录
    timeout: int = 30                  # 超时时间(秒)
    priority: CommandPriority = field(default=CommandPriority.NORMAL)
    requires_approval: bool = False    # 是否需要审批
    approval_id: Optional[str] = None  # 审批ID
    env_vars: Dict[str, str] = field(default_factory=dict)  # 环境变量
    device_id: str = ""                # 目标设备ID
    device_group: str = ""             # 目标设备组
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['priority'] = self.priority.value
        return data


@dataclass
class ResponseMessage(Message):
    """响应消息"""
    type: MessageType = field(default=MessageType.RESPONSE, init=False)
    command_id: str = ""               # 对应的命令ID
    status: str = "success"            # success/error/timeout/cancelled
    output: str = ""                   # 命令输出
    error_output: str = ""             # 错误输出
    exit_code: Optional[int] = None    # 退出码
    execution_time: float = 0.0        # 执行时间(秒)
    device_id: str = ""                # 执行设备ID


@dataclass
class HeartbeatMessage(Message):
    """心跳消息"""
    type: MessageType = field(default=MessageType.HEARTBEAT, init=False)
    device_id: str = ""                # 设备ID
    device_name: str = ""              # 设备名称
    device_group: str = ""             # 设备组
    os_version: str = ""               # 操作系统版本
    ip_address: str = ""               # IP地址
    cpu_usage: float = 0.0             # CPU使用率
    memory_usage: float = 0.0          # 内存使用率
    disk_usage: float = 0.0            # 磁盘使用率
    uptime: float = 0.0                # 运行时间(秒)
    active_commands: int = 0           # 活跃命令数


@dataclass
class RegisterMessage(Message):
    """设备注册消息"""
    type: MessageType = field(default=MessageType.REGISTER, init=False)
    device_id: str = ""                # 设备ID (UUID)
    device_name: str = ""              # 设备名称 (用户自定义)
    device_group: str = "default"      # 设备组
    os_version: str = ""               # 操作系统版本
    ip_address: str = ""               # IP地址
    mac_address: str = ""              # MAC地址
    hostname: str = ""                 # 主机名
    capabilities: List[str] = field(default_factory=list)  # 支持的能力
    auth_token: str = ""               # 认证令牌


@dataclass
class ApprovalMessage(Message):
    """审批请求消息"""
    type: MessageType = field(default=MessageType.APPROVAL_REQUEST, init=False)
    approval_id: str = ""              # 审批ID
    command: str = ""                  # 待审批的命令
    command_preview: str = ""          # 命令预览 (截断)
    device_id: str = ""                # 目标设备
    device_name: str = ""              # 设备名称
    risk_level: str = "medium"         # 风险等级: low/medium/high/critical
    reason: str = ""                   # 审批原因
    timeout: int = 300                 # 审批超时(秒)


@dataclass
class ApprovalResponse(Message):
    """审批响应消息"""
    type: MessageType = field(default=MessageType.APPROVAL_RESPONSE, init=False)
    approval_id: str = ""              # 审批ID
    action: ApprovalAction = field(default=ApprovalAction.DENY)
    approver: str = ""                 # 审批人
    reason: str = ""                   # 审批原因
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['action'] = self.action.value
        return data


@dataclass
class ErrorMessage(Message):
    """错误消息"""
    type: MessageType = field(default=MessageType.ERROR, init=False)
    error_code: str = ""               # 错误代码
    error_message: str = ""            # 错误信息
    details: Optional[Dict[str, Any]] = None  # 错误详情
    original_message_id: str = ""      # 原始消息ID


@dataclass
class FileTransferMessage(Message):
    """文件传输消息"""
    type: MessageType = field(default=MessageType.FILE_DATA, init=False)
    file_name: str = ""                # 文件名
    file_size: int = 0                 # 文件大小
    file_hash: str = ""                # 文件哈希
    chunk_index: int = 0               # 分片索引
    total_chunks: int = 1              # 总分片数
    data: str = ""                     # Base64编码的数据
    is_last_chunk: bool = True         # 是否最后一片


@dataclass
class DeviceListRequest(Message):
    """设备列表请求"""
    type: MessageType = field(default=MessageType.DEVICE_LIST, init=False)
    group_filter: str = ""             # 按组过滤
    status_filter: str = ""            # 按状态过滤


@dataclass
class DeviceListResponse(Message):
    """设备列表响应"""
    type: MessageType = field(default=MessageType.DEVICE_LIST, init=False)
    devices: List[Dict[str, Any]] = field(default_factory=list)


# 消息类型映射
MESSAGE_TYPE_MAP: Dict[MessageType, type] = {
    MessageType.COMMAND: CommandMessage,
    MessageType.RESPONSE: ResponseMessage,
    MessageType.HEARTBEAT: HeartbeatMessage,
    MessageType.REGISTER: RegisterMessage,
    MessageType.APPROVAL_REQUEST: ApprovalMessage,
    MessageType.APPROVAL_RESPONSE: ApprovalResponse,
    MessageType.ERROR: ErrorMessage,
    MessageType.FILE_DATA: FileTransferMessage,
    MessageType.DEVICE_LIST: DeviceListRequest,
}


def parse_message(data: Dict[str, Any]) -> Message:
    """解析消息"""
    msg_type = MessageType(data.get('type', 'error'))
    msg_class = MESSAGE_TYPE_MAP.get(msg_type, Message)
    
    # 处理枚举字段
    if msg_type == MessageType.COMMAND and 'priority' in data:
        data['priority'] = CommandPriority(data['priority'])
    elif msg_type == MessageType.APPROVAL_RESPONSE and 'action' in data:
        data['action'] = ApprovalAction(data['action'])
    
    return msg_class(**data)
