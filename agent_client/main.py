"""
Hermes Relay - 被控端 Agent 主模块
运行在被控电脑上，接收并执行命令
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any, Dict, Optional

from .config import AgentConfig, load_config
from .websocket import WSClient
from .executor import CommandExecutor
from .system import SystemInfo

logger = logging.getLogger(__name__)


class RelayAgent:
    """
    被控端 Agent
    
    连接到中转站服务端，接收并执行命令
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        初始化被控端 Agent
        
        Args:
            config: 配置对象，如果为None则从环境变量加载
        """
        self._config = config or load_config()
        
        # 初始化日志
        self._setup_logging()
        
        # 初始化组件
        self._executor = CommandExecutor(
            default_timeout=self._config.command_timeout
        )
        self._system_info = SystemInfo()
        self._ws_client = WSClient(
            server_url=self._config.server_url,
            device_id=self._config.device_id,
            device_name=self._config.device_name,
            device_group=self._config.device_group,
            auth_token=self._config.auth_token,
        )
        
        # 状态
        self._running = False
        
        # 注册回调
        self._setup_callbacks()
    
    def _setup_logging(self) -> None:
        """设置日志"""
        log_level = getattr(logging, self._config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('relay_agent.log', encoding='utf-8'),
            ]
        )
    
    def _setup_callbacks(self) -> None:
        """设置回调"""
        self._ws_client.set_callbacks(
            on_command=self._handle_command,
            on_cancel=self._handle_cancel,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )
    
    async def start(self) -> bool:
        """
        启动被控端 Agent
        
        Returns:
            是否启动成功
        """
        logger.info("=" * 60)
        logger.info("Hermes Relay Agent starting...")
        logger.info("=" * 60)
        
        # 连接到服务端
        if not await self._ws_client.connect():
            logger.error("Failed to connect to relay server")
            return False
        
        self._running = True
        
        # 启动心跳任务
        asyncio.create_task(self._heartbeat_loop())
        
        logger.info("=" * 60)
        logger.info("Hermes Relay Agent started successfully!")
        logger.info("Device: %s (%s)", self._config.device_name, self._config.device_id)
        logger.info("Server: %s", self._config.server_url)
        logger.info("=" * 60)
        
        return True
    
    async def stop(self) -> None:
        """停止被控端 Agent"""
        logger.info("Stopping Hermes Relay Agent...")
        
        self._running = False
        
        # 断开连接
        await self._ws_client.disconnect()
        
        logger.info("Hermes Relay Agent stopped")
    
    async def run(self) -> None:
        """运行被控端 Agent (阻塞)"""
        if not await self.start():
            return
        
        # 注册信号处理
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                pass
        
        try:
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop()
    
    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            try:
                # 获取系统信息
                info = self._system_info.get_all()
                
                # 发送心跳
                await self._ws_client.send_heartbeat(
                    cpu_usage=info.get("cpu_usage", 0.0),
                    memory_usage=info.get("memory_usage", 0.0),
                    disk_usage=info.get("disk_usage", 0.0),
                    uptime=info.get("uptime", 0.0),
                    active_commands=self._executor.active_count,
                )
                
                await asyncio.sleep(self._config.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error: %s", e, exc_info=True)
                await asyncio.sleep(5)
    
    async def _handle_command(self, data: Dict[str, Any]) -> None:
        """处理命令"""
        command_id = data.get("command_id", "")
        command = data.get("command", "")
        working_dir = data.get("working_dir", "")
        timeout = data.get("timeout", self._config.command_timeout)
        env_vars = data.get("env_vars", {})
        
        logger.info("[Command] Received: %s (id: %s)", command[:100], command_id)
        
        # 执行命令
        result = await self._executor.execute(
            command=command,
            working_dir=working_dir,
            timeout=timeout,
            env_vars=env_vars,
        )
        
        # 发送响应
        await self._ws_client.send_response(
            command_id=command_id,
            status=result.status,
            output=result.output,
            error_output=result.error_output,
            exit_code=result.exit_code,
            execution_time=result.execution_time,
        )
        
        logger.info("[Command] Completed: %s (status: %s, time: %.2fs)",
                    command[:50], result.status, result.execution_time)
    
    async def _handle_cancel(self, data: Dict[str, Any]) -> None:
        """处理取消命令"""
        command_id = data.get("command_id", "")
        logger.info("[Command] Cancel requested: %s", command_id)
        
        await self._executor.cancel(command_id)
    
    async def _on_connect(self) -> None:
        """连接成功回调"""
        logger.info("[Connection] Connected to relay server")
    
    async def _on_disconnect(self) -> None:
        """断开连接回调"""
        logger.warning("[Connection] Disconnected from relay server")
        
        # 尝试重连
        if self._running:
            logger.info("[Connection] Attempting to reconnect...")
            await asyncio.sleep(5)
            if self._running:
                await self._ws_client.connect()


def main():
    """主入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hermes Relay Agent")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--server", help="服务端地址 (ws://host:port)")
    parser.add_argument("--name", help="设备名称")
    parser.add_argument("--group", default="default", help="设备组")
    parser.add_argument("--token", help="认证令牌")
    args = parser.parse_args()
    
    # 加载配置
    if args.config:
        config = load_config(args.config)
    else:
        config = load_config()
    
    # 覆盖命令行参数
    if args.server:
        config.server_url = args.server
    if args.name:
        config.device_name = args.name
    if args.group:
        config.device_group = args.group
    if args.token:
        config.auth_token = args.token
    
    # 创建并运行 Agent
    agent = RelayAgent(config)
    asyncio.run(agent.run())


if __name__ == "__main__":
    main()
