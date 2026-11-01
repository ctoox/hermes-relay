"""
Hermes Relay - 审批管理器
管理命令审批流程，包括审批请求、响应和记录
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
class ApprovalRecord:
    """审批记录"""
    approval_id: str
    command: str
    command_preview: str
    device_id: str
    device_name: str
    risk_level: str
    reason: str
    
    # 审批结果
    approved: bool = False
    approver: str = ""
    approval_time: float = 0.0
    
    # 时间信息
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    
    # 状态
    status: str = "pending"  # pending/approved/denied/expired
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        return time.time() > self.expires_at if self.expires_at > 0 else False


@dataclass
class ApprovalResult:
    """审批结果"""
    approval_id: str
    approved: bool
    approver: str = ""
    reason: str = ""
    session_approve: bool = False


class ApprovalManager:
    """
    审批管理器
    
    负责：
    - 创建审批请求
    - 处理审批响应
    - 管理审批记录
    - 会话级审批缓存
    - 自动过期处理
    """
    
    def __init__(self, default_timeout: int = 300):
        """
        初始化审批管理器
        
        Args:
            default_timeout: 默认审批超时时间(秒)
        """
        self._default_timeout = default_timeout
        
        # 待审批请求
        self._pending_approvals: Dict[str, ApprovalRecord] = {}
        
        # 审批历史
        self._approval_history: List[ApprovalRecord] = []
        
        # 会话级审批缓存 (session_key -> approved_commands)
        self._session_approvals: Dict[str, Set[str]] = {}
        
        # 永久批准的命令
        self._permanent_approvals: Set[str] = set()
        
        # 回调函数
        self._on_approval_timeout: Optional[Callable] = None
        
        self._lock = asyncio.Lock()
        
        # 监控任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    def set_timeout_callback(self, callback: Callable) -> None:
        """设置超时回调"""
        self._on_approval_timeout = callback
    
    async def start(self) -> None:
        """启动审批管理器"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("[ApprovalManager] Started")
    
    async def stop(self) -> None:
        """停止审批管理器"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("[ApprovalManager] Stopped")
    
    async def _cleanup_loop(self) -> None:
        """清理过期审批的循环"""
        while self._running:
            try:
                await self._cleanup_expired()
                await asyncio.sleep(10)  # 每10秒检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[ApprovalManager] Cleanup error: %s", e, exc_info=True)
                await asyncio.sleep(5)
    
    async def _cleanup_expired(self) -> None:
        """清理过期的审批请求"""
        expired = []
        
        async with self._lock:
            for approval_id, record in self._pending_approvals.items():
                if record.is_expired:
                    expired.append(approval_id)
            
            for approval_id in expired:
                record = self._pending_approvals.pop(approval_id)
                record.status = "expired"
                self._approval_history.append(record)
                logger.info("[ApprovalManager] Approval expired: %s", approval_id)
        
        # 触发超时回调
        for approval_id in expired:
            if self._on_approval_timeout:
                await self._on_approval_timeout(approval_id)
    
    async def create_approval(
        self,
        command: str,
        device_id: str,
        device_name: str = "",
        risk_level: str = "medium",
        reason: str = "",
        timeout: Optional[int] = None,
    ) -> ApprovalRecord:
        """
        创建审批请求
        
        Args:
            command: 待审批的命令
            device_id: 目标设备ID
            device_name: 设备名称
            risk_level: 风险等级
            reason: 审批原因
            timeout: 超时时间
        
        Returns:
            审批记录
        """
        approval_id = str(uuid.uuid4())
        timeout = timeout or self._default_timeout
        
        # 截断命令预览
        preview = command[:200] + "..." if len(command) > 200 else command
        
        record = ApprovalRecord(
            approval_id=approval_id,
            command=command,
            command_preview=preview,
            device_id=device_id,
            device_name=device_name,
            risk_level=risk_level,
            reason=reason,
            expires_at=time.time() + timeout,
        )
        
        async with self._lock:
            self._pending_approvals[approval_id] = record
        
        logger.info("[ApprovalManager] Created approval: %s for command: %s", 
                   approval_id, command[:50])
        
        return record
    
    async def handle_response(
        self,
        approval_id: str,
        action: str,
        approver: str = "",
    ) -> ApprovalResult:
        """
        处理审批响应
        
        Args:
            approval_id: 审批ID
            action: 审批动作 (allow_once/allow_session/allow_always/deny)
            approver: 审批人
        
        Returns:
            审批结果
        """
        async with self._lock:
            record = self._pending_approvals.pop(approval_id, None)
            if record is None:
                logger.warning("[ApprovalManager] Unknown approval ID: %s", approval_id)
                return ApprovalResult(
                    approval_id=approval_id,
                    approved=False,
                    reason="审批请求不存在或已过期",
                )
            
            # 处理审批动作
            if action == "allow_once":
                record.approved = True
                record.approver = approver
                record.approval_time = time.time()
                record.status = "approved"
                
            elif action == "allow_session":
                record.approved = True
                record.approver = approver
                record.approval_time = time.time()
                record.status = "approved"
                
                # 添加到会话审批缓存
                # 注意：这里简化处理，实际应该关联到具体的会话
                command_key = self._normalize_command_key(record.command)
                if "current_session" not in self._session_approvals:
                    self._session_approvals["current_session"] = set()
                self._session_approvals["current_session"].add(command_key)
                
            elif action == "allow_always":
                record.approved = True
                record.approver = approver
                record.approval_time = time.time()
                record.status = "approved"
                
                # 添加到永久批准列表
                command_key = self._normalize_command_key(record.command)
                self._permanent_approvals.add(command_key)
                
            else:  # deny
                record.approved = False
                record.approver = approver
                record.approval_time = time.time()
                record.status = "denied"
            
            # 添加到历史
            self._approval_history.append(record)
            
            logger.info("[ApprovalManager] Approval %s: %s by %s", 
                       approval_id, action, approver)
        
        return ApprovalResult(
            approval_id=approval_id,
            approved=record.approved,
            approver=approver,
            session_approve=(action == "allow_session"),
        )
    
    def _normalize_command_key(self, command: str) -> str:
        """标准化命令用于比较"""
        # 提取命令的主要部分（去掉参数）
        parts = command.strip().split()
        if parts:
            return parts[0].lower()
        return command.lower()
    
    def is_pre_approved(self, command: str, session_key: str = "") -> bool:
        """
        检查命令是否已预先批准
        
        Args:
            command: 命令
            session_key: 会话密钥
        
        Returns:
            是否已批准
        """
        command_key = self._normalize_command_key(command)
        
        # 检查永久批准
        if command_key in self._permanent_approvals:
            return True
        
        # 检查会话批准
        if session_key and session_key in self._session_approvals:
            if command_key in self._session_approvals[session_key]:
                return True
        
        return False
    
    async def get_pending_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        """获取待审批记录"""
        return self._pending_approvals.get(approval_id)
    
    async def get_all_pending(self) -> List[ApprovalRecord]:
        """获取所有待审批记录"""
        return list(self._pending_approvals.values())
    
    def record_approval(
        self,
        command: str,
        approver: str = "",
        session_approve: bool = False,
    ) -> None:
        """
        记录命令批准 (用于命令引擎)
        
        Args:
            command: 命令
            approver: 审批人
            session_approve: 是否会话级批准
        """
        command_key = self._normalize_command_key(command)
        
        if session_approve:
            if "current_session" not in self._session_approvals:
                self._session_approvals["current_session"] = set()
            self._session_approvals["current_session"].add(command_key)
    
    def clear_session_approvals(self, session_key: str = "current_session") -> None:
        """清除会话批准"""
        self._session_approvals.pop(session_key, None)
    
    def get_approval_stats(self) -> Dict[str, Any]:
        """获取审批统计"""
        total = len(self._approval_history)
        approved = sum(1 for r in self._approval_history if r.approved)
        denied = total - approved
        
        return {
            'total_approvals': total,
            'approved': approved,
            'denied': denied,
            'pending': len(self._pending_approvals),
            'permanent_approvals': len(self._permanent_approvals),
            'session_approvals': sum(len(v) for v in self._session_approvals.values()),
        }
