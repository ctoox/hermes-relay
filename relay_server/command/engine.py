"""
Hermes Relay - 命令执行引擎
负责命令的解析、安全检查、路由和执行
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .approval import ApprovalManager, ApprovalResult
from .whitelist import CommandWhitelist, RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class CommandRequest:
    """命令请求"""
    command_id: str                     # 命令ID
    command: str                        # 原始命令
    normalized_command: str = ""        # 标准化后的命令
    device_id: str = ""                 # 目标设备ID
    device_group: str = ""              # 目标设备组
    working_dir: str = ""               # 工作目录
    timeout: int = 30                   # 超时时间
    priority: str = "normal"            # 优先级
    env_vars: Dict[str, str] = field(default_factory=dict)  # 环境变量
    
    # 审批相关
    requires_approval: bool = False     # 是否需要审批
    approval_id: str = ""               # 审批ID
    approved: bool = False              # 是否已批准
    
    # 来源信息
    source: str = ""                    # 来源 (feishu/websocket)
    requester: str = ""                 # 请求者
    chat_id: str = ""                   # 聊天ID
    
    # 状态
    status: str = "pending"             # pending/approved/executing/completed/failed/cancelled
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    
    # 结果
    output: str = ""
    error_output: str = ""
    exit_code: Optional[int] = None
    execution_time: float = 0.0


@dataclass
class CommandResult:
    """命令执行结果"""
    command_id: str
    status: str  # success/error/timeout/cancelled
    output: str = ""
    error_output: str = ""
    exit_code: Optional[int] = None
    execution_time: float = 0.0
    device_id: str = ""


class CommandEngine:
    """
    命令执行引擎
    
    负责：
    - 命令解析和标准化
    - 安全检查 (白名单/黑名单)
    - 审批流程管理
    - 命令路由 (单设备/多设备)
    - 执行结果处理
    """
    
    def __init__(
        self,
        whitelist: Optional[CommandWhitelist] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ):
        """
        初始化命令引擎
        
        Args:
            whitelist: 命令白名单管理器
            approval_manager: 审批管理器
        """
        self._whitelist = whitelist or CommandWhitelist()
        self._approval_manager = approval_manager or ApprovalManager()
        
        # 命令队列
        self._pending_commands: Dict[str, CommandRequest] = {}
        self._executing_commands: Dict[str, CommandRequest] = {}
        self._completed_commands: Dict[str, CommandResult] = {}
        
        # 命令回调
        self._on_command_complete: Optional[Callable] = None
        self._on_command_error: Optional[Callable] = None
        self._on_approval_required: Optional[Callable] = None
        
        # 设备发送回调
        self._send_to_device: Optional[Callable] = None
        
        self._lock = asyncio.Lock()
        
        # 历史记录限制
        self._max_history = 1000
    
    def set_callbacks(
        self,
        on_command_complete: Optional[Callable] = None,
        on_command_error: Optional[Callable] = None,
        on_approval_required: Optional[Callable] = None,
        send_to_device: Optional[Callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_command_complete = on_command_complete
        self._on_command_error = on_command_error
        self._on_approval_required = on_approval_required
        self._send_to_device = send_to_device
    
    async def process_command(
        self,
        command: str,
        device_id: str = "",
        device_group: str = "",
        working_dir: str = "",
        timeout: int = 30,
        priority: str = "normal",
        env_vars: Optional[Dict[str, str]] = None,
        requester: str = "",
        chat_id: str = "",
    ) -> CommandRequest:
        """
        处理命令请求
        
        Args:
            command: 命令字符串
            device_id: 目标设备ID
            device_group: 目标设备组
            working_dir: 工作目录
            timeout: 超时时间
            priority: 优先级
            env_vars: 环境变量
            requester: 请求者
            chat_id: 聊天ID
        
        Returns:
            命令请求对象
        """
        # 创建命令请求
        request = CommandRequest(
            command_id=str(uuid.uuid4()),
            command=command,
            normalized_command=self._normalize_command(command),
            device_id=device_id,
            device_group=device_group,
            working_dir=working_dir,
            timeout=timeout,
            priority=priority,
            env_vars=env_vars or {},
            requester=requester,
            chat_id=chat_id,
        )
        
        # 安全检查
        risk_level = self._whitelist.check_command(request.normalized_command)
        
        # 根据风险等级处理
        if risk_level == RiskLevel.BLOCKED:
            logger.warning("[CommandEngine] Blocked command: %s", command)
            request.status = "failed"
            request.output = "命令被禁止执行"
            await self._handle_command_error(request, "BLOCKED")
            return request
        
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            # 需要审批
            request.requires_approval = True
            request.approval_id = str(uuid.uuid4())
            
            logger.info("[CommandEngine] Command requires approval: %s (risk: %s)", 
                       command, risk_level.value)
            
            # 存储待审批命令
            async with self._lock:
                self._pending_commands[request.command_id] = request
            
            # 触发审批回调
            if self._on_approval_required:
                await self._on_approval_required(request, risk_level)
            
            return request
        
        # 无需审批，直接执行
        await self._execute_command(request)
        return request
    
    def _normalize_command(self, command: str) -> str:
        """标准化命令"""
        # 去除首尾空白
        command = command.strip()
        
        # 统一路径分隔符
        command = command.replace('/', '\\')
        
        # 移除多余的空格
        command = re.sub(r'\s+', ' ', command)
        
        return command
    
    async def _execute_command(self, request: CommandRequest) -> None:
        """执行命令"""
        request.status = "executing"
        request.started_at = time.time()
        
        async with self._lock:
            self._executing_commands[request.command_id] = request
            if request.command_id in self._pending_commands:
                del self._pending_commands[request.command_id]
        
        # 发送到设备执行
        if self._send_to_device:
            device_id = request.device_id
            if not device_id and request.device_group:
                # 发送到组内的所有设备
                device_id = f"group:{request.device_group}"
            
            await self._send_to_device(device_id, request)
        else:
            logger.error("[CommandEngine] No device send callback configured")
            await self._handle_command_error(request, "NO_DEVICE")
    
    async def handle_command_response(
        self,
        command_id: str,
        status: str,
        output: str = "",
        error_output: str = "",
        exit_code: Optional[int] = None,
        execution_time: float = 0.0,
        device_id: str = "",
    ) -> None:
        """
        处理命令执行响应
        
        Args:
            command_id: 命令ID
            status: 执行状态
            output: 输出内容
            error_output: 错误输出
            exit_code: 退出码
            execution_time: 执行时间
            device_id: 执行设备ID
        """
        async with self._lock:
            # 从执行中列表移除
            request = self._executing_commands.pop(command_id, None)
            if request is None:
                logger.warning("[CommandEngine] Unknown command response: %s", command_id)
                return
            
            # 更新请求状态
            request.status = status
            request.output = output
            request.error_output = error_output
            request.exit_code = exit_code
            request.execution_time = execution_time
            request.completed_at = time.time()
            
            # 创建结果
            result = CommandResult(
                command_id=command_id,
                status=status,
                output=output,
                error_output=error_output,
                exit_code=exit_code,
                execution_time=execution_time,
                device_id=device_id,
            )
            
            # 存储到历史
            self._completed_commands[command_id] = result
            
            # 限制历史记录大小
            while len(self._completed_commands) > self._max_history:
                self._completed_commands.popitem(last=False)
        
        # 触发回调
        if status == "success":
            if self._on_command_complete:
                await self._on_command_complete(request, result)
        else:
            if self._on_command_error:
                await self._on_command_error(request, result)
    
    async def _handle_command_error(
        self,
        request: CommandRequest,
        error_code: str,
    ) -> None:
        """处理命令错误"""
        request.status = "failed"
        request.completed_at = time.time()
        
        result = CommandResult(
            command_id=request.command_id,
            status="error",
            output=request.output,
            error_output=f"Error: {error_code}",
        )
        
        async with self._lock:
            self._completed_commands[request.command_id] = result
        
        if self._on_command_error:
            await self._on_command_error(request, result)
    
    async def approve_command(
        self,
        approval_id: str,
        approved: bool,
        approver: str = "",
        session_approve: bool = False,
    ) -> bool:
        """
        审批命令
        
        Args:
            approval_id: 审批ID
            approved: 是否批准
            approver: 审批人
            session_approve: 是否会话级批准
        
        Returns:
            是否成功处理
        """
        # 查找待审批的命令
        request = None
        async with self._lock:
            for req in self._pending_commands.values():
                if req.approval_id == approval_id:
                    request = req
                    break
        
        if request is None:
            logger.warning("[CommandEngine] Unknown approval ID: %s", approval_id)
            return False
        
        if approved:
            # 记录审批结果
            self._approval_manager.record_approval(
                command=request.normalized_command,
                approver=approver,
                session_approve=session_approve,
            )
            
            # 执行命令
            await self._execute_command(request)
        else:
            # 拒绝命令
            request.status = "cancelled"
            request.output = "命令被用户拒绝"
            request.completed_at = time.time()
            
            async with self._lock:
                self._pending_commands.pop(request.command_id, None)
            
            if self._on_command_error:
                result = CommandResult(
                    command_id=request.command_id,
                    status="cancelled",
                    output="命令被用户拒绝",
                )
                await self._on_command_error(request, result)
        
        return True
    
    async def cancel_command(self, command_id: str) -> bool:
        """
        取消命令
        
        Args:
            command_id: 命令ID
        
        Returns:
            是否成功取消
        """
        async with self._lock:
            # 检查待审批队列
            if command_id in self._pending_commands:
                request = self._pending_commands.pop(command_id)
                request.status = "cancelled"
                request.output = "命令被取消"
                request.completed_at = time.time()
                return True
            
            # 检查执行中队列
            if command_id in self._executing_commands:
                request = self._executing_commands[command_id]
                request.status = "cancelled"
                # 需要发送取消指令到设备
                if self._send_to_device:
                    await self._send_to_device(request.device_id, None, cancel=True)
                return True
        
        return False
    
    def get_pending_commands(self) -> List[CommandRequest]:
        """获取待处理命令"""
        return list(self._pending_commands.values())
    
    def get_executing_commands(self) -> List[CommandRequest]:
        """获取执行中命令"""
        return list(self._executing_commands.values())
    
    def get_command_result(self, command_id: str) -> Optional[CommandResult]:
        """获取命令结果"""
        return self._completed_commands.get(command_id)
    
    def get_command_history(self, limit: int = 50) -> List[CommandResult]:
        """获取命令历史"""
        results = list(self._completed_commands.values())
        results.sort(key=lambda r: r.command_id, reverse=True)
        return results[:limit]
