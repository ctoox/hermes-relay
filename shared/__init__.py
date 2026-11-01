"""
Hermes Relay - 共享协议模块
定义中转站和被控端之间的通信协议
"""

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
    DeviceStatus,
)
from .message import (
    create_command,
    create_response,
    create_heartbeat,
    create_register,
    create_approval_request,
    create_approval_response,
    create_error,
)
from .crypto import (
    generate_key,
    encrypt_message,
    decrypt_message,
    sign_message,
    verify_signature,
)

__all__ = [
    # Protocol types
    "MessageType",
    "Message",
    "CommandMessage",
    "ResponseMessage",
    "HeartbeatMessage",
    "RegisterMessage",
    "ApprovalMessage",
    "ApprovalResponse",
    "ErrorMessage",
    "DeviceStatus",
    # Message factories
    "create_command",
    "create_response",
    "create_heartbeat",
    "create_register",
    "create_approval_request",
    "create_approval_response",
    "create_error",
    # Crypto
    "generate_key",
    "encrypt_message",
    "decrypt_message",
    "sign_message",
    "verify_signature",
]
