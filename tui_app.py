"""
Hermes Relay - TUI 终端界面
类似 Hermes Agent --tui 的现代化终端 UI
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Log,
    ProgressBar,
    RichLog,
    Rule,
    Select,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)


# ============================================================================
# 样式定义
# ============================================================================

CSS = """
Screen {
    background: #0a0a0f;
}

#sidebar {
    width: 30;
    background: #0d0d14;
    border-right: tall #1a1a2e;
    padding: 1 2;
}

#main {
    background: #0a0a0f;
}

#header {
    background: #0d0d14;
    color: #4dabf7;
    text-style: bold;
}

.title {
    text-align: center;
    padding: 1 2;
    color: #4dabf7;
    text-style: bold;
}

.subtitle {
    text-align: center;
    color: #868e96;
    margin-bottom: 1;
}

.nav-button {
    width: 100%;
    margin: 0 0 1 0;
    background: #1a1a2e;
    border: none;
    color: #adb5bd;
    text-align: left;
    padding: 1 2;
}

.nav-button:hover {
    background: #2a2a3e;
    color: #4dabf7;
}

.nav-button.active {
    background: #1a3a5c;
    color: #4dabf7;
    border-left: thick #4dabf7;
}

.status-indicator {
    margin: 2 0;
    padding: 1;
    background: #1a1a2e;
    border-radius: 1;
}

.status-online {
    color: #51cf66;
    text-style: bold;
}

.status-offline {
    color: #ff6b6b;
    text-style: bold;
}

.status-busy {
    color: #ffd43b;
    text-style: bold;
}

.panel {
    height: 100%;
    border: tall #1a1a2e;
    background: #0d0d14;
    margin: 0 1;
}

.panel-title {
    dock: top;
    padding: 1 2;
    background: #1a1a2e;
    color: #4dabf7;
    text-style: bold;
    height: 3;
}

.log-panel {
    height: 100%;
    overflow-y: auto;
    padding: 1;
}

.device-list {
    height: 100%;
    overflow-y: auto;
}

.device-item {
    padding: 1 2;
    border-bottom: tall #1a1a2e;
}

.device-item:hover {
    background: #1a1a2e;
}

.device-name {
    color: #e9ecef;
    text-style: bold;
}

.device-status {
    color: #868e96;
}

.device-ip {
    color: #4dabf7;
}

.input-area {
    dock: bottom;
    height: auto;
    padding: 1;
    background: #0d0d14;
    border-top: tall #1a1a2e;
}

.command-input {
    width: 100%;
    margin: 0;
    background: #1a1a2e;
    border: tall #2a2a3e;
    color: #e9ecef;
}

.command-input:focus {
    border: tall #4dabf7;
}

.send-button {
    margin: 0 0 0 1;
    background: #1a3a5c;
    color: #4dabf7;
    min-width: 10;
}

.stats-bar {
    dock: bottom;
    height: 3;
    padding: 0 2;
    background: #0d0d14;
    border-top: tall #1a1a2e;
    color: #868e96;
}

.help-text {
    color: #868e96;
    padding: 1;
}

.keybinding {
    color: #4dabf7;
    text-style: bold;
}

#output-log {
    height: 100%;
    overflow-y: auto;
    background: #0a0a0f;
    padding: 1;
}

.welcome {
    text-align: center;
    padding: 4;
    color: #4dabf7;
    text-style: bold;
}

.version {
    color: #868e96;
}

.config-item {
    padding: 1 2;
    margin: 0 0 1 0;
    background: #1a1a2e;
    border-radius: 1;
}

.config-label {
    color: #868e96;
}

.config-value {
    color: #4dabf7;
    text-style: bold;
}

.success {
    color: #51cf66;
}

.error {
    color: #ff6b6b;
}

.warning {
    color: #ffd43b;
}

.info {
    color: #4dabf7;
}
"""


# ============================================================================
# 侧边栏导航
# ============================================================================

class Sidebar(Vertical):
    """侧边栏导航"""
    
    def compose(self) -> ComposeResult:
        yield Static("Hermes Relay", classes="title")
        yield Static("Remote Control", classes="subtitle")
        yield Rule()
        yield Button("Dashboard", id="btn-dashboard", classes="nav-button active")
        yield Button("Server", id="btn-server", classes="nav-button")
        yield Button("Agent", id="btn-agent", classes="nav-button")
        yield Button("Devices", id="btn-devices", classes="nav-button")
        yield Button("Logs", id="btn-logs", classes="nav-button")
        yield Button("Settings", id="btn-settings", classes="nav-button")
        yield Rule()
        yield Static("● Ready", id="status-indicator", classes="status-indicator status-online")


# ============================================================================
# Dashboard 页面
# ============================================================================

class DashboardPane(Vertical):
    """Dashboard 页面"""
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("Dashboard", classes="panel-title")
            with Horizontal():
                with Vertical(classes="panel"):
                    yield Static("Server", classes="panel-title")
                    yield Static("● Stopped", id="server-status", classes="status-offline")
                    yield Static("WebSocket: Not running", id="server-info")
                with Vertical(classes="panel"):
                    yield Static("Agent", classes="panel-title")
                    yield Static("● Disconnected", id="agent-status", classes="status-offline")
                    yield Static("Devices: 0", id="agent-info")
                with Vertical(classes="panel"):
                    yield Static("System", classes="panel-title")
                    yield Static("CPU: --%", id="cpu-usage")
                    yield Static("Memory: --%", id="mem-usage")
                    yield Static("Disk: --%", id="disk-usage")
            yield RichLog(id="output-log", markup=True)


# ============================================================================
# Server 页面
# ============================================================================

class ServerPane(Vertical):
    """Server 页面"""
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("Server Control", classes="panel-title")
            with Horizontal():
                yield Button("Start Server", id="start-server", classes="send-button")
                yield Button("Stop Server", id="stop-server", classes="send-button")
            yield Rule()
            yield Static("Configuration", classes="panel-title")
            with Container(classes="config-item"):
                yield Static("Listen Host:", classes="config-label")
                yield Input("0.0.0.0", id="server-host", classes="command-input")
            with Container(classes="config-item"):
                yield Static("Listen Port:", classes="config-label")
                yield Input("8765", id="server-port", classes="command-input")
            yield Rule()
            yield Static("Server Log", classes="panel-title")
            yield RichLog(id="server-log", markup=True)


# ============================================================================
# Agent 页面
# ============================================================================

class AgentPane(Vertical):
    """Agent 页面"""
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("Agent Control", classes="panel-title")
            with Horizontal():
                yield Button("Start Agent", id="start-agent", classes="send-button")
                yield Button("Stop Agent", id="stop-agent", classes="send-button")
            yield Rule()
            yield Static("Configuration", classes="panel-title")
            with Container(classes="config-item"):
                yield Static("Relay Server:", classes="config-label")
                yield Input("ws://localhost:8765", id="agent-server", classes="command-input")
            with Container(classes="config-item"):
                yield Static("Device Name:", classes="config-label")
                yield Input("", id="agent-name", classes="command-input")
            with Container(classes="config-item"):
                yield Static("Device Group:", classes="config-label")
                yield Input("default", id="agent-group", classes="command-input")
            yield Rule()
            yield Static("Agent Log", classes="panel-title")
            yield RichLog(id="agent-log", markup=True)


# ============================================================================
# Devices 页面
# ============================================================================

class DevicesPane(Vertical):
    """Devices 页面"""
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("Connected Devices", classes="panel-title")
            yield Button("Refresh", id="refresh-devices", classes="send-button")
            yield DataTable(id="device-table")


# ============================================================================
# Logs 页面
# ============================================================================

class LogsPane(Vertical):
    """Logs 页面"""
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("System Logs", classes="panel-title")
            with Horizontal():
                yield Button("Clear", id="clear-logs", classes="send-button")
                yield Button("Export", id="export-logs", classes="send-button")
            yield RichLog(id="system-log", markup=True, highlight=True)


# ============================================================================
# Settings 页面
# ============================================================================

class SettingsPane(Vertical):
    """Settings 页面"""
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("Settings", classes="panel-title")
            yield Rule()
            yield Static("Feishu Configuration", classes="panel-title")
            with Container(classes="config-item"):
                yield Static("App ID:", classes="config-label")
                yield Input("", id="feishu-app-id", classes="command-input")
            with Container(classes="config-item"):
                yield Static("App Secret:", classes="config-label")
                yield Input("", id="feishu-app-secret", classes="command-input", password=True)
            with Container(classes="config-item"):
                yield Static("Domain:", classes="config-label")
                yield Select([("feishu", "feishu"), ("lark", "lark")], id="feishu-domain")
            yield Rule()
            with Horizontal():
                yield Button("Save Settings", id="save-settings", classes="send-button")
                yield Button("扫码创建机器人", id="qr-register", classes="send-button")
            yield Rule()
            yield Static("Keybindings", classes="panel-title")
            yield Static("  [bold cyan]Ctrl+Q[/] - Quit", classes="help-text")
            yield Static("  [bold cyan]Ctrl+L[/] - Clear logs", classes="help-text")
            yield Static("  [bold cyan]Ctrl+S[/] - Start server", classes="help-text")
            yield Static("  [bold cyan]Ctrl+A[/] - Start agent", classes="help-text")
            yield Static("  [bold cyan]Tab[/] - Switch panels", classes="help-text")


# ============================================================================
# 主应用
# ============================================================================

class HermesRelayTUI(App):
    """Hermes Relay TUI 主应用"""
    
    TITLE = "Hermes Relay"
    CSS = CSS
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "clear_logs", "Clear Logs"),
        Binding("ctrl+s", "start_server", "Start Server"),
        Binding("ctrl+a", "start_agent", "Start Agent"),
        Binding("f1", "show_dashboard", "Dashboard"),
        Binding("f2", "show_server", "Server"),
        Binding("f3", "show_agent", "Agent"),
        Binding("f4", "show_devices", "Devices"),
        Binding("f5", "show_logs", "Logs"),
        Binding("f6", "show_settings", "Settings"),
    ]
    
    # 状态
    server_running = reactive(False)
    agent_running = reactive(False)
    current_page = reactive("dashboard")
    
    def compose(self) -> ComposeResult:
        yield Header(id="header")
        with Horizontal():
            yield Sidebar(id="sidebar")
            with Vertical(id="main"):
                yield TabbedContent(
                    TabPane("Dashboard", DashboardPane(), id="tab-dashboard"),
                    TabPane("Server", ServerPane(), id="tab-server"),
                    TabPane("Agent", AgentPane(), id="tab-agent"),
                    TabPane("Devices", DevicesPane(), id="tab-devices"),
                    TabPane("Logs", LogsPane(), id="tab-logs"),
                    TabPane("Settings", SettingsPane(), id="tab-settings"),
                    id="tabs"
                )
        with Container(classes="input-area"):
            with Horizontal():
                yield Input(
                    placeholder="Enter command or natural language...",
                    id="command-input",
                    classes="command-input"
                )
                yield Button("Send", id="send-command", classes="send-button")
        yield Footer()
    
    def on_mount(self) -> None:
        """应用启动"""
        self._log("[bold green]Hermes Relay TUI started[/]")
        self._log("[dim]Type 'help' for available commands[/]")
        self._log("")
        
        # 初始化设备表格
        try:
            table = self.query_one("#device-table", DataTable)
            table.add_columns("Name", "Status", "IP", "Group", "CPU", "Memory")
        except NoMatches:
            pass
        
        # 加载设置
        self._load_settings()
    
    def _log(self, message: str, panel: str = "output-log") -> None:
        """写入日志"""
        try:
            log = self.query_one(f"#{panel}", RichLog)
            timestamp = datetime.now().strftime("%H:%M:%S")
            log.write(f"[dim]{timestamp}[/] {message}")
        except NoMatches:
            pass
    
    def _load_settings(self) -> None:
        """加载设置"""
        try:
            import yaml
            config_path = Path("config/relay_config.yaml")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                
                feishu = config.get("feishu", {})
                self._set_input_value("#feishu-app-id", feishu.get("app_id", ""))
                self._set_input_value("#feishu-app-secret", feishu.get("app_secret", ""))
        except Exception:
            pass
    
    def _set_input_value(self, selector: str, value: str) -> None:
        """设置输入框值"""
        try:
            input_widget = self.query_one(selector, Input)
            input_widget.value = value
        except NoMatches:
            pass
    
    def action_quit(self) -> None:
        """退出"""
        self.exit()
    
    def action_clear_logs(self) -> None:
        """清除日志"""
        try:
            log = self.query_one("#output-log", RichLog)
            log.clear()
            self._log("[dim]Logs cleared[/]")
        except NoMatches:
            pass
    
    def action_start_server(self) -> None:
        """启动服务端"""
        self._start_server()
    
    def action_start_agent(self) -> None:
        """启动 Agent"""
        self._start_agent()
    
    def action_show_dashboard(self) -> None:
        """显示 Dashboard"""
        self._switch_tab("dashboard")
    
    def action_show_server(self) -> None:
        """显示 Server"""
        self._switch_tab("server")
    
    def action_show_agent(self) -> None:
        """显示 Agent"""
        self._switch_tab("agent")
    
    def action_show_devices(self) -> None:
        """显示 Devices"""
        self._switch_tab("devices")
    
    def action_show_logs(self) -> None:
        """显示 Logs"""
        self._switch_tab("logs")
    
    def action_show_settings(self) -> None:
        """显示 Settings"""
        self._switch_tab("settings")
    
    def _switch_tab(self, name: str) -> None:
        """切换标签页"""
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = f"tab-{name}"
            self.current_page = name
        except NoMatches:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件"""
        button_id = event.button.id
        
        if button_id == "btn-dashboard":
            self._switch_tab("dashboard")
        elif button_id == "btn-server":
            self._switch_tab("server")
        elif button_id == "btn-agent":
            self._switch_tab("agent")
        elif button_id == "btn-devices":
            self._switch_tab("devices")
        elif button_id == "btn-logs":
            self._switch_tab("logs")
        elif button_id == "btn-settings":
            self._switch_tab("settings")
        elif button_id == "start-server":
            self._start_server()
        elif button_id == "stop-server":
            self._stop_server()
        elif button_id == "start-agent":
            self._start_agent()
        elif button_id == "stop-agent":
            self._stop_agent()
        elif button_id == "send-command":
            self._send_command()
        elif button_id == "refresh-devices":
            self._refresh_devices()
        elif button_id == "clear-logs":
            self.action_clear_logs()
        elif button_id == "save-settings":
            self._save_settings()
        elif button_id == "qr-register":
            self._start_qr_register()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """输入提交事件"""
        if event.input.id == "command-input":
            self._send_command()
    
    def _start_server(self) -> None:
        """启动服务端"""
        if self.server_running:
            self._log("[yellow]Server is already running[/]")
            return
        
        self._log("[bold green]Starting server...[/]")
        self.server_running = True
        
        # 更新状态
        self._update_server_status(True)
        
        # TODO: 实际启动服务端
        import threading
        def run_server():
            try:
                import subprocess
                self.process = subprocess.Popen(
                    [sys.executable, "hermes_relay.py", "server"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in self.process.stdout:
                    self._log(f"[dim]{line.strip()}[/]", "server-log")
            except Exception as e:
                self._log(f"[red]Server error: {e}[/]")
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
    
    def _stop_server(self) -> None:
        """停止服务端"""
        if not self.server_running:
            self._log("[yellow]Server is not running[/]")
            return
        
        self._log("[bold red]Stopping server...[/]")
        self.server_running = False
        self._update_server_status(False)
        
        if hasattr(self, 'process'):
            self.process.terminate()
    
    def _start_agent(self) -> None:
        """启动 Agent"""
        if self.agent_running:
            self._log("[yellow]Agent is already running[/]")
            return
        
        self._log("[bold green]Starting agent...[/]")
        self.agent_running = True
        self._update_agent_status(True)
        
        # TODO: 实际启动 Agent
        import threading
        def run_agent():
            try:
                import subprocess
                self.agent_process = subprocess.Popen(
                    [sys.executable, "hermes_relay.py", "agent"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in self.agent_process.stdout:
                    self._log(f"[dim]{line.strip()}[/]", "agent-log")
            except Exception as e:
                self._log(f"[red]Agent error: {e}[/]")
        
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()
    
    def _stop_agent(self) -> None:
        """停止 Agent"""
        if not self.agent_running:
            self._log("[yellow]Agent is not running[/]")
            return
        
        self._log("[bold red]Stopping agent...[/]")
        self.agent_running = False
        self._update_agent_status(False)
        
        if hasattr(self, 'agent_process'):
            self.agent_process.terminate()
    
    def _send_command(self) -> None:
        """发送命令"""
        try:
            input_widget = self.query_one("#command-input", Input)
            command = input_widget.value.strip()
            
            if not command:
                return
            
            self._log(f"[bold]> {command}[/]")
            input_widget.value = ""
            
            # 处理命令
            self._process_command(command)
        except NoMatches:
            pass
    
    def _process_command(self, command: str) -> None:
        """处理命令"""
        cmd_lower = command.lower()
        
        if cmd_lower in ("help", "帮助", "?"):
            self._show_help()
        elif cmd_lower in ("status", "状态"):
            self._show_status()
        elif cmd_lower in ("clear", "cls", "清屏"):
            self.action_clear_logs()
        elif cmd_lower in ("quit", "exit", "退出"):
            self.action_quit()
        elif cmd_lower in ("server", "服务端"):
            self._switch_tab("server")
        elif cmd_lower in ("agent", "被控端"):
            self._switch_tab("agent")
        elif cmd_lower in ("devices", "设备"):
            self._switch_tab("devices")
        elif cmd_lower in ("settings", "设置"):
            self._switch_tab("settings")
        elif cmd_lower in ("qr", "scan", "扫码", "注册"):
            self._start_qr_register()
        elif cmd_lower.startswith("start server"):
            self._start_server()
        elif cmd_lower.startswith("start agent"):
            self._start_agent()
        elif cmd_lower.startswith("stop server"):
            self._stop_server()
        elif cmd_lower.startswith("stop agent"):
            self._stop_agent()
        else:
            # 尝试 NLP 解析
            self._nlp_execute(command)
    
    def _show_help(self) -> None:
        """显示帮助"""
        help_text = """
[bold cyan]Available Commands:[/]

  [bold]help[/]          - Show this help
  [bold]status[/]        - Show system status
  [bold]clear[/]         - Clear logs
  [bold]quit[/]          - Exit application

  [bold]server[/]        - Switch to Server tab
  [bold]agent[/]         - Switch to Agent tab
  [bold]devices[/]       - Switch to Devices tab
  [bold]settings[/]      - Switch to Settings tab

  [bold]start server[/]  - Start relay server
  [bold]stop server[/]   - Stop relay server
  [bold]start agent[/]   - Start agent
  [bold]stop agent[/]    - Stop agent

  [bold]qr[/] / [bold]scan[/] - 扫码创建飞书机器人

[bold cyan]Natural Language:[/]

  [bold]截图[/]          - Take screenshot
  [bold]点击 100，200[/]  - Click at coordinates
  [bold]查看IP[/]        - Show IP configuration
  [bold]查看进程[/]      - List processes
  [bold]设备列表[/]      - List devices

[bold cyan]Keyboard Shortcuts:[/]

  [bold]Ctrl+Q[/]        - Quit
  [bold]Ctrl+L[/]        - Clear logs
  [bold]Ctrl+S[/]        - Start server
  [bold]Ctrl+A[/]        - Start agent
  [bold]F1-F6[/]         - Switch tabs
"""
        self._log(help_text)
    
    def _show_status(self) -> None:
        """显示状态"""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            status = f"""
[bold cyan]System Status:[/]

  CPU:    [{'green' if cpu < 80 else 'red'}]{cpu}%[/]
  Memory: [{'green' if mem < 80 else 'red'}]{mem}%[/]
  Disk:   [{'green' if disk < 80 else 'red'}]{disk}%[/]

  Server: [{'green' if self.server_running else 'red'}]{'Running' if self.server_running else 'Stopped'}[/]
  Agent:  [{'green' if self.agent_running else 'red'}]{'Connected' if self.agent_running else 'Disconnected'}[/]
"""
            self._log(status)
        except Exception as e:
            self._log(f"[red]Error: {e}[/]")
    
    def _nlp_execute(self, command: str) -> None:
        """NLP 命令执行"""
        try:
            from relay_server.nlp.parser import NLPParser
            parser = NLPParser()
            result = parser.parse(command)
            
            if result and result[0]:
                cmd, metadata = result
                self._log(f"[dim]Executing: {cmd}[/]")
                
                special_action = metadata.get("special_action")
                
                if special_action == "screenshot":
                    self._take_screenshot()
                elif special_action == "device_list":
                    self._refresh_devices()
                elif special_action == "help":
                    self._show_help()
                elif special_action.startswith("mouse_"):
                    self._execute_mouse_action(special_action, cmd)
                else:
                    self._execute_command(cmd)
            else:
                self._log(f"[yellow]Unknown command: {command}[/]")
        except Exception as e:
            self._log(f"[red]NLP error: {e}[/]")
    
    def _execute_command(self, command: str) -> None:
        """执行系统命令"""
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.stdout:
                self._log(f"[dim]{result.stdout.strip()}[/]")
            if result.stderr:
                self._log(f"[red]{result.stderr.strip()}[/]")
            if result.returncode != 0:
                self._log(f"[red]Exit code: {result.returncode}[/]")
        except subprocess.TimeoutExpired:
            self._log("[red]Command timed out[/]")
        except Exception as e:
            self._log(f"[red]Error: {e}[/]")
    
    def _take_screenshot(self) -> None:
        """截图"""
        try:
            from agent_client.executor.windows_control import get_controller
            controller = get_controller()
            path, b64 = controller.screenshot()
            self._log(f"[green]Screenshot saved: {path}[/]")
        except Exception as e:
            self._log(f"[red]Screenshot error: {e}[/]")
    
    def _execute_mouse_action(self, action: str, command: str) -> None:
        """执行鼠标操作"""
        try:
            parts = command.split()
            if len(parts) >= 3:
                x, y = int(parts[1]), int(parts[2])
                
                from agent_client.executor.windows_control import get_controller
                controller = get_controller()
                
                if action == "mouse_click":
                    controller.mouse_click(x, y)
                    self._log(f"[green]Clicked ({x}, {y})[/]")
                elif action == "mouse_move":
                    controller.mouse_move(x, y)
                    self._log(f"[green]Moved to ({x}, {y})[/]")
                elif action == "mouse_double_click":
                    controller.mouse_double_click(x, y)
                    self._log(f"[green]Double-clicked ({x}, {y})[/]")
                elif action == "mouse_right_click":
                    controller.mouse_right_click(x, y)
                    self._log(f"[green]Right-clicked ({x}, {y})[/]")
        except Exception as e:
            self._log(f"[red]Mouse error: {e}[/]")
    
    def _refresh_devices(self) -> None:
        """刷新设备列表"""
        self._log("[dim]Refreshing devices...[/]")
        # TODO: 从服务端获取设备列表
    
    def _save_settings(self) -> None:
        """保存设置"""
        try:
            import yaml
            
            app_id = self.query_one("#feishu-app-id", Input).value
            app_secret = self.query_one("#feishu-app-secret", Input).value
            
            config = {
                "feishu": {
                    "app_id": app_id,
                    "app_secret": app_secret,
                    "domain": "feishu",
                }
            }
            
            Path("config").mkdir(exist_ok=True)
            with open("config/relay_config.yaml", "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            self._log("[green]Settings saved![/]")
        except Exception as e:
            self._log(f"[red]Save error: {e}[/]")
    
    def _start_qr_register(self) -> None:
        """开始扫码注册"""
        import threading
        
        self._log("[bold cyan]开始扫码注册飞书机器人...[/]")
        self._log("[dim]请用飞书手机端扫描下方二维码[/]")
        self._log("")
        
        def run_register():
            try:
                from relay_server.feishu.onboard import qr_register, print_setup_result
                import yaml
                
                def callback(event, data):
                    if event == "qr_url":
                        self._log(f"[bold cyan]二维码链接:[/]")
                        self._log(f"[link={data}]{data}[/link]")
                        self._log("")
                        self._log("[dim]请在飞书/Lark 手机端打开上方链接扫描二维码[/]")
                    elif event == "polling":
                        if data % 6 == 1:
                            self._log("[dim]等待扫码中...[/]", "server-log")
                    elif event == "success":
                        self._log("[green]扫码成功![/]", "server-log")
                    elif event == "denied":
                        self._log("[red]扫码被拒绝[/]")
                    elif event == "timeout":
                        self._log("[red]扫码超时[/]")
                    elif event == "probing":
                        self._log("[dim]验证机器人信息...[/]")
                    elif event == "complete":
                        if data:
                            # 保存配置
                            config = {
                                "feishu": {
                                    "app_id": data["app_id"],
                                    "app_secret": data["app_secret"],
                                    "domain": data["domain"],
                                    "encrypt_key": "",
                                    "verification_token": "",
                                },
                                "ws_host": "0.0.0.0",
                                "ws_port": 8765,
                                "heartbeat_timeout": 60,
                                "approval_timeout": 300,
                                "log_level": "INFO",
                            }
                            
                            Path("config").mkdir(exist_ok=True)
                            with open("config/relay_config.yaml", "w", encoding="utf-8") as f:
                                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                            
                            # 更新 UI
                            self._set_input_value("#feishu-app-id", data["app_id"])
                            self._set_input_value("#feishu-app-secret", data["app_secret"])
                            
                            self._log("")
                            self._log("[bold green]✅ 飞书机器人创建成功![/]")
                            self._log(f"  App ID:     {data['app_id']}")
                            self._log(f"  App Secret: {data['app_secret'][:8]}...")
                            if data.get("bot_name"):
                                self._log(f"  Bot 名称:   {data['bot_name']}")
                            self._log("")
                            self._log("[green]配置已保存，可以启动服务端了。[/]")
                    elif event == "error":
                        self._log(f"[red]注册失败: {data}[/]")
                
                result = qr_register(
                    initial_domain="feishu",
                    timeout_seconds=600,
                    callback=callback,
                )
                
            except Exception as e:
                self._log(f"[red]注册错误: {e}[/]")
        
        thread = threading.Thread(target=run_register, daemon=True)
        thread.start()
    
    def _update_server_status(self, running: bool) -> None:
        """更新服务端状态"""
        try:
            status = self.query_one("#server-status")
            if running:
                status.update("● Running")
                status.remove_class("status-offline")
                status.add_class("status-online")
            else:
                status.update("● Stopped")
                status.remove_class("status-online")
                status.add_class("status-offline")
        except NoMatches:
            pass
    
    def _update_agent_status(self, running: bool) -> None:
        """更新 Agent 状态"""
        try:
            status = self.query_one("#agent-status")
            if running:
                status.update("● Connected")
                status.remove_class("status-offline")
                status.add_class("status-online")
            else:
                status.update("● Disconnected")
                status.remove_class("status-online")
                status.add_class("status-offline")
        except NoMatches:
            pass


def main():
    """启动 TUI"""
    app = HermesRelayTUI()
    app.run()


if __name__ == "__main__":
    main()
