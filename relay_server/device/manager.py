"""
Hermes Relay - 设备管理器
负责设备的注册、心跳监控、状态管理和分组
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class Device:
    """设备信息"""
    device_id: str                          # 设备唯一ID (UUID)
    device_name: str                        # 设备名称 (用户自定义)
    device_group: str = "default"           # 设备组
    os_version: str = ""                    # 操作系统版本
    ip_address: str = ""                    # IP地址
    mac_address: str = ""                   # MAC地址
    hostname: str = ""                      # 主机名
    capabilities: List[str] = field(default_factory=list)  # 支持的能力
    auth_token: str = ""                    # 认证令牌
    
    # 状态信息
    status: str = "offline"                 # online/offline/busy/error
    last_heartbeat: float = 0.0             # 最后心跳时间
    cpu_usage: float = 0.0                  # CPU使用率
    memory_usage: float = 0.0               # 内存使用率
    disk_usage: float = 0.0                 # 磁盘使用率
    uptime: float = 0.0                     # 运行时间
    active_commands: int = 0                # 活跃命令数
    
    # 连接信息
    websocket_id: str = ""                  # WebSocket连接ID
    connected_at: float = 0.0               # 连接时间
    last_command_at: float = 0.0            # 最后命令执行时间
    
    # 统计信息
    total_commands: int = 0                 # 总命令数
    successful_commands: int = 0            # 成功命令数
    failed_commands: int = 0                # 失败命令数
    
    @property
    def is_online(self) -> bool:
        """是否在线"""
        return self.status == "online"
    
    @property
    def is_busy(self) -> bool:
        """是否忙碌"""
        return self.status == "busy"
    
    @property
    def is_available(self) -> bool:
        """是否可用 (在线且不忙碌)"""
        return self.status == "online" and self.active_commands == 0
    
    @property
    def command_success_rate(self) -> float:
        """命令成功率"""
        if self.total_commands == 0:
            return 100.0
        return (self.successful_commands / self.total_commands) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_group': self.device_group,
            'os_version': self.os_version,
            'ip_address': self.ip_address,
            'hostname': self.hostname,
            'capabilities': self.capabilities,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'uptime': self.uptime,
            'active_commands': self.active_commands,
            'connected_at': self.connected_at,
            'total_commands': self.total_commands,
            'successful_commands': self.successful_commands,
            'failed_commands': self.failed_commands,
        }
    
    def update_from_heartbeat(self, heartbeat_data: Dict[str, Any]) -> None:
        """从心跳数据更新设备信息"""
        self.cpu_usage = heartbeat_data.get('cpu_usage', self.cpu_usage)
        self.memory_usage = heartbeat_data.get('memory_usage', self.memory_usage)
        self.disk_usage = heartbeat_data.get('disk_usage', self.disk_usage)
        self.uptime = heartbeat_data.get('uptime', self.uptime)
        self.active_commands = heartbeat_data.get('active_commands', self.active_commands)
        self.last_heartbeat = time.time()
        self.status = "online"


@dataclass
class DeviceGroup:
    """设备组"""
    group_id: str                           # 组ID
    group_name: str                         # 组名称
    description: str = ""                   # 组描述
    device_ids: Set[str] = field(default_factory=set)  # 设备ID集合
    
    @property
    def device_count(self) -> int:
        """设备数量"""
        return len(self.device_ids)
    
    def add_device(self, device_id: str) -> None:
        """添加设备"""
        self.device_ids.add(device_id)
    
    def remove_device(self, device_id: str) -> None:
        """移除设备"""
        self.device_ids.discard(device_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'group_id': self.group_id,
            'group_name': self.group_name,
            'description': self.description,
            'device_count': self.device_count,
            'device_ids': list(self.device_ids),
        }


class DeviceManager:
    """
    设备管理器
    
    负责：
    - 设备注册和注销
    - 心跳监控
    - 状态管理
    - 设备分组
    - 设备查询
    """
    
    def __init__(self, heartbeat_timeout: int = 60):
        """
        初始化设备管理器
        
        Args:
            heartbeat_timeout: 心跳超时时间(秒)
        """
        self._devices: Dict[str, Device] = {}
        self._groups: Dict[str, DeviceGroup] = {}
        self._heartbeat_timeout = heartbeat_timeout
        self._lock = asyncio.Lock()
        
        # 回调函数
        self._on_device_online: Optional[Callable] = None
        self._on_device_offline: Optional[Callable] = None
        self._on_device_status_change: Optional[Callable] = None
        
        # 监控任务
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
    
    @property
    def device_count(self) -> int:
        """设备总数"""
        return len(self._devices)
    
    @property
    def online_count(self) -> int:
        """在线设备数"""
        return sum(1 for d in self._devices.values() if d.is_online)
    
    @property
    def online_devices(self) -> List[Device]:
        """获取所有在线设备"""
        return [d for d in self._devices.values() if d.is_online]
    
    @property
    def all_devices(self) -> List[Device]:
        """获取所有设备"""
        return list(self._devices.values())
    
    def set_callbacks(
        self,
        on_device_online: Optional[Callable] = None,
        on_device_offline: Optional[Callable] = None,
        on_device_status_change: Optional[Callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_device_online = on_device_online
        self._on_device_offline = on_device_offline
        self._on_device_status_change = on_device_status_change
    
    async def start(self) -> None:
        """启动设备管理器"""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("[DeviceManager] Started")
    
    async def stop(self) -> None:
        """停止设备管理器"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("[DeviceManager] Stopped")
    
    async def _monitor_loop(self) -> None:
        """心跳监控循环"""
        while self._running:
            try:
                await self._check_heartbeats()
                await asyncio.sleep(10)  # 每10秒检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[DeviceManager] Monitor error: %s", e, exc_info=True)
                await asyncio.sleep(5)
    
    async def _check_heartbeats(self) -> None:
        """检查设备心跳"""
        now = time.time()
        offline_devices = []
        
        async with self._lock:
            for device_id, device in self._devices.items():
                if device.status == "online" and now - device.last_heartbeat > self._heartbeat_timeout:
                    device.status = "offline"
                    offline_devices.append(device)
                    logger.warning("[DeviceManager] Device %s (%s) offline", 
                                 device.device_name, device.device_id)
        
        # 触发回调
        for device in offline_devices:
            if self._on_device_offline:
                await self._on_device_offline(device)
    
    async def register_device(
        self,
        device_id: str,
        device_name: str,
        device_group: str = "default",
        os_version: str = "",
        ip_address: str = "",
        mac_address: str = "",
        hostname: str = "",
        capabilities: Optional[List[str]] = None,
        auth_token: str = "",
        websocket_id: str = "",
    ) -> Device:
        """
        注册设备
        
        Args:
            device_id: 设备ID
            device_name: 设备名称
            device_group: 设备组
            os_version: 操作系统版本
            ip_address: IP地址
            mac_address: MAC地址
            hostname: 主机名
            capabilities: 支持的能力
            auth_token: 认证令牌
            websocket_id: WebSocket连接ID
        
        Returns:
            注册的设备对象
        """
        async with self._lock:
            # 检查设备是否已存在
            if device_id in self._devices:
                # 更新设备信息
                device = self._devices[device_id]
                device.device_name = device_name
                device.os_version = os_version
                device.ip_address = ip_address
                device.mac_address = mac_address
                device.hostname = hostname
                device.capabilities = capabilities or device.capabilities
                device.websocket_id = websocket_id
                device.status = "online"
                device.last_heartbeat = time.time()
                device.connected_at = time.time()
            else:
                # 创建新设备
                device = Device(
                    device_id=device_id,
                    device_name=device_name,
                    device_group=device_group,
                    os_version=os_version,
                    ip_address=ip_address,
                    mac_address=mac_address,
                    hostname=hostname,
                    capabilities=capabilities or [],
                    auth_token=auth_token,
                    status="online",
                    last_heartbeat=time.time(),
                    websocket_id=websocket_id,
                    connected_at=time.time(),
                )
                self._devices[device_id] = device
            
            # 添加到设备组
            if device_group not in self._groups:
                self._groups[device_group] = DeviceGroup(
                    group_id=device_group,
                    group_name=device_group,
                )
            self._groups[device_group].add_device(device_id)
            
            logger.info("[DeviceManager] Device registered: %s (%s) in group %s",
                       device_name, device_id, device_group)
        
        # 触发回调
        if self._on_device_online:
            await self._on_device_online(device)
        
        return device
    
    async def unregister_device(self, device_id: str) -> bool:
        """
        注销设备
        
        Args:
            device_id: 设备ID
        
        Returns:
            是否成功注销
        """
        async with self._lock:
            if device_id not in self._devices:
                return False
            
            device = self._devices[device_id]
            
            # 从设备组中移除
            for group in self._groups.values():
                group.remove_device(device_id)
            
            # 删除设备
            del self._devices[device_id]
            
            logger.info("[DeviceManager] Device unregistered: %s (%s)",
                       device.device_name, device_id)
        
        # 触发回调
        if self._on_device_offline:
            await self._on_device_offline(device)
        
        return True
    
    async def update_heartbeat(
        self,
        device_id: str,
        heartbeat_data: Dict[str, Any],
    ) -> bool:
        """
        更新设备心跳
        
        Args:
            device_id: 设备ID
            heartbeat_data: 心跳数据
        
        Returns:
            是否成功更新
        """
        async with self._lock:
            if device_id not in self._devices:
                return False
            
            device = self._devices[device_id]
            device.update_from_heartbeat(heartbeat_data)
            
            return True
    
    async def get_device(self, device_id: str) -> Optional[Device]:
        """获取设备"""
        return self._devices.get(device_id)
    
    async def get_device_by_name(self, name: str) -> Optional[Device]:
        """根据名称获取设备"""
        for device in self._devices.values():
            if device.device_name.lower() == name.lower():
                return device
        return None
    
    async def get_devices_by_group(self, group_name: str) -> List[Device]:
        """获取指定组的所有设备"""
        group = self._groups.get(group_name)
        if not group:
            return []
        
        return [
            self._devices[device_id]
            for device_id in group.device_ids
            if device_id in self._devices
        ]
    
    async def get_available_devices(self) -> List[Device]:
        """获取所有可用设备"""
        return [d for d in self._devices.values() if d.is_available]
    
    async def get_all_groups(self) -> List[DeviceGroup]:
        """获取所有设备组"""
        return list(self._groups.values())
    
    async def update_device_status(
        self,
        device_id: str,
        status: str,
    ) -> bool:
        """
        更新设备状态
        
        Args:
            device_id: 设备ID
            status: 新状态
        
        Returns:
            是否成功更新
        """
        async with self._lock:
            if device_id not in self._devices:
                return False
            
            device = self._devices[device_id]
            old_status = device.status
            device.status = status
            
            if old_status != status:
                logger.info("[DeviceManager] Device %s status: %s -> %s",
                           device.device_name, old_status, status)
                
                # 触发回调
                if self._on_device_status_change:
                    await self._on_device_status_change(device, old_status, status)
            
            return True
    
    async def record_command_result(
        self,
        device_id: str,
        success: bool,
    ) -> None:
        """记录命令执行结果"""
        async with self._lock:
            if device_id not in self._devices:
                return
            
            device = self._devices[device_id]
            device.total_commands += 1
            if success:
                device.successful_commands += 1
            else:
                device.failed_commands += 1
            device.last_command_at = time.time()
    
    async def get_device_stats(self) -> Dict[str, Any]:
        """获取设备统计信息"""
        async with self._lock:
            total = len(self._devices)
            online = sum(1 for d in self._devices.values() if d.is_online)
            busy = sum(1 for d in self._devices.values() if d.is_busy)
            offline = total - online
            
            total_commands = sum(d.total_commands for d in self._devices.values())
            successful_commands = sum(d.successful_commands for d in self._devices.values())
            
            return {
                'total_devices': total,
                'online_devices': online,
                'busy_devices': busy,
                'offline_devices': offline,
                'total_groups': len(self._groups),
                'total_commands': total_commands,
                'successful_commands': successful_commands,
                'success_rate': (successful_commands / total_commands * 100) if total_commands > 0 else 100,
            }
