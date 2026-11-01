"""
Hermes Relay - Windows 命令执行器
在 Windows 系统上执行命令
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """命令执行结果"""
    command_id: str
    status: str  # success/error/timeout/cancelled
    output: str = ""
    error_output: str = ""
    exit_code: Optional[int] = None
    execution_time: float = 0.0


class CommandExecutor:
    """
    Windows 命令执行器
    
    支持：
    - 前台/后台执行
    - 超时控制
    - 取消执行
    - 并发执行
    """
    
    def __init__(self, default_timeout: int = 60, max_concurrent: int = 5):
        """
        初始化命令执行器
        
        Args:
            default_timeout: 默认超时时间(秒)
            max_concurrent: 最大并发数
        """
        self._default_timeout = default_timeout
        self._max_concurrent = max_concurrent
        
        # 执行中的命令
        self._running_commands: Dict[str, asyncio.subprocess.Process] = {}
        self._command_tasks: Dict[str, asyncio.Task] = {}
        
        # 并发控制
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        self._lock = asyncio.Lock()
    
    @property
    def active_count(self) -> int:
        """活跃命令数"""
        return len(self._running_commands)
    
    async def execute(
        self,
        command: str,
        command_id: Optional[str] = None,
        working_dir: str = "",
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            command_id: 命令ID (可选)
            working_dir: 工作目录
            timeout: 超时时间
            env_vars: 环境变量
        
        Returns:
            命令执行结果
        """
        command_id = command_id or str(uuid.uuid4())
        timeout = timeout or self._default_timeout
        
        # 准备环境变量
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # 准备工作目录
        if working_dir and not os.path.isdir(working_dir):
            working_dir = ""
        
        start_time = time.time()
        
        try:
            # 使用信号量控制并发
            async with self._semaphore:
                result = await self._execute_command(
                    command_id=command_id,
                    command=command,
                    working_dir=working_dir,
                    timeout=timeout,
                    env=env,
                )
        except asyncio.CancelledError:
            result = CommandResult(
                command_id=command_id,
                status="cancelled",
                output="命令被取消",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            result = CommandResult(
                command_id=command_id,
                status="error",
                error_output=str(e),
                execution_time=time.time() - start_time,
            )
        
        return result
    
    async def _execute_command(
        self,
        command_id: str,
        command: str,
        working_dir: str,
        timeout: int,
        env: Dict[str, str],
    ) -> CommandResult:
        """执行命令 (内部方法)"""
        start_time = time.time()
        process = None
        
        try:
            # 创建子进程
            # 使用 cmd /c 执行命令，这样可以支持管道、重定向等
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir if working_dir else None,
                env=env,
                # Windows 特定：隐藏控制台窗口
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
            
            # 记录运行中的进程
            async with self._lock:
                self._running_commands[command_id] = process
            
            try:
                # 等待命令完成，带超时
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
                
                # 解码输出
                output = self._decode_output(stdout)
                error_output = self._decode_output(stderr)
                
                exit_code = process.returncode
                
                if exit_code == 0:
                    status = "success"
                else:
                    status = "error"
                
                return CommandResult(
                    command_id=command_id,
                    status=status,
                    output=output,
                    error_output=error_output,
                    exit_code=exit_code,
                    execution_time=time.time() - start_time,
                )
                
            except asyncio.TimeoutError:
                # 超时，终止进程
                logger.warning("[Executor] Command timeout: %s", command[:100])
                await self._kill_process(process)
                
                return CommandResult(
                    command_id=command_id,
                    status="timeout",
                    output="命令执行超时",
                    execution_time=time.time() - start_time,
                )
                
        except asyncio.CancelledError:
            # 命令被取消
            if process:
                await self._kill_process(process)
            raise
            
        except Exception as e:
            logger.error("[Executor] Execution error: %s", e, exc_info=True)
            return CommandResult(
                command_id=command_id,
                status="error",
                error_output=str(e),
                execution_time=time.time() - start_time,
            )
            
        finally:
            # 从运行列表中移除
            async with self._lock:
                self._running_commands.pop(command_id, None)
    
    async def _kill_process(self, process: asyncio.subprocess.Process) -> None:
        """终止进程"""
        try:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        except Exception as e:
            logger.error("[Executor] Error killing process: %s", e)
    
    def _decode_output(self, data: bytes) -> str:
        """解码输出"""
        if not data:
            return ""
        
        # 尝试多种编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                return data.decode(encoding).strip()
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 如果都失败，使用 latin-1 (不会失败)
        return data.decode('latin-1').strip()
    
    async def cancel(self, command_id: str) -> bool:
        """
        取消命令
        
        Args:
            command_id: 命令ID
        
        Returns:
            是否成功取消
        """
        async with self._lock:
            process = self._running_commands.get(command_id)
            if process:
                await self._kill_process(process)
                return True
            
            task = self._command_tasks.get(command_id)
            if task and not task.done():
                task.cancel()
                return True
        
        return False
    
    async def cancel_all(self) -> int:
        """
        取消所有命令
        
        Returns:
            取消的命令数
        """
        cancelled = 0
        
        async with self._lock:
            for command_id, process in list(self._running_commands.items()):
                await self._kill_process(process)
                cancelled += 1
            
            for command_id, task in list(self._command_tasks.items()):
                if not task.done():
                    task.cancel()
                    cancelled += 1
        
        return cancelled
    
    def get_running_commands(self) -> List[str]:
        """获取运行中的命令ID列表"""
        return list(self._running_commands.keys())
