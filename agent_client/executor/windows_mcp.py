"""
Hermes Relay - Windows MCP (Model Context Protocol) 集成
提供与 MCP 服务器的集成，扩展 Agent 能力
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP 服务器配置"""
    
    def __init__(
        self,
        name: str,
        command: str,
        args: List[str] = None,
        env: Dict[str, str] = None,
    ):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self.tools: List[Dict[str, Any]] = []


class WindowsMCP:
    """
    Windows MCP 集成
    
    提供功能:
    - MCP 服务器管理
    - 工具注册和调用
    - 资源访问
    """
    
    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._load_builtin_tools()
    
    def _load_builtin_tools(self) -> None:
        """加载内置工具"""
        # 截图工具
        self._tools["screenshot"] = {
            "name": "screenshot",
            "description": "截取屏幕截图",
            "parameters": {
                "type": "object",
                "properties": {
                    "save_path": {
                        "type": "string",
                        "description": "保存路径 (可选)",
                    },
                },
            },
        }
        
        # 鼠标点击工具
        self._tools["mouse_click"] = {
            "name": "mouse_click",
            "description": "点击指定位置",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X 坐标"},
                    "y": {"type": "integer", "description": "Y 坐标"},
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "description": "鼠标按钮",
                        "default": "left",
                    },
                },
                "required": ["x", "y"],
            },
        }
        
        # 鼠标移动工具
        self._tools["mouse_move"] = {
            "name": "mouse_move",
            "description": "移动鼠标到指定位置",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X 坐标"},
                    "y": {"type": "integer", "description": "Y 坐标"},
                },
                "required": ["x", "y"],
            },
        }
        
        # 键盘输入工具
        self._tools["keyboard_type"] = {
            "name": "keyboard_type",
            "description": "输入文字",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要输入的文字"},
                },
                "required": ["text"],
            },
        }
        
        # 快捷键工具
        self._tools["keyboard_hotkey"] = {
            "name": "keyboard_hotkey",
            "description": "按下快捷键",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "按键列表，如 ['ctrl', 'c']",
                    },
                },
                "required": ["keys"],
            },
        }
        
        # 文件读取工具
        self._tools["read_file"] = {
            "name": "read_file",
            "description": "读取文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "encoding": {
                        "type": "string",
                        "description": "编码格式",
                        "default": "utf-8",
                    },
                },
                "required": ["path"],
            },
        }
        
        # 文件写入工具
        self._tools["write_file"] = {
            "name": "write_file",
            "description": "写入文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "encoding": {
                        "type": "string",
                        "description": "编码格式",
                        "default": "utf-8",
                    },
                },
                "required": ["path", "content"],
            },
        }
        
        # 执行命令工具
        self._tools["execute_command"] = {
            "name": "execute_command",
            "description": "执行系统命令",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间(秒)",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        }
        
        # 获取系统信息工具
        self._tools["system_info"] = {
            "name": "system_info",
            "description": "获取系统信息",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }
        
        # 获取屏幕分辨率工具
        self._tools["screen_size"] = {
            "name": "screen_size",
            "description": "获取屏幕分辨率",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }
        
        # 获取鼠标位置工具
        self._tools["mouse_position"] = {
            "name": "mouse_position",
            "description": "获取当前鼠标位置",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }
    
    # =========================================================================
    # MCP 服务器管理
    # =========================================================================
    
    def add_server(self, server: MCPServer) -> None:
        """添加 MCP 服务器"""
        self._servers[server.name] = server
        logger.info("[MCP] Added server: %s", server.name)
    
    def remove_server(self, name: str) -> bool:
        """移除 MCP 服务器"""
        if name in self._servers:
            server = self._servers[name]
            if server.process:
                server.process.terminate()
            del self._servers[name]
            logger.info("[MCP] Removed server: %s", name)
            return True
        return False
    
    async def start_server(self, name: str) -> bool:
        """启动 MCP 服务器"""
        if name not in self._servers:
            return False
        
        server = self._servers[name]
        
        try:
            env = os.environ.copy()
            env.update(server.env)
            
            server.process = subprocess.Popen(
                [server.command] + server.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            
            logger.info("[MCP] Started server: %s (PID: %s)", name, server.process.pid)
            return True
        except Exception as e:
            logger.error("[MCP] Failed to start server %s: %s", name, e)
            return False
    
    async def stop_server(self, name: str) -> bool:
        """停止 MCP 服务器"""
        if name not in self._servers:
            return False
        
        server = self._servers[name]
        if server.process:
            server.process.terminate()
            server.process = None
            logger.info("[MCP] Stopped server: %s", name)
        
        return True
    
    # =========================================================================
    # 工具管理
    # =========================================================================
    
    def register_tool(self, tool: Dict[str, Any]) -> None:
        """注册工具"""
        name = tool.get("name")
        if name:
            self._tools[name] = tool
            logger.info("[MCP] Registered tool: %s", name)
    
    def unregister_tool(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            logger.info("[MCP] Unregistered tool: %s", name)
            return True
        return False
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """获取指定工具"""
        return self._tools.get(name)
    
    # =========================================================================
    # 工具调用
    # =========================================================================
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
        
        Returns:
            工具执行结果
        """
        if name not in self._tools:
            return {"error": f"Tool not found: {name}"}
        
        # 内置工具处理
        if name == "screenshot":
            return await self._handle_screenshot(arguments)
        elif name == "mouse_click":
            return await self._handle_mouse_click(arguments)
        elif name == "mouse_move":
            return await self._handle_mouse_move(arguments)
        elif name == "keyboard_type":
            return await self._handle_keyboard_type(arguments)
        elif name == "keyboard_hotkey":
            return await self._handle_keyboard_hotkey(arguments)
        elif name == "read_file":
            return await self._handle_read_file(arguments)
        elif name == "write_file":
            return await self._handle_write_file(arguments)
        elif name == "execute_command":
            return await self._handle_execute_command(arguments)
        elif name == "system_info":
            return await self._handle_system_info(arguments)
        elif name == "screen_size":
            return await self._handle_screen_size(arguments)
        elif name == "mouse_position":
            return await self._handle_mouse_position(arguments)
        
        return {"error": f"Tool not implemented: {name}"}
    
    async def _handle_screenshot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理截图工具"""
        from .windows_control import get_controller
        controller = get_controller()
        
        save_path = args.get("save_path")
        path, b64 = controller.screenshot(save_path)
        
        return {
            "path": path,
            "base64": b64[:100] + "..." if len(b64) > 100 else b64,
            "size": len(b64),
        }
    
    async def _handle_mouse_click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理鼠标点击工具"""
        from .windows_control import get_controller
        controller = get_controller()
        
        x = args.get("x", 0)
        y = args.get("y", 0)
        button = args.get("button", "left")
        
        success = controller.mouse_click(x, y, button=button)
        return {"success": success, "x": x, "y": y, "button": button}
    
    async def _handle_mouse_move(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理鼠标移动工具"""
        from .windows_control import get_controller
        controller = get_controller()
        
        x = args.get("x", 0)
        y = args.get("y", 0)
        
        success = controller.mouse_move(x, y)
        return {"success": success, "x": x, "y": y}
    
    async def _handle_keyboard_type(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理键盘输入工具"""
        from .windows_control import get_controller
        controller = get_controller()
        
        text = args.get("text", "")
        success = controller.keyboard_type(text)
        return {"success": success, "text": text}
    
    async def _handle_keyboard_hotkey(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理快捷键工具"""
        from .windows_control import get_controller
        controller = get_controller()
        
        keys = args.get("keys", [])
        success = controller.keyboard_hotkey(*keys)
        return {"success": success, "keys": keys}
    
    async def _handle_read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理文件读取工具"""
        path = args.get("path", "")
        encoding = args.get("encoding", "utf-8")
        
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理文件写入工具"""
        path = args.get("path", "")
        content = args.get("content", "")
        encoding = args.get("encoding", "utf-8")
        
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_execute_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理命令执行工具"""
        command = args.get("command", "")
        timeout = args.get("timeout", 30)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_system_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理系统信息工具"""
        import platform
        import psutil
        
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "hostname": platform.node(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "memory_percent": psutil.virtual_memory().percent,
        }
    
    async def _handle_screen_size(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理屏幕分辨率工具"""
        from .windows_control import get_controller
        controller = get_controller()
        
        width, height = controller.get_screen_size()
        return {"width": width, "height": height}
    
    async def _handle_mouse_position(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """处理鼠标位置工具"""
        from .windows_control import get_controller
        controller = get_controller()
        
        x, y = controller.get_mouse_position()
        return {"x": x, "y": y}


# 全局实例
_mcp: Optional[WindowsMCP] = None


def get_mcp() -> WindowsMCP:
    """获取全局 MCP 实例"""
    global _mcp
    if _mcp is None:
        _mcp = WindowsMCP()
    return _mcp
