"""
Hermes Relay - 被控端 WebSocket 客户端
连接到中转站服务端，接收和发送消息
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

try:
    import websockets
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MessageType:
    """消息类型常量"""
    REGISTER = "register"
    REGISTER_ACK = "register_ack"
    HEARTBEAT = "heartbeat"
    PONG = "pong"
    COMMAND = "command"
    RESPONSE = "response"
    CANCEL = "cancel"
    ERROR = "error"
    ACK = "ack"


class WSClient:
    """
    WebSocket 客户端
    
    连接到中转站服务端，处理命令和心跳
    """
    
    def __init__(
        self,
        server_url: str,
        device_id: str,
        device_name: str = "",
        device_group: str = "default",
        auth_token: str = "",
    ):
        """
        初始化 WebSocket 客户端
        
        Args:
            server_url: 服务端地址 (ws://host:port)
            device_id: 设备ID
            device_name: 设备名称
            device_group: 设备组
            auth_token: 认证令牌
        """
        self._server_url = server_url
        self._device_id = device_id
        self._device_name = device_name
        self._device_group = device_group
        self._auth_token = auth_token
        
        self._websocket = None
        self._connected = False
        self._running = False
        
        # 回调函数
        self._on_command: Optional[Callable] = None
        self._on_cancel: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        
        # 消息处理任务
        self._receive_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    def set_callbacks(
        self,
        on_command: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_command = on_command
        self._on_cancel = on_cancel
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
    
    async def connect(self) -> bool:
        """
        连接到服务端
        
        Returns:
            是否连接成功
        """
        if not WS_AVAILABLE:
            logger.error("websockets not installed. Run: pip install websockets")
            return False
        
        try:
            self._websocket = await websockets.connect(
                self._server_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            self._running = True
            
            # 发送注册消息
            await self._send_register()
            
            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            logger.info("[WSClient] Connected to %s", self._server_url)
            
            # 触发回调
            if self._on_connect:
                await self._on_connect()
            
            return True
            
        except Exception as e:
            logger.error("[WSClient] Failed to connect: %s", e, exc_info=True)
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        self._running = False
        self._connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
        
        logger.info("[WSClient] Disconnected")
    
    async def _send_register(self) -> None:
        """发送注册消息"""
        import platform
        import socket
        
        message = {
            "type": MessageType.REGISTER,
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "payload": {
                "device_id": self._device_id,
                "device_name": self._device_name,
                "device_group": self._device_group,
                "os_version": platform.platform(),
                "ip_address": self._get_local_ip(),
                "hostname": socket.gethostname(),
                "capabilities": ["command", "screenshot", "file_transfer"],
                "auth_token": self._auth_token,
            }
        }
        
        await self._send(message)
    
    async def _receive_loop(self) -> None:
        """消息接收循环"""
        try:
            async for raw_message in self._websocket:
                if not self._running:
                    break
                
                try:
                    data = json.loads(raw_message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.error("[WSClient] Invalid JSON message")
                except Exception as e:
                    logger.error("[WSClient] Error handling message: %s", e, exc_info=True)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("[WSClient] Connection closed")
        except Exception as e:
            logger.error("[WSClient] Receive error: %s", e, exc_info=True)
        finally:
            self._connected = False
            
            # 触发断开回调
            if self._on_disconnect:
                await self._on_disconnect()
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """处理接收到的消息"""
        message_type = data.get("type")
        payload = data.get("payload", {})
        
        if message_type == MessageType.REGISTER_ACK:
            logger.info("[WSClient] Registration acknowledged")
            
        elif message_type == MessageType.COMMAND:
            # 触发命令回调
            if self._on_command:
                await self._on_command(payload)
            
        elif message_type == MessageType.CANCEL:
            # 触发取消回调
            if self._on_cancel:
                await self._on_cancel(payload)
            
        elif message_type == MessageType.PONG:
            # 心跳响应，忽略
            pass
            
        elif message_type == MessageType.ERROR:
            logger.error("[WSClient] Server error: %s", payload.get("error_message"))
            
        else:
            logger.debug("[WSClient] Unknown message type: %s", message_type)
    
    async def _send(self, data: Dict[str, Any]) -> bool:
        """发送消息"""
        if not self._websocket or not self._connected:
            logger.error("[WSClient] Not connected")
            return False
        
        try:
            await self._websocket.send(json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error("[WSClient] Send error: %s", e, exc_info=True)
            return False
    
    async def send_heartbeat(
        self,
        cpu_usage: float = 0.0,
        memory_usage: float = 0.0,
        disk_usage: float = 0.0,
        uptime: float = 0.0,
        active_commands: int = 0,
    ) -> bool:
        """发送心跳"""
        message = {
            "type": MessageType.HEARTBEAT,
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "payload": {
                "device_id": self._device_id,
                "device_name": self._device_name,
                "device_group": self._device_group,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": disk_usage,
                "uptime": uptime,
                "active_commands": active_commands,
            }
        }
        return await self._send(message)
    
    async def send_response(
        self,
        command_id: str,
        status: str = "success",
        output: str = "",
        error_output: str = "",
        exit_code: Optional[int] = None,
        execution_time: float = 0.0,
    ) -> bool:
        """发送命令响应"""
        message = {
            "type": MessageType.RESPONSE,
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "payload": {
                "command_id": command_id,
                "status": status,
                "output": output,
                "error_output": error_output,
                "exit_code": exit_code,
                "execution_time": execution_time,
            }
        }
        return await self._send(message)
    
    async def send_error(
        self,
        error_code: str,
        error_message: str,
    ) -> bool:
        """发送错误消息"""
        message = {
            "type": MessageType.ERROR,
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "payload": {
                "error_code": error_code,
                "error_message": error_message,
            }
        }
        return await self._send(message)
    
    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
