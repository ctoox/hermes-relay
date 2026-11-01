"""
Hermes Relay - 命令白名单
定义安全命令、危险命令和禁止命令
"""

from __future__ import annotations

import re
import logging
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """风险等级"""
    SAFE = "safe"           # 安全命令，无需审批
    LOW = "low"             # 低风险，无需审批
    MEDIUM = "medium"       # 中等风险，需要审批
    HIGH = "high"           # 高风险，需要审批
    CRITICAL = "critical"   # 危险命令，需要审批
    BLOCKED = "blocked"     # 禁止命令


class CommandWhitelist:
    """
    命令白名单管理器
    
    提供命令安全检查，包括：
    - 安全命令白名单
    - 危险命令黑名单
    - 禁止命令列表
    - 正则表达式匹配
    """
    
    def __init__(self):
        # 安全命令 (无需审批)
        self._safe_commands: Set[str] = {
            # 文件浏览
            "dir", "ls", "ll", "la", "tree", "find", "where",
            "type", "cat", "head", "tail", "more", "less",
            
            # 系统信息
            "whoami", "hostname", "ver", "systeminfo",
            "ipconfig", "ifconfig", "ip", "netstat", "nslookup",
            "ping", "tracert", "pathping", "arp",
            
            # 进程查看
            "tasklist", "ps", "top", "htop",
            
            # 磁盘和文件系统
            "vol", "label", "fsutil", "chkdsk",
            "df", "du", "mount",
            
            # 网络
            "net", "nbtstat", "route",
            
            # 时间和日期
            "date", "time", "tzutil",
            
            # 环境变量
            "set", "echo", "env", "printenv",
            
            # 其他
            "cls", "clear", "history", "help", "man",
            "pwd", "cd", "pushd", "popd",
            "md5sum", "sha256sum", "certutil",
        }
        
        # 低风险命令 (无需审批，但可能有轻微影响)
        self._low_risk_commands: Set[str] = {
            # 文件操作 (非删除)
            "copy", "xcopy", "robocopy", "move", "ren", "rename",
            "mkdir", "md", "touch",
            
            # 文本处理
            "findstr", "grep", "awk", "sed", "sort", "uniq",
            "wc", "diff", "comp",
            
            # 压缩
            "tar", "gzip", "gunzip", "zip", "unzip",
            "7z", "rar", "unrar",
            
            # 系统监控
            "perfmon", "resmon", "eventvwr",
            
            # 服务查看
            "sc query", "net start",
        }
        
        # 中等风险命令 (需要审批)
        self._medium_risk_commands: Set[str] = {
            # 进程管理
            "taskkill", "kill", "killall",
            
            # 服务管理
            "sc", "net start", "net stop",
            
            # 注册表查看
            "reg query", "reg list",
            
            # 计划任务
            "schtasks /query", "at",
            
            # 用户管理 (查看)
            "net user", "net localgroup",
            "whoami /priv", "whoami /groups",
        }
        
        # 高风险命令 (需要审批)
        self._high_risk_commands: Set[str] = {
            # 文件删除
            "del", "erase", "rm", "rmdir", "rd",
            
            # 注册表修改
            "reg add", "reg delete", "reg import", "reg export",
            
            # 服务管理 (修改)
            "sc config", "sc create", "sc delete",
            
            # 用户管理 (修改)
            "net user /add", "net user /delete",
            "net localgroup /add", "net localgroup /delete",
            
            # 网络配置
            "netsh", "ipconfig /release", "ipconfig /renew",
            "ipconfig /flushdns",
            
            # 计划任务 (修改)
            "schtasks /create", "schtasks /delete", "schtasks /run",
            
            # 系统配置
            "bcdedit", "bootcfg",
            
            # PowerShell
            "powershell", "pwsh",
        }
        
        # 危险命令 (需要审批，高风险)
        self._critical_risk_commands: Set[str] = {
            # 系统关机/重启
            "shutdown", "restart", "logoff",
            
            # 磁盘操作
            "format", "diskpart", "clean", "convert",
            
            # 系统恢复
            "recover", "restore",
            
            # 驱动程序
            "driverquery", "pnputil",
            
            # Windows 功能
            "dism", "sfc",
            
            # 系统更新
            "wuauclt", "usoclient",
        }
        
        # 禁止命令 (永远不允许)
        self._blocked_patterns: List[Tuple[str, str]] = [
            # 格式化系统盘
            (r"format\s+[cC]:", "禁止格式化系统盘"),
            (r"format\s+/[qQyY]\s+[cC]:", "禁止格式化系统盘"),
            
            # 删除系统关键目录
            (r"rd\s+/[sS]\s+/[qQ]\s+[cC]:\\", "禁止删除系统根目录"),
            (r"rm\s+-[rRfF]*\s+/", "禁止删除根目录"),
            (r"del\s+/[sS]\s+/[qQ]\s+[cC]:\\", "禁止删除系统盘文件"),
            
            # 破坏性操作
            (r"echo\s+.*>\s*\\\\\\.\\PhysicalDrive", "禁止直接写入物理磁盘"),
            (r"dd\s+if=.*of=", "禁止磁盘镜像操作"),
            
            # 危险的 PowerShell
            (r"Invoke-Expression.*DownloadString", "禁止远程代码执行"),
            (r"IEX\s*\(.*Net\.WebClient", "禁止远程代码执行"),
            (r"powershell.*-enc\s", "禁止编码命令执行"),
            
            # 注册表破坏
            (r"reg\s+delete\s+HKLM\\SYSTEM", "禁止删除系统注册表"),
            (r"reg\s+delete\s+HKLM\\SOFTWARE", "禁止删除软件注册表"),
            
            # 网络破坏
            (r"netsh\s+firewall\s+set\s+opmode\s+disable", "禁止禁用防火墙"),
            (r"netsh\s+advfirewall\s+set\s+allprofiles\s+state\s+off", "禁止禁用防火墙"),
        ]
        
        # 需要审批的命令模式 (正则表达式)
        self._approval_patterns: List[Tuple[str, str, RiskLevel]] = [
            # 删除文件 (带通配符)
            (r"del\s+.*\*.*", "删除文件操作", RiskLevel.HIGH),
            (r"rm\s+.*\*.*", "删除文件操作", RiskLevel.HIGH),
            
            # 修改系统设置
            (r"reg\s+(add|delete|import)", "注册表修改", RiskLevel.HIGH),
            (r"sc\s+(config|create|delete)", "服务配置修改", RiskLevel.HIGH),
            
            # 用户管理
            (r"net\s+user\s+\S+\s+/", "用户管理操作", RiskLevel.MEDIUM),
            (r"net\s+localgroup\s+\S+\s+/", "用户组管理", RiskLevel.MEDIUM),
            
            # 网络配置
            (r"netsh\s+.*set\s+", "网络配置修改", RiskLevel.HIGH),
            (r"ipconfig\s+/(release|renew|flushdns)", "网络配置修改", RiskLevel.MEDIUM),
            
            # 计划任务
            (r"schtasks\s+/(create|delete|run)", "计划任务管理", RiskLevel.MEDIUM),
            
            # PowerShell 脚本执行
            (r"powershell.*-[eE]xecutionPolicy", "PowerShell策略修改", RiskLevel.HIGH),
            (r"powershell.*Set-ExecutionPolicy", "PowerShell策略修改", RiskLevel.HIGH),
        ]
    
    def check_command(self, command: str) -> RiskLevel:
        """
        检查命令风险等级
        
        Args:
            command: 要检查的命令
        
        Returns:
            风险等级
        """
        command = command.strip()
        if not command:
            return RiskLevel.SAFE
        
        # 提取命令名 (第一个单词)
        cmd_parts = command.split()
        cmd_name = cmd_parts[0].lower() if cmd_parts else ""
        
        # 检查禁止命令
        for pattern, reason in self._blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                logger.warning("[Whitelist] Blocked command: %s (reason: %s)", command, reason)
                return RiskLevel.BLOCKED
        
        # 检查需要审批的模式
        for pattern, reason, risk_level in self._approval_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                logger.info("[Whitelist] Command requires approval: %s (reason: %s, risk: %s)", 
                           command, reason, risk_level.value)
                return risk_level
        
        # 检查安全命令
        if cmd_name in self._safe_commands:
            return RiskLevel.SAFE
        
        # 检查低风险命令
        if cmd_name in self._low_risk_commands:
            return RiskLevel.LOW
        
        # 检查中等风险命令
        if cmd_name in self._medium_risk_commands:
            return RiskLevel.MEDIUM
        
        # 检查高风险命令
        if cmd_name in self._high_risk_commands:
            return RiskLevel.HIGH
        
        # 检查危险命令
        if cmd_name in self._critical_risk_commands:
            return RiskLevel.CRITICAL
        
        # 默认需要审批 (未知命令)
        logger.info("[Whitelist] Unknown command requires approval: %s", command)
        return RiskLevel.MEDIUM
    
    def add_safe_command(self, command: str) -> None:
        """添加安全命令"""
        self._safe_commands.add(command.lower())
    
    def add_blocked_pattern(self, pattern: str, reason: str) -> None:
        """添加禁止命令模式"""
        self._blocked_patterns.append((pattern, reason))
    
    def get_safe_commands(self) -> Set[str]:
        """获取所有安全命令"""
        return self._safe_commands.copy()
    
    def get_blocked_patterns(self) -> List[Tuple[str, str]]:
        """获取所有禁止模式"""
        return self._blocked_patterns.copy()
