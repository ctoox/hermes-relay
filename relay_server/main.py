"""
Hermes Relay - 中转站服务端主模块
整合所有组件，提供完整的远程控制服务
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any, Dict, Optional

from .config import RelayConfig, load_config
from .feishu import FeishuAdapter, CardBuilder
from .device import DeviceManager, Device, DeviceGroup
from .command import CommandEngine, ApprovalManager, CommandWhitelist
from .nlp import NLPParser
from .websocket import WebSocketServer

logger = logging.getLogger(__name__)


class RelayServer:
    """
    中转站服务端
    
    整合飞书通信、设备管理、命令执行、NLP解析等功能
    """
    
    def __init__(self, config: Optional[RelayConfig] = None):
        """
        初始化中转站服务端
        
        Args:
            config: 配置对象，如果为None则从环境变量加载
        """
        self._config = config or load_config()
        
        # 初始化日志
        self._setup_logging()
        
        # 初始化组件
        self._feishu = FeishuAdapter(self._config.feishu)
        self._device_manager = DeviceManager(
            heartbeat_timeout=self._config.heartbeat_timeout
        )
        self._whitelist = CommandWhitelist()
        self._approval_manager = ApprovalManager(
            default_timeout=self._config.approval_timeout
        )
        self._command_engine = CommandEngine(
            whitelist=self._whitelist,
            approval_manager=self._approval_manager,
        )
        self._nlp_parser = NLPParser()
        self._ws_server = WebSocketServer(
            host=self._config.ws_host,
            port=self._config.ws_port,
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
                logging.FileHandler('relay_server.log', encoding='utf-8'),
            ]
        )
    
    def _setup_callbacks(self) -> None:
        """设置组件间的回调"""
        # 飞书消息回调
        self._feishu.set_message_callback(self._handle_feishu_message)
        self._feishu.set_approval_callback(self._handle_approval_response)
        
        # 设备管理器回调
        self._device_manager.set_callbacks(
            on_device_online=self._on_device_online,
            on_device_offline=self._on_device_offline,
        )
        
        # 命令引擎回调
        self._command_engine.set_callbacks(
            on_command_complete=self._on_command_complete,
            on_command_error=self._on_command_error,
            on_approval_required=self._on_approval_required,
            send_to_device=self._send_command_to_device,
        )
        
        # 审批管理器回调
        self._approval_manager.set_timeout_callback(self._on_approval_timeout)
        
        # WebSocket 服务端回调
        self._ws_server.set_callbacks(
            on_device_register=self._on_ws_device_register,
            on_device_heartbeat=self._on_ws_device_heartbeat,
            on_command_response=self._on_ws_command_response,
            on_device_disconnect=self._on_ws_device_disconnect,
        )
    
    async def start(self) -> bool:
        """
        启动中转站服务端
        
        Returns:
            是否启动成功
        """
        logger.info("=" * 60)
        logger.info("Hermes Relay Server starting...")
        logger.info("=" * 60)
        
        # 启动设备管理器
        await self._device_manager.start()
        
        # 启动审批管理器
        await self._approval_manager.start()
        
        # 启动 WebSocket 服务端
        if not await self._ws_server.start():
            logger.error("Failed to start WebSocket server")
            return False
        
        # 连接飞书
        if not await self._feishu.connect():
            logger.error("Failed to connect to Feishu")
            return False
        
        self._running = True
        
        logger.info("=" * 60)
        logger.info("Hermes Relay Server started successfully!")
        logger.info("WebSocket: %s:%d", self._config.ws_host, self._config.ws_port)
        logger.info("Feishu: Connected (%s)", self._config.feishu.domain)
        logger.info("=" * 60)
        
        return True
    
    async def stop(self) -> None:
        """停止中转站服务端"""
        logger.info("Stopping Hermes Relay Server...")
        
        self._running = False
        
        # 断开飞书
        await self._feishu.disconnect()
        
        # 停止 WebSocket 服务端
        await self._ws_server.stop()
        
        # 停止审批管理器
        await self._approval_manager.stop()
        
        # 停止设备管理器
        await self._device_manager.stop()
        
        logger.info("Hermes Relay Server stopped")
    
    async def run(self) -> None:
        """运行中转站服务端 (阻塞)"""
        if not await self.start():
            return
        
        # 注册信号处理
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                # Windows 不支持 add_signal_handler
                pass
        
        try:
            # 保持运行
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop()
    
    # =========================================================================
    # 飞书消息处理
    # =========================================================================
    
    async def _handle_feishu_message(self, message: Any) -> None:
        """处理飞书消息"""
        try:
            content = message.content.strip()
            chat_id = message.chat_id
            sender_id = message.sender_id
            
            logger.info("[Feishu] Message from %s in %s: %s", 
                       sender_id, chat_id, content[:100])
            
            # 检查是否是审批响应
            if message.message_type == "interactive":
                # 交互式卡片的按钮点击
                return
            
            # 解析命令 (NLP)
            command, metadata = self._nlp_parser.parse(content)
            
            if command is None:
                # 无法解析，发送帮助信息
                help_card = CardBuilder.build_help_card()
                await self._feishu.send_card(chat_id, help_card)
                return
            
            # 检查是否是特殊动作
            special_action = metadata.get("special_action")
            if special_action:
                await self._handle_special_action(special_action, chat_id, content)
                return
            
            # 处理命令
            # 确定目标设备
            device_id = ""
            device_group = ""
            
            # 检查是否指定了设备
            # TODO: 解析 "在 设备名 上执行 命令" 格式
            
            # 执行命令
            request = await self._command_engine.process_command(
                command=command,
                device_id=device_id,
                device_group=device_group,
                requester=sender_id,
                chat_id=chat_id,
            )
            
            # 如果需要审批，发送审批卡片
            if request.requires_approval:
                await self._send_approval_card(request, metadata)
            
        except Exception as e:
            logger.error("[Feishu] Error handling message: %s", e, exc_info=True)
    
    async def _handle_special_action(
        self,
        action: str,
        chat_id: str,
        content: str,
    ) -> None:
        """处理特殊动作"""
        if action == "help":
            help_card = CardBuilder.build_help_card()
            await self._feishu.send_card(chat_id, help_card)
        
        elif action == "device_list":
            devices = self._device_manager.all_devices
            device_dicts = [d.to_dict() for d in devices]
            card = CardBuilder.build_device_list_card(device_dicts)
            await self._feishu.send_card(chat_id, card)
        
        elif action == "screenshot":
            # TODO: 实现截图功能
            await self._feishu.send_message(chat_id, "截图功能开发中...")
    
    async def _send_approval_card(
        self,
        request: Any,
        metadata: Dict[str, Any],
    ) -> None:
        """发送审批卡片"""
        card = CardBuilder.build_approval_card(
            approval_id=request.approval_id,
            command=request.command,
            device_name=request.device_id or "未指定",
            risk_level=metadata.get("risk_level", "medium"),
            reason=metadata.get("description", ""),
        )
        
        await self._feishu.send_card(request.chat_id, card)
    
    async def _handle_approval_response(self, data: Any) -> None:
        """处理审批响应"""
        try:
            # 解析审批响应
            action = data.get("action")
            approval_id = data.get("approval_id")
            
            if action and approval_id:
                await self._command_engine.approve_command(
                    approval_id=approval_id,
                    approved=(action != "deny"),
                    approver=data.get("approver", ""),
                    session_approve=(action == "allow_session"),
                )
        except Exception as e:
            logger.error("[Feishu] Error handling approval: %s", e, exc_info=True)
    
    # =========================================================================
    # 设备管理回调
    # =========================================================================
    
    async def _on_device_online(self, device: Device) -> None:
        """设备上线回调"""
        logger.info("[Device] Online: %s (%s)", device.device_name, device.device_id)
    
    async def _on_device_offline(self, device: Device) -> None:
        """设备离线回调"""
        logger.info("[Device] Offline: %s (%s)", device.device_name, device.device_id)
    
    # =========================================================================
    # 命令执行回调
    # =========================================================================
    
    async def _on_command_complete(self, request: Any, result: Any) -> None:
        """命令执行完成回调"""
        logger.info("[Command] Completed: %s", request.command[:50])
        
        # 发送结果到飞书
        if request.chat_id:
            card = CardBuilder.build_command_result_card(
                command=request.command,
                device_name=request.device_id,
                status="success",
                output=result.output,
                execution_time=result.execution_time,
            )
            await self._feishu.send_card(request.chat_id, card)
        
        # 记录设备命令结果
        await self._device_manager.record_command_result(request.device_id, True)
    
    async def _on_command_error(self, request: Any, result: Any) -> None:
        """命令执行错误回调"""
        logger.error("[Command] Error: %s - %s", request.command[:50], result.error_output)
        
        # 发送错误到飞书
        if request.chat_id:
            card = CardBuilder.build_command_result_card(
                command=request.command,
                device_name=request.device_id,
                status="error",
                output=result.output,
                execution_time=result.execution_time,
            )
            await self._feishu.send_card(request.chat_id, card)
        
        # 记录设备命令结果
        await self._device_manager.record_command_result(request.device_id, False)
    
    async def _on_approval_required(self, request: Any, risk_level: Any) -> None:
        """需要审批回调"""
        logger.info("[Command] Approval required: %s (risk: %s)", 
                   request.command[:50], risk_level.value)
    
    async def _on_approval_timeout(self, approval_id: str) -> None:
        """审批超时回调"""
        logger.warning("[Approval] Timeout: %s", approval_id)
    
    # =========================================================================
    # WebSocket 回调
    # =========================================================================
    
    async def _on_ws_device_register(
        self,
        device_id: str,
        data: Dict[str, Any],
    ) -> None:
        """WebSocket 设备注册回调"""
        await self._device_manager.register_device(
            device_id=device_id,
            device_name=data.get("device_name", ""),
            device_group=data.get("device_group", "default"),
            os_version=data.get("os_version", ""),
            ip_address=data.get("ip_address", ""),
            capabilities=data.get("capabilities", []),
            auth_token=data.get("auth_token", ""),
        )
    
    async def _on_ws_device_heartbeat(
        self,
        device_id: str,
        data: Dict[str, Any],
    ) -> None:
        """WebSocket 设备心跳回调"""
        await self._device_manager.update_heartbeat(device_id, data)
    
    async def _on_ws_command_response(
        self,
        device_id: str,
        data: Dict[str, Any],
    ) -> None:
        """WebSocket 命令响应回调"""
        await self._command_engine.handle_command_response(
            command_id=data.get("command_id", ""),
            status=data.get("status", "error"),
            output=data.get("output", ""),
            error_output=data.get("error_output", ""),
            exit_code=data.get("exit_code"),
            execution_time=data.get("execution_time", 0.0),
            device_id=device_id,
        )
    
    async def _on_ws_device_disconnect(self, device_id: str) -> None:
        """WebSocket 设备断开回调"""
        await self._device_manager.update_device_status(device_id, "offline")
    
    # =========================================================================
    # 命令下发
    # =========================================================================
    
    async def _send_command_to_device(
        self,
        device_id: str,
        request: Any,
        cancel: bool = False,
    ) -> None:
        """发送命令到设备"""
        from .websocket.protocol import WSProtocol
        
        if cancel:
            message = WSProtocol.create_cancel_message(request.command_id if request else "")
        else:
            message = WSProtocol.create_command_message(
                command_id=request.command_id,
                command=request.command,
                working_dir=request.working_dir,
                timeout=request.timeout,
                env_vars=request.env_vars,
            )
        
        # 检查是否是组广播
        if device_id.startswith("group:"):
            group_name = device_id[6:]
            devices = await self._device_manager.get_devices_by_group(group_name)
            for device in devices:
                await self._ws_server.send_to_device(device.device_id, message)
        else:
            await self._ws_server.send_to_device(device_id, message)


def main():
    """主入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hermes Relay Server")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--host", default="0.0.0.0", help="WebSocket 监听地址")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket 监听端口")
    args = parser.parse_args()
    
    # 加载配置
    if args.config:
        config = load_config(args.config)
    else:
        config = load_config()
    
    # 覆盖命令行参数
    if args.host:
        config.ws_host = args.host
    if args.port:
        config.ws_port = args.port
    
    # 创建并运行服务端
    server = RelayServer(config)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
