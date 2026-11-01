"""
Hermes Relay - WebSocket 服务端
处理被控端 Agent 的连接和通信
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

from .protocol import WSProtocol, WSMessage, MessageType

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket 服务端
    
    处理被控端 Agent 的连接，包括：
    - 设备注册
    - 心跳维护
    - 命令下发
    - 结果接收
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        """
        初始化 WebSocket 服务端
        
        Args:
            host: 监听地址
            port: 监听端口
        """
        self._host = host
        self._port = port
        
        # 连接管理
        self._connections: Dict[str, WebSocketServerProtocol] = {}  # websocket_id -> websocket
        self._device_connections: Dict[str, str] = {}  # device_id -> websocket_id
        self._connection_devices: Dict[str, str] = {}  # websocket_id -> device_id
        
        # 回调函数
        self._on_device_register: Optional[Callable] = None
        self._on_device_heartbeat: Optional[Callable] = None
        self._on_command_response: Optional[Callable] = None
        self._on_device_disconnect: Optional[Callable] = None
        
        # 服务状态
        self._server = None
        self._running = False
        
        # 统计信息
        self._total_connections = 0
        self._total_messages = 0
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self._connections)
    
    def set_callbacks(
        self,
        on_device_register: Optional[Callable] = None,
        on_device_heartbeat: Optional[Callable] = None,
        on_command_response: Optional[Callable] = None,
        on_device_disconnect: Optional[Callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_device_register = on_device_register
        self._on_device_heartbeat = on_device_heartbeat
        self._on_command_response = on_command_response
        self._on_device_disconnect = on_device_disconnect
    
    async def start(self) -> bool:
        """
        启动 WebSocket 服务端
        
        Returns:
            是否启动成功
        """
        if not WS_AVAILABLE:
            logger.error("websockets not installed. Run: pip install websockets")
            return False
        
        try:
            self._server = await websockets.serve(
                self._handle_connection,
                self._host,
                self._port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
            )
            self._running = True
            logger.info("[WebSocket] Server started on %s:%d", self._host, self._port)
            return True
        except Exception as e:
            logger.error("[WebSocket] Failed to start: %s", e, exc_info=True)
            return False
    
    async def stop(self) -> None:
        """停止 WebSocket 服务端"""
        self._running = False
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        # 关闭所有连接
        for ws_id, ws in self._connections.items():
            try:
                await ws.close()
            except Exception:
                pass
        
        self._connections.clear()
        self._device_connections.clear()
        self._connection_devices.clear()
        
        logger.info("[WebSocket] Server stopped")
    
    async def _handle_connection(
        self,
        websocket: WebSocketServerProtocol,
        path: str,
    ) -> None:
        """
        处理新的 WebSocket 连接
        
        Args:
            websocket: WebSocket 连接
            path: 请求路径
        """
        ws_id = str(uuid.uuid4())
        self._connections[ws_id] = websocket
        self._total_connections += 1
        
        logger.info("[WebSocket] New connection: %s from %s", ws_id, websocket.remote_address)
        
        try:
            async for message in websocket:
                await self._handle_message(ws_id, websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("[WebSocket] Connection closed: %s", ws_id)
        except Exception as e:
            logger.error("[WebSocket] Connection error: %s - %s", ws_id, e, exc_info=True)
        finally:
            await self._handle_disconnect(ws_id)
    
    async def _handle_message(
        self,
        ws_id: str,
        websocket: WebSocketServerProtocol,
        raw_message: str,
    ) -> None:
        """
        处理接收到的消息
        
        Args:
            ws_id: WebSocket 连接 ID
            websocket: WebSocket 连接
            raw_message: 原始消息
        """
        self._total_messages += 1
        
        try:
            data = json.loads(raw_message)
            message = WSMessage.from_dict(data)
            
            logger.debug("[WebSocket] Received message: %s from %s", message.type, ws_id)
            
            # 根据消息类型处理
            if message.type == MessageType.REGISTER:
                await self._handle_register(ws_id, websocket, message)
            elif message.type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(ws_id, websocket, message)
            elif message.type == MessageType.RESPONSE:
                await self._handle_response(ws_id, websocket, message)
            elif message.type == MessageType.PONG:
                # 心跳响应，忽略
                pass
            else:
                logger.warning("[WebSocket] Unknown message type: %s", message.type)
                
        except json.JSONDecodeError:
            logger.error("[WebSocket] Invalid JSON message from %s", ws_id)
        except Exception as e:
            logger.error("[WebSocket] Error handling message: %s", e, exc_info=True)
    
    async def _handle_register(
        self,
        ws_id: str,
        websocket: WebSocketServerProtocol,
        message: WSMessage,
    ) -> None:
        """处理设备注册消息"""
        device_id = message.payload.get("device_id", "")
        device_name = message.payload.get("device_name", "")
        
        if not device_id:
            logger.warning("[WebSocket] Registration without device_id from %s", ws_id)
            return
        
        # 建立映射关系
        self._device_connections[device_id] = ws_id
        self._connection_devices[ws_id] = device_id
        
        logger.info("[WebSocket] Device registered: %s (%s) via %s", 
                   device_name, device_id, ws_id)
        
        # 发送注册确认
        response = WSMessage(
            type=MessageType.ACK,
            payload={
                "status": "ok",
                "device_id": device_id,
                "server_time": time.time(),
            }
        )
        await websocket.send(response.to_json())
        
        # 触发回调
        if self._on_device_register:
            await self._on_device_register(device_id, message.payload)
    
    async def _handle_heartbeat(
        self,
        ws_id: str,
        websocket: WebSocketServerProtocol,
        message: WSMessage,
    ) -> None:
        """处理心跳消息"""
        device_id = self._connection_devices.get(ws_id)
        if not device_id:
            return
        
        # 发送心跳响应
        response = WSMessage(
            type=MessageType.PONG,
            payload={"server_time": time.time()}
        )
        await websocket.send(response.to_json())
        
        # 触发回调
        if self._on_device_heartbeat:
            await self._on_device_heartbeat(device_id, message.payload)
    
    async def _handle_response(
        self,
        ws_id: str,
        websocket: WebSocketServerProtocol,
        message: WSMessage,
    ) -> None:
        """处理命令响应"""
        device_id = self._connection_devices.get(ws_id)
        if not device_id:
            return
        
        # 触发回调
        if self._on_command_response:
            await self._on_command_response(device_id, message.payload)
    
    async def _handle_disconnect(self, ws_id: str) -> None:
        """处理连接断开"""
        # 获取关联的设备
        device_id = self._connection_devices.pop(ws_id, None)
        if device_id:
            self._device_connections.pop(device_id, None)
            
            logger.info("[WebSocket] Device disconnected: %s", device_id)
            
            # 触发回调
            if self._on_device_disconnect:
                await self._on_device_disconnect(device_id)
        
        # 移除连接
        self._connections.pop(ws_id, None)
    
    async def send_to_device(
        self,
        device_id: str,
        message: WSMessage,
    ) -> bool:
        """
        发送消息到指定设备
        
        Args:
            device_id: 设备ID
            message: 消息
        
        Returns:
            是否发送成功
        """
        ws_id = self._device_connections.get(device_id)
        if not ws_id:
            logger.warning("[WebSocket] Device not connected: %s", device_id)
            return False
        
        websocket = self._connections.get(ws_id)
        if not websocket:
            logger.warning("[WebSocket] Connection not found: %s", ws_id)
            return False
        
        try:
            await websocket.send(message.to_json())
            return True
        except Exception as e:
            logger.error("[WebSocket] Send error: %s", e, exc_info=True)
            return False
    
    async def send_to_group(
        self,
        device_ids: List[str],
        message: WSMessage,
    ) -> Dict[str, bool]:
        """
        发送消息到多个设备
        
        Args:
            device_ids: 设备ID列表
            message: 消息
        
        Returns:
            设备ID -> 发送结果 的映射
        """
        results = {}
        for device_id in device_ids:
            results[device_id] = await self.send_to_device(device_id, message)
        return results
    
    async def broadcast(self, message: WSMessage) -> int:
        """
        广播消息到所有连接
        
        Args:
            message: 消息
        
        Returns:
            成功发送的数量
        """
        success_count = 0
        for ws_id, websocket in self._connections.items():
            try:
                await websocket.send(message.to_json())
                success_count += 1
            except Exception:
                pass
        return success_count
    
    def get_connected_devices(self) -> List[str]:
        """获取所有已连接的设备ID"""
        return list(self._device_connections.keys())
    
    def get_device_websocket(self, device_id: str) -> Optional[WebSocketServerProtocol]:
        """获取设备的 WebSocket 连接"""
        ws_id = self._device_connections.get(device_id)
        if ws_id:
            return self._connections.get(ws_id)
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "running": self._running,
            "host": self._host,
            "port": self._port,
            "current_connections": len(self._connections),
            "connected_devices": len(self._device_connections),
            "total_connections": self._total_connections,
            "total_messages": self._total_messages,
        }
