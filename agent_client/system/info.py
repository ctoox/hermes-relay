"""
Hermes Relay - 系统信息收集器
收集 Windows 系统的 CPU、内存、磁盘等信息
"""

from __future__ import annotations

import logging
import os
import platform
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not installed. System monitoring will be limited.")


class SystemInfo:
    """
    系统信息收集器
    
    收集 Windows 系统的各种信息：
    - CPU 使用率
    - 内存使用率
    - 磁盘使用率
    - 网络信息
    - 运行时间
    """
    
    def __init__(self):
        self._start_time = time.time()
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有系统信息
        
        Returns:
            系统信息字典
        """
        return {
            "os_version": self.get_os_version(),
            "hostname": self.get_hostname(),
            "cpu_usage": self.get_cpu_usage(),
            "memory_usage": self.get_memory_usage(),
            "memory_total": self.get_memory_total(),
            "memory_available": self.get_memory_available(),
            "disk_usage": self.get_disk_usage(),
            "disk_total": self.get_disk_total(),
            "disk_free": self.get_disk_free(),
            "uptime": self.get_uptime(),
            "boot_time": self.get_boot_time(),
            "ip_address": self.get_ip_address(),
            "cpu_count": self.get_cpu_count(),
        }
    
    def get_os_version(self) -> str:
        """获取操作系统版本"""
        return platform.platform()
    
    def get_hostname(self) -> str:
        """获取主机名"""
        return platform.node()
    
    def get_cpu_usage(self) -> float:
        """
        获取 CPU 使用率
        
        Returns:
            CPU 使用率 (0-100)
        """
        if PSUTIL_AVAILABLE:
            try:
                return psutil.cpu_percent(interval=0.1)
            except Exception:
                pass
        return 0.0
    
    def get_cpu_count(self) -> int:
        """获取 CPU 核心数"""
        if PSUTIL_AVAILABLE:
            try:
                return psutil.cpu_count(logical=True)
            except Exception:
                pass
        return os.cpu_count() or 1
    
    def get_memory_usage(self) -> float:
        """
        获取内存使用率
        
        Returns:
            内存使用率 (0-100)
        """
        if PSUTIL_AVAILABLE:
            try:
                return psutil.virtual_memory().percent
            except Exception:
                pass
        return 0.0
    
    def get_memory_total(self) -> int:
        """获取总内存 (字节)"""
        if PSUTIL_AVAILABLE:
            try:
                return psutil.virtual_memory().total
            except Exception:
                pass
        return 0
    
    def get_memory_available(self) -> int:
        """获取可用内存 (字节)"""
        if PSUTIL_AVAILABLE:
            try:
                return psutil.virtual_memory().available
            except Exception:
                pass
        return 0
    
    def get_disk_usage(self) -> float:
        """
        获取磁盘使用率 (C盘)
        
        Returns:
            磁盘使用率 (0-100)
        """
        try:
            if PSUTIL_AVAILABLE:
                return psutil.disk_usage('C:\\').percent
            else:
                import shutil
                total, used, free = shutil.disk_usage('C:\\')
                return (used / total) * 100
        except Exception:
            return 0.0
    
    def get_disk_total(self) -> int:
        """获取磁盘总空间 (字节)"""
        try:
            if PSUTIL_AVAILABLE:
                return psutil.disk_usage('C:\\').total
            else:
                import shutil
                total, used, free = shutil.disk_usage('C:\\')
                return total
        except Exception:
            return 0
    
    def get_disk_free(self) -> int:
        """获取磁盘可用空间 (字节)"""
        try:
            if PSUTIL_AVAILABLE:
                return psutil.disk_usage('C:\\').free
            else:
                import shutil
                total, used, free = shutil.disk_usage('C:\\')
                return free
        except Exception:
            return 0
    
    def get_uptime(self) -> float:
        """
        获取系统运行时间 (秒)
        
        Returns:
            运行时间 (秒)
        """
        if PSUTIL_AVAILABLE:
            try:
                boot_time = psutil.boot_time()
                return time.time() - boot_time
            except Exception:
                pass
        return time.time() - self._start_time
    
    def get_boot_time(self) -> float:
        """
        获取系统启动时间
        
        Returns:
            启动时间戳
        """
        if PSUTIL_AVAILABLE:
            try:
                return psutil.boot_time()
            except Exception:
                pass
        return self._start_time
    
    def get_ip_address(self) -> str:
        """
        获取本机 IP 地址
        
        Returns:
            IP 地址
        """
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def get_network_stats(self) -> Dict[str, Any]:
        """
        获取网络统计信息
        
        Returns:
            网络统计字典
        """
        if PSUTIL_AVAILABLE:
            try:
                net_io = psutil.net_io_counters()
                return {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                }
            except Exception:
                pass
        return {}
    
    def get_process_count(self) -> int:
        """获取进程数量"""
        if PSUTIL_AVAILABLE:
            try:
                return len(psutil.pids())
            except Exception:
                pass
        return 0
    
    def format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f} PB"
