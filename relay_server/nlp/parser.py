"""
Hermes Relay - NLP 解析器
将自然语言转换为系统命令
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from .rules import Rule, RuleEngine
from .templates import CommandTemplate, TemplateManager

logger = logging.getLogger(__name__)


class NLPParser:
    """
    自然语言解析器
    """
    
    def __init__(self):
        self._rule_engine = RuleEngine()
        self._template_manager = TemplateManager()
        self._load_default_rules()
        self._context: Dict[str, any] = {}
    
    def _load_default_rules(self) -> None:
        """加载默认规则 (按优先级排序)"""
        rules = [
            # ===== 系统信息 (最高优先级) =====
            # 查看IP地址
            Rule(
                patterns=[
                    r"(?:查看|显示|看看)(?:本机)?(?:IP|ip|网络|网卡)(?:地址|信息)?",
                    r"(?:show|view|check|display)(?:\s+my)?(?:\s+ip|\s+network|\s+nic)?",
                    r"^ipconfig$",
                ],
                command="ipconfig /all",
                description="查看IP配置",
                priority=10,
            ),
            
            # 查看系统信息
            Rule(
                patterns=[
                    r"(?:查看|显示|看看)(?:系统|电脑|计算机)(?:信息|配置|状态)",
                    r"(?:show|view|check)(?:\s+system)?(?:\s+info|\s+config|\s+status)?",
                    r"^systeminfo$",
                ],
                command="systeminfo",
                description="查看系统信息",
                priority=10,
            ),
            
            # 查看进程
            Rule(
                patterns=[
                    r"(?:查看|显示|列出|看看)(?:当前)?(?:进程|程序|任务)(?:列表)?",
                    r"(?:list|show|view)(?:\s+current)?(?:\s+process|\s+program|\s+task)?",
                    r"^tasklist$",
                ],
                command="tasklist /V",
                description="查看进程列表",
                priority=10,
            ),
            
            # 查看端口
            Rule(
                patterns=[
                    r"(?:查看|显示|检查)(?:当前)?(?:端口|连接|网络状态)",
                    r"(?:show|view|check)(?:\s+current)?(?:\s+port|\s+connection|\s+network)?",
                    r"^netstat$",
                ],
                command="netstat -ano",
                description="查看网络连接",
                priority=10,
            ),
            
            # 查看时间
            Rule(
                patterns=[
                    r"(?:查看|显示|看看)(?:当前)?(?:时间|日期)",
                    r"(?:show|what)\s+(?:time|date)",
                    r"^time$",
                    r"^date$",
                ],
                command="echo %date% %time%",
                description="查看当前时间",
                priority=10,
            ),
            
            # ===== 截图功能 (高优先级) =====
            Rule(
                patterns=[
                    r"(?:截图|截屏|屏幕截图|抓屏|屏幕捕获)",
                    r"(?:screenshot|capture|screen\s*shot|print\s*screen)",
                ],
                command="screenshot",
                description="截图",
                priority=9,
                special_action="screenshot",
            ),
            
            # ===== 鼠标操作 (高优先级) =====
            # 点击指定位置
            Rule(
                patterns=[
                    r"(?:点击|单击|鼠标点击)\s*(\d+)\s*[，,]\s*(\d+)",
                    r"(?:click|tap)\s+(\d+)\s*[，,]\s*(\d+)",
                    r"(?:点击|单击)\s*坐标\s*(\d+)\s*[，,]\s*(\d+)",
                ],
                command="mouse_click {0} {1}",
                description="点击指定坐标",
                extract_args=True,
                priority=9,
                special_action="mouse_click",
            ),
            
            # 鼠标移动
            Rule(
                patterns=[
                    r"(?:移动|鼠标移动)(?:到)?\s*(\d+)\s*[，,]\s*(\d+)",
                    r"(?:move\s+mouse|mouse\s+move)\s+(\d+)\s*[，,]\s*(\d+)",
                ],
                command="mouse_move {0} {1}",
                description="移动鼠标到指定坐标",
                extract_args=True,
                priority=9,
                special_action="mouse_move",
            ),
            
            # 双击
            Rule(
                patterns=[
                    r"(?:双击)\s*(\d+)\s*[，,]\s*(\d+)",
                    r"(?:double\s*click)\s+(\d+)\s*[，,]\s*(\d+)",
                ],
                command="mouse_double_click {0} {1}",
                description="双击指定坐标",
                extract_args=True,
                priority=9,
                special_action="mouse_double_click",
            ),
            
            # 右键点击
            Rule(
                patterns=[
                    r"(?:右键|右击)\s*(\d+)\s*[，,]\s*(\d+)",
                    r"(?:right\s*click)\s+(\d+)\s*[，,]\s*(\d+)",
                ],
                command="mouse_right_click {0} {1}",
                description="右键点击指定坐标",
                extract_args=True,
                priority=9,
                special_action="mouse_right_click",
            ),
            
            # ===== 文件传输 (高优先级) =====
            # 发送文件
            Rule(
                patterns=[
                    r"(?:发送|传输|上传)(?:文件)?\s*(.+)",
                    r"(?:send|transfer|upload)(?:\s+file)?\s+(.+)",
                ],
                command="file_send {0}",
                description="发送文件",
                extract_args=True,
                priority=9,
                special_action="file_send",
            ),
            
            # 接收文件
            Rule(
                patterns=[
                    r"(?:接收|下载)(?:文件)?\s*(.+)",
                    r"(?:receive|download)(?:\s+file)?\s+(.+)",
                ],
                command="file_receive {0}",
                description="接收文件",
                extract_args=True,
                priority=9,
                special_action="file_receive",
            ),
            
            # ===== 设备管理 (高优先级) =====
            # 设备列表
            Rule(
                patterns=[
                    r"(?:设备列表|设备|查看设备|显示设备|所有设备)",
                    r"(?:device|device\s+list|show\s+device|all\s+device)",
                ],
                command="device_list",
                description="查看设备列表",
                priority=9,
                special_action="device_list",
            ),
            
            # ===== 帮助 (高优先级) =====
            Rule(
                patterns=[
                    r"^(?:帮助|帮忙|怎么用|使用方法|命令|菜单)$",
                    r"^(?:help|usage|how\s+to|command|menu)$",
                ],
                command="help",
                description="显示帮助",
                priority=9,
                special_action="help",
            ),
            
            # ===== 文件和目录操作 (中优先级) =====
            # 查看目录
            Rule(
                patterns=[
                    r"(?:查看|显示|列出|看看)(?:当前)?(?:目录|文件夹|文件)(?:内容)?",
                    r"(?:list|show|view)(?:\s+current)?(?:\s+directory|\s+folder|\s+files)?",
                    r"^dir$",
                    r"^ls$",
                ],
                command="dir",
                description="查看当前目录内容",
                priority=5,
            ),
            
            # 查看指定目录
            Rule(
                patterns=[
                    r"(?:查看|显示|列出)(?:目录|文件夹)\s+(.+)",
                    r"(?:list|show|view)(?:\s+directory|\s+folder)\s+(.+)",
                ],
                command="dir {0}",
                description="查看指定目录内容",
                extract_args=True,
                priority=5,
            ),
            
            # 创建目录
            Rule(
                patterns=[
                    r"(?:创建|新建|建立)(?:目录|文件夹)\s+(.+)",
                    r"(?:create|make|new)(?:\s+directory|\s+folder)\s+(.+)",
                    r"^mkdir\s+(.+)",
                ],
                command="mkdir {0}",
                description="创建目录",
                extract_args=True,
                priority=5,
            ),
            
            # 切换目录
            Rule(
                patterns=[
                    r"(?:切换|进入|打开)(?:到)?(?:目录|文件夹)\s+(.+)",
                    r"(?:cd|change\s+to|goto)\s+(.+)",
                ],
                command="cd /d {0}",
                description="切换目录",
                extract_args=True,
                priority=5,
            ),
            
            # ===== 应用程序 (中优先级) =====
            # 打开记事本
            Rule(
                patterns=[
                    r"(?:打开|启动|运行)记事本",
                    r"(?:open|start|run)\s+notepad",
                    r"^notepad$",
                ],
                command="start notepad",
                description="打开记事本",
                priority=5,
            ),
            
            # 打开计算器
            Rule(
                patterns=[
                    r"(?:打开|启动|运行)计算器",
                    r"(?:open|start|run)\s+calc(?:ulator)?",
                    r"^calc$",
                ],
                command="start calc",
                description="打开计算器",
                priority=5,
            ),
            
            # 打开命令提示符
            Rule(
                patterns=[
                    r"(?:打开|启动|运行)(?:命令行|cmd|终端|命令提示符)",
                    r"(?:open|start|run)\s+(?:cmd|command|terminal)",
                    r"^cmd$",
                ],
                command="start cmd",
                description="打开命令提示符",
                priority=5,
            ),
            
            # 打开资源管理器
            Rule(
                patterns=[
                    r"(?:打开|启动|运行)(?:资源管理器|文件管理器|我的电脑|此电脑)",
                    r"(?:open|start|run)\s+(?:explorer|file\s+manager)",
                    r"^explorer$",
                ],
                command="start explorer",
                description="打开资源管理器",
                priority=5,
            ),
            
            # 打开任务管理器
            Rule(
                patterns=[
                    r"(?:打开|启动|运行)(?:任务管理器)",
                    r"(?:open|start|run)\s+task\s*manager",
                    r"^taskmgr$",
                ],
                command="start taskmgr",
                description="打开任务管理器",
                priority=5,
            ),
            
            # ===== 进程管理 (中优先级) =====
            # 查找指定进程
            Rule(
                patterns=[
                    r"(?:查看|查找|搜索)(?:进程)?\s+(.+)",
                    r"(?:find|search|look\s+for)(?:\s+process)?\s+(.+)",
                ],
                command='tasklist /FI "IMAGENAME eq {0}*"',
                description="查找指定进程",
                extract_args=True,
                priority=5,
            ),
            
            # 关闭进程 (需要审批)
            Rule(
                patterns=[
                    r"(?:关闭|结束|杀死|停止|杀掉)(?:进程)?\s+(.+)",
                    r"(?:kill|stop|close|terminate|end)(?:\s+process)?\s+(.+)",
                    r"^taskkill\s+(.+)",
                ],
                command='taskkill /IM {0} /F',
                description="关闭进程",
                extract_args=True,
                require_approval=True,
                priority=5,
            ),
            
            # ===== 网络操作 (中优先级) =====
            # Ping测试
            Rule(
                patterns=[
                    r"(?:ping|测试|检查)(?:到)?\s+(.+?)(?:\s*的)?(?:\s*连接)?",
                    r"^ping\s+(.+)",
                ],
                command="ping -n 4 {0}",
                description="Ping测试",
                extract_args=True,
                priority=5,
            ),
            
            # ===== 其他操作 (低优先级) =====
            # 清屏
            Rule(
                patterns=[
                    r"^(?:清屏|清除屏幕|清除)$",
                    r"^(?:clear|cls)$",
                ],
                command="cls",
                description="清屏",
                priority=1,
            ),
            
            # 查看文件内容 (低优先级，避免与系统信息冲突)
            Rule(
                patterns=[
                    r"(?:查看|显示|打开|读取)(?:文件)?\s+(.+?)(?:\s*的)?(?:内容)?",
                    r"(?:cat|type|view|read|show)\s+(.+)",
                ],
                command="type {0}",
                description="查看文件内容",
                extract_args=True,
                priority=1,
            ),
        ]
        
        for rule in rules:
            self._rule_engine.add_rule(rule)
    
    def parse(self, text: str) -> Tuple[Optional[str], Dict[str, any]]:
        """
        解析自然语言文本
        
        Args:
            text: 输入文本
        
        Returns:
            (命令, 元数据) 的元组，如果没有匹配返回 (None, {})
        """
        text = text.strip()
        if not text:
            return None, {}
        
        # 尝试规则匹配
        result = self._rule_engine.match(text)
        if result:
            command, metadata = result
            logger.debug("[NLP] Matched rule: %s -> %s", text, command)
            return command, metadata
        
        # 尝试模板匹配
        template_result = self._template_manager.match(text)
        if template_result:
            command, metadata = template_result
            logger.debug("[NLP] Matched template: %s -> %s", text, command)
            return command, metadata
        
        # 如果没有匹配，检查是否直接是命令
        if self._looks_like_command(text):
            logger.debug("[NLP] Direct command: %s", text)
            return text, {"type": "direct_command"}
        
        logger.debug("[NLP] No match for: %s", text)
        return None, {}
    
    def _looks_like_command(self, text: str) -> bool:
        """检查文本是否看起来像命令"""
        cmd_prefixes = [
            "dir", "ls", "cd", "mkdir", "copy", "move", "del", "rm",
            "ipconfig", "ping", "netstat", "tasklist", "taskkill",
            "systeminfo", "whoami", "hostname", "ver", "type",
            "echo", "set", "path", "exit", "shutdown", "restart",
            "net", "sc", "reg", "powershell", "cmd",
        ]
        
        first_word = text.split()[0].lower() if text.split() else ""
        return first_word in cmd_prefixes
    
    def add_rule(self, rule: Rule) -> None:
        """添加自定义规则"""
        self._rule_engine.add_rule(rule)
    
    def add_template(self, template: CommandTemplate) -> None:
        """添加自定义模板"""
        self._template_manager.add_template(template)
    
    def set_context(self, key: str, value: any) -> None:
        """设置上下文"""
        self._context[key] = value
    
    def get_context(self, key: str, default: any = None) -> any:
        """获取上下文"""
        return self._context.get(key, default)
    
    def clear_context(self) -> None:
        """清除上下文"""
        self._context.clear()
