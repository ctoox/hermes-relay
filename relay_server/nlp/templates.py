"""
Hermes Relay - 命令模板管理器
提供命令模板的定义和匹配
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CommandTemplate:
    """命令模板"""
    name: str                              # 模板名称
    patterns: List[str]                    # 匹配模式
    template: str                          # 命令模板 (使用 {0}, {1} 等占位符)
    description: str = ""                  # 描述
    examples: List[str] = field(default_factory=list)  # 示例
    require_approval: bool = False         # 是否需要审批
    
    # 编译后的正则表达式
    _compiled_patterns: List[re.Pattern] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """编译正则表达式"""
        for pattern in self.patterns:
            try:
                self._compiled_patterns.append(
                    re.compile(pattern, re.IGNORECASE | re.UNICODE)
                )
            except re.error as e:
                logger.error("[Template] Invalid pattern '%s': %s", pattern, e)
    
    def match(self, text: str) -> Optional[Tuple[str, Dict[str, any]]]:
        """
        尝试匹配文本
        
        Args:
            text: 输入文本
        
        Returns:
            匹配成功返回 (命令, 元数据)，否则返回 None
        """
        for pattern in self._compiled_patterns:
            match = pattern.search(text)
            if match:
                args = match.groups()
                
                try:
                    command = self.template.format(*args)
                except (IndexError, KeyError):
                    command = self.template
                
                metadata = {
                    "template_name": self.name,
                    "description": self.description,
                    "require_approval": self.require_approval,
                    "args": args,
                }
                
                return command, metadata
        
        return None


class TemplateManager:
    """
    模板管理器
    
    管理命令模板，提供模板匹配功能
    """
    
    def __init__(self):
        self._templates: List[CommandTemplate] = []
        self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """加载默认模板"""
        templates = [
            # 打开应用程序
            CommandTemplate(
                name="open_app",
                patterns=[
                    r"(?:打开|启动|运行)\s*(.+?)(?:\s*程序)?(?:\s*$)",
                    r"(?:open|start|run)\s+(.+?)(?:\s*$)",
                ],
                template="start {0}",
                description="打开应用程序",
                examples=["打开记事本", "启动计算器", "运行 cmd"],
            ),
            
            # 在指定目录执行命令
            CommandTemplate(
                name="in_directory",
                patterns=[
                    r"(?:在|到)\s*(.+?)\s*(?:目录|文件夹)?(?:里|下|中|内)?(?:执行|运行|运行)\s*(.+)",
                    r"(?:in|at|under)\s+(.+?)\s+(?:directory|folder)?(?:execute|run)\s+(.+)",
                ],
                template='cd /d "{0}" && {1}',
                description="在指定目录执行命令",
                examples=["在 C:\\temp 目录下执行 dir"],
            ),
            
            # 查找文件
            CommandTemplate(
                name="find_file",
                patterns=[
                    r"(?:查找|搜索|找)(?:文件)?\s*(.+?)(?:\s*文件)?",
                    r"(?:find|search|look\s+for)(?:\s+file)?\s+(.+)",
                ],
                template='dir /s /b *{0}*',
                description="查找文件",
                examples=["查找 config.ini", "搜索 .txt 文件"],
            ),
            
            # 复制文件
            CommandTemplate(
                name="copy_file",
                patterns=[
                    r"(?:复制|拷贝)(?:文件)?\s*(.+?)\s*(?:到|至)\s*(.+)",
                    r"(?:copy|cp)(?:\s+file)?\s+(.+?)\s+(?:to)\s+(.+)",
                ],
                template='copy "{0}" "{1}"',
                description="复制文件",
                examples=["复制 file.txt 到 backup/"],
            ),
            
            # 移动文件
            CommandTemplate(
                name="move_file",
                patterns=[
                    r"(?:移动|剪切)(?:文件)?\s*(.+?)\s*(?:到|至)\s*(.+)",
                    r"(?:move|mv)(?:\s+file)?\s+(.+?)\s+(?:to)\s+(.+)",
                ],
                template='move "{0}" "{1}"',
                description="移动文件",
                examples=["移动 file.txt 到 archive/"],
            ),
            
            # 删除文件 (需要审批)
            CommandTemplate(
                name="delete_file",
                patterns=[
                    r"(?:删除|删掉|移除)(?:文件)?\s*(.+)",
                    r"(?:delete|remove|del|rm)(?:\s+file)?\s+(.+)",
                ],
                template='del "{0}"',
                description="删除文件",
                examples=["删除 temp.txt"],
                require_approval=True,
            ),
            
            # 查看服务状态
            CommandTemplate(
                name="service_status",
                patterns=[
                    r"(?:查看|检查|显示)(?:服务)\s*(.+?)(?:\s*的状态)?",
                    r"(?:check|show|view)(?:\s+service)?\s+(.+?)\s*(?:status)?",
                ],
                template='sc query {0}',
                description="查看服务状态",
                examples=["查看 wuauserv 服务"],
            ),
            
            # 重启服务
            CommandTemplate(
                name="restart_service",
                patterns=[
                    r"(?:重启|重新启动)(?:服务)\s*(.+)",
                    r"(?:restart)(?:\s+service)?\s+(.+)",
                ],
                template='net stop {0} && net start {0}',
                description="重启服务",
                examples=["重启 spooler 服务"],
                require_approval=True,
            ),
            
            # 测试网络连通性
            CommandTemplate(
                name="test_connection",
                patterns=[
                    r"(?:测试|检查|ping)\s*(.+?)(?:\s*的)?(?:\s*连通性|连接)?",
                    r"(?:test|check|ping)\s+(.+?)(?:\s*connection)?",
                ],
                template="ping -n 4 {0}",
                description="测试网络连通性",
                examples=["测试 8.8.8.8", "ping google.com"],
            ),
            
            # 下载文件
            CommandTemplate(
                name="download_file",
                patterns=[
                    r"(?:下载)\s*(.+?)(?:\s*到|至)\s*(.+)",
                    r"(?:download)\s+(.+?)\s+(?:to)\s+(.+)",
                ],
                template='curl -L -o "{1}" "{0}"',
                description="下载文件",
                examples=["下载 http://example.com/file.zip 到 C:\\downloads\\"],
                require_approval=True,
            ),
        ]
        
        for template in templates:
            self.add_template(template)
    
    def add_template(self, template: CommandTemplate) -> None:
        """添加模板"""
        self._templates.append(template)
    
    def remove_template(self, name: str) -> bool:
        """移除模板"""
        for i, template in enumerate(self._templates):
            if template.name == name:
                self._templates.pop(i)
                return True
        return False
    
    def match(self, text: str) -> Optional[Tuple[str, Dict[str, any]]]:
        """
        匹配文本
        
        Args:
            text: 输入文本
        
        Returns:
            匹配成功返回 (命令, 元数据)，否则返回 None
        """
        for template in self._templates:
            result = template.match(text)
            if result:
                return result
        
        return None
    
    def get_templates(self) -> List[CommandTemplate]:
        """获取所有模板"""
        return self._templates.copy()
    
    def get_template_by_name(self, name: str) -> Optional[CommandTemplate]:
        """根据名称获取模板"""
        for template in self._templates:
            if template.name == name:
                return template
        return None
