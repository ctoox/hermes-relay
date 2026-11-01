"""
Hermes Relay - 桌面端主程序
基于 PySide6 的现代化远程控制界面
"""

import sys
import os
import json
import asyncio
import threading
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import (
    Qt, QPoint, QThread, Signal, QTimer, QSize,
    QPropertyAnimation, QEasingCurve, QRect
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox,
    QSystemTrayIcon, QMenu, QMessageBox, QDialog, QTabWidget,
    QGroupBox, QFormLayout, QCheckBox, QSpinBox, QScrollArea,
    QFrame, QSplitter, QListWidget, QListWidgetItem, QStatusBar
)
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QFont, QCursor,
    QLinearGradient, QBrush, QPen, QAction, QIcon, QPixmap
)


# ============================================================================
# 样式定义
# ============================================================================

DARK_STYLE = """
QMainWindow {
    background: #0a0a0f;
}

QWidget {
    color: #e0e4f0;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QWidget#sidebar {
    background: #0d0d14;
    border-right: 1px solid rgba(70, 140, 255, 15);
}

QWidget#content {
    background: #0a0a0f;
}

QLabel#title {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
}

QLabel#subtitle {
    color: rgba(160, 165, 185, 200);
    font-size: 12px;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(70, 130, 255, 200),
        stop:1 rgba(100, 160, 255, 200));
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: bold;
    min-height: 20px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(80, 140, 255, 220),
        stop:1 rgba(110, 170, 255, 220));
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(60, 120, 245, 200),
        stop:1 rgba(90, 150, 245, 200));
}

QPushButton#danger {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255, 80, 80, 200),
        stop:1 rgba(255, 120, 100, 200));
}

QPushButton#secondary {
    background: rgba(40, 42, 55, 200);
    border: 1px solid rgba(70, 140, 255, 30);
}

QTextEdit {
    background: rgba(8, 8, 14, 220);
    color: #e0e4f0;
    border: 1px solid rgba(70, 140, 255, 20);
    border-radius: 10px;
    padding: 12px;
    font-family: "Consolas", "Cascadia Code", monospace;
    font-size: 12px;
    selection-background-color: rgba(70, 140, 255, 80);
}

QLineEdit {
    background: rgba(20, 22, 35, 200);
    color: #e0e4f0;
    border: 1px solid rgba(70, 140, 255, 25);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid rgba(70, 140, 255, 60);
}

QComboBox {
    background: rgba(20, 22, 35, 200);
    color: #e0e4f0;
    border: 1px solid rgba(70, 140, 255, 25);
    border-radius: 8px;
    padding: 8px 12px;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox QAbstractItemView {
    background: rgba(20, 22, 35, 240);
    border: 1px solid rgba(70, 140, 255, 30);
    selection-background-color: rgba(70, 140, 255, 60);
}

QGroupBox {
    background: rgba(15, 15, 22, 180);
    border: 1px solid rgba(70, 140, 255, 20);
    border-radius: 12px;
    margin-top: 10px;
    padding-top: 20px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px;
    color: rgba(130, 210, 255, 230);
}

QListWidget {
    background: rgba(8, 8, 14, 200);
    border: 1px solid rgba(70, 140, 255, 20);
    border-radius: 10px;
    padding: 5px;
}

QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin: 2px;
}

QListWidget::item:selected {
    background: rgba(70, 140, 255, 40);
}

QListWidget::item:hover {
    background: rgba(70, 140, 255, 20);
}

QTabWidget::pane {
    border: 1px solid rgba(70, 140, 255, 20);
    border-radius: 10px;
    background: rgba(10, 10, 15, 200);
}

QTabBar::tab {
    background: rgba(20, 22, 35, 180);
    color: rgba(160, 165, 185, 200);
    border: none;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

QTabBar::tab:selected {
    background: rgba(70, 140, 255, 30);
    color: #ffffff;
}

QStatusBar {
    background: rgba(8, 8, 14, 200);
    color: rgba(160, 165, 185, 200);
    border-top: 1px solid rgba(70, 140, 255, 15);
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(70, 140, 255, 40);
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(70, 140, 255, 60);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid rgba(70, 140, 255, 40);
    background: rgba(20, 22, 35, 200);
}

QCheckBox::indicator:checked {
    background: rgba(70, 140, 255, 200);
    border: 1px solid rgba(70, 140, 255, 80);
}

QSpinBox {
    background: rgba(20, 22, 35, 200);
    color: #e0e4f0;
    border: 1px solid rgba(70, 140, 255, 25);
    border-radius: 8px;
    padding: 8px;
}
"""


# ============================================================================
# 工作线程
# ============================================================================

class ServerThread(QThread):
    """服务端线程"""
    log_signal = Signal(str)
    status_signal = Signal(str)
    
    def __init__(self, config_path):
        super().__init__()
        self.config_path = config_path
        self.running = False
    
    def run(self):
        self.running = True
        self.status_signal.emit("starting")
        self.log_signal.emit("[Server] Starting...")
        
        try:
            # 这里启动服务端
            import subprocess
            self.process = subprocess.Popen(
                [sys.executable, "hermes_relay.py", "server", "--config", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.status_signal.emit("running")
            self.log_signal.emit("[Server] Started successfully")
            
            for line in self.process.stdout:
                if not self.running:
                    break
                self.log_signal.emit(line.strip())
            
        except Exception as e:
            self.log_signal.emit(f"[Server] Error: {e}")
            self.status_signal.emit("error")
    
    def stop(self):
        self.running = False
        if hasattr(self, 'process'):
            self.process.terminate()
        self.status_signal.emit("stopped")


class AgentThread(QThread):
    """Agent 线程"""
    log_signal = Signal(str)
    status_signal = Signal(str)
    
    def __init__(self, config_path):
        super().__init__()
        self.config_path = config_path
        self.running = False
    
    def run(self):
        self.running = True
        self.status_signal.emit("starting")
        self.log_signal.emit("[Agent] Starting...")
        
        try:
            import subprocess
            self.process = subprocess.Popen(
                [sys.executable, "hermes_relay.py", "agent", "--config", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.status_signal.emit("running")
            self.log_signal.emit("[Agent] Connected to relay server")
            
            for line in self.process.stdout:
                if not self.running:
                    break
                self.log_signal.emit(line.strip())
            
        except Exception as e:
            self.log_signal.emit(f"[Agent] Error: {e}")
            self.status_signal.emit("error")
    
    def stop(self):
        self.running = False
        if hasattr(self, 'process'):
            self.process.terminate()
        self.status_signal.emit("stopped")


# ============================================================================
# 主窗口
# ============================================================================

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hermes Relay - Remote Control")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # 设置图标
        if Path("app.ico").exists():
            self.setWindowIcon(QIcon("app.ico"))
        
        # 初始化 UI
        self._init_ui()
        self._init_tray()
        
        # 线程
        self.server_thread = None
        self.agent_thread = None
    
    def _init_ui(self):
        """初始化界面"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)
        sidebar_layout.setSpacing(5)
        
        # Logo
        logo_label = QLabel("Hermes Relay")
        logo_label.setObjectName("title")
        sidebar_layout.addWidget(logo_label)
        
        subtitle = QLabel("Remote Control")
        subtitle.setObjectName("subtitle")
        sidebar_layout.addWidget(subtitle)
        
        sidebar_layout.addSpacing(20)
        
        # 导航按钮
        self.nav_buttons = []
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Server", "server"),
            ("Agent", "agent"),
            ("Devices", "devices"),
            ("Settings", "settings"),
        ]
        
        for text, name in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("secondary")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda checked, n=name: self._switch_page(n))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append((btn, name))
        
        sidebar_layout.addStretch()
        
        # 状态指示
        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet("color: rgba(100, 255, 150, 200); font-size: 12px;")
        sidebar_layout.addWidget(self.status_label)
        
        main_layout.addWidget(sidebar)
        
        # 内容区域
        content = QWidget()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # 堆叠页面
        from PySide6.QtWidgets import QStackedWidget
        self.stack = QStackedWidget()
        
        # 添加页面
        self.stack.addWidget(self._create_dashboard_page())
        self.stack.addWidget(self._create_server_page())
        self.stack.addWidget(self._create_agent_page())
        self.stack.addWidget(self._create_devices_page())
        self.stack.addWidget(self._create_settings_page())
        
        content_layout.addWidget(self.stack)
        main_layout.addWidget(content)
        
        # 状态栏
        self.statusBar().showMessage("Ready")
    
    def _create_dashboard_page(self):
        """创建 Dashboard 页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("Dashboard")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 状态卡片
        cards_layout = QHBoxLayout()
        
        # 服务端状态卡片
        server_card = QGroupBox("Server Status")
        server_layout = QVBoxLayout(server_card)
        self.server_status_label = QLabel("Stopped")
        self.server_status_label.setStyleSheet("color: #ff6b6b; font-size: 24px; font-weight: bold;")
        server_layout.addWidget(self.server_status_label)
        server_layout.addWidget(QLabel("WebSocket: Not running"))
        cards_layout.addWidget(server_card)
        
        # Agent 状态卡片
        agent_card = QGroupBox("Agent Status")
        agent_layout = QVBoxLayout(agent_card)
        self.agent_status_label = QLabel("Disconnected")
        self.agent_status_label.setStyleSheet("color: #ff6b6b; font-size: 24px; font-weight: bold;")
        agent_layout.addWidget(self.agent_status_label)
        agent_layout.addWidget(QLabel("Devices: 0"))
        cards_layout.addWidget(agent_card)
        
        # 设备统计卡片
        devices_card = QGroupBox("Devices")
        devices_layout = QVBoxLayout(devices_card)
        self.devices_count_label = QLabel("0")
        self.devices_count_label.setStyleSheet("color: #4dabf7; font-size: 24px; font-weight: bold;")
        devices_layout.addWidget(self.devices_count_label)
        devices_layout.addWidget(QLabel("Online devices"))
        cards_layout.addWidget(devices_card)
        
        layout.addLayout(cards_layout)
        
        # 日志区域
        log_group = QGroupBox("System Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        return page
    
    def _create_server_page(self):
        """创建服务端页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        title = QLabel("Server Control")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 配置区域
        config_group = QGroupBox("Configuration")
        config_layout = QFormLayout(config_group)
        
        self.server_host_input = QLineEdit("0.0.0.0")
        config_layout.addRow("Listen Host:", self.server_host_input)
        
        self.server_port_input = QSpinBox()
        self.server_port_input.setRange(1, 65535)
        self.server_port_input.setValue(8765)
        config_layout.addRow("Listen Port:", self.server_port_input)
        
        layout.addWidget(config_group)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_server_btn = QPushButton("Start Server")
        self.start_server_btn.clicked.connect(self._start_server)
        btn_layout.addWidget(self.start_server_btn)
        
        self.stop_server_btn = QPushButton("Stop Server")
        self.stop_server_btn.setObjectName("danger")
        self.stop_server_btn.clicked.connect(self._stop_server)
        self.stop_server_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_server_btn)
        
        layout.addLayout(btn_layout)
        
        # 服务端日志
        log_group = QGroupBox("Server Log")
        log_layout = QVBoxLayout(log_group)
        self.server_log = QTextEdit()
        self.server_log.setReadOnly(True)
        log_layout.addWidget(self.server_log)
        layout.addWidget(log_group)
        
        return page
    
    def _create_agent_page(self):
        """创建 Agent 页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        title = QLabel("Agent Control")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 配置区域
        config_group = QGroupBox("Configuration")
        config_layout = QFormLayout(config_group)
        
        self.agent_server_input = QLineEdit("ws://localhost:8765")
        config_layout.addRow("Relay Server:", self.agent_server_input)
        
        self.agent_name_input = QLineEdit()
        config_layout.addRow("Device Name:", self.agent_name_input)
        
        self.agent_group_input = QLineEdit("default")
        config_layout.addRow("Device Group:", self.agent_group_input)
        
        layout.addWidget(config_group)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_agent_btn = QPushButton("Start Agent")
        self.start_agent_btn.clicked.connect(self._start_agent)
        btn_layout.addWidget(self.start_agent_btn)
        
        self.stop_agent_btn = QPushButton("Stop Agent")
        self.stop_agent_btn.setObjectName("danger")
        self.stop_agent_btn.clicked.connect(self._stop_agent)
        self.stop_agent_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_agent_btn)
        
        layout.addLayout(btn_layout)
        
        # Agent 日志
        log_group = QGroupBox("Agent Log")
        log_layout = QVBoxLayout(log_group)
        self.agent_log = QTextEdit()
        self.agent_log.setReadOnly(True)
        log_layout.addWidget(self.agent_log)
        layout.addWidget(log_group)
        
        return page
    
    def _create_devices_page(self):
        """创建设备页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        title = QLabel("Connected Devices")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 设备列表
        self.devices_list = QListWidget()
        self.devices_list.setMinimumHeight(400)
        layout.addWidget(self.devices_list)
        
        # 刷新按钮
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_devices)
        layout.addWidget(refresh_btn)
        
        return page
    
    def _create_settings_page(self):
        """创建设置页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        title = QLabel("Settings")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 飞书配置
        feishu_group = QGroupBox("Feishu Configuration")
        feishu_layout = QFormLayout(feishu_group)
        
        self.feishu_app_id = QLineEdit()
        feishu_layout.addRow("App ID:", self.feishu_app_id)
        
        self.feishu_app_secret = QLineEdit()
        self.feishu_app_secret.setEchoMode(QLineEdit.Password)
        feishu_layout.addRow("App Secret:", self.feishu_app_secret)
        
        self.feishu_domain = QComboBox()
        self.feishu_domain.addItems(["feishu", "lark"])
        feishu_layout.addRow("Domain:", self.feishu_domain)
        
        layout.addWidget(feishu_group)
        
        # 保存按钮
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        return page
    
    def _init_tray(self):
        """初始化系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        if Path("app.ico").exists():
            self.tray_icon.setIcon(QIcon("app.ico"))
        
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()
    
    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
    
    def _switch_page(self, name):
        """切换页面"""
        pages = {
            "dashboard": 0,
            "server": 1,
            "agent": 2,
            "devices": 3,
            "settings": 4,
        }
        if name in pages:
            self.stack.setCurrentIndex(pages[name])
    
    def _start_server(self):
        """启动服务端"""
        config_path = "config/relay_config.yaml"
        self.server_thread = ServerThread(config_path)
        self.server_thread.log_signal.connect(self._log_server)
        self.server_thread.status_signal.connect(self._update_server_status)
        self.server_thread.start()
        
        self.start_server_btn.setEnabled(False)
        self.stop_server_btn.setEnabled(True)
    
    def _stop_server(self):
        """停止服务端"""
        if self.server_thread:
            self.server_thread.stop()
        self.start_server_btn.setEnabled(True)
        self.stop_server_btn.setEnabled(False)
    
    def _start_agent(self):
        """启动 Agent"""
        config_path = "config/agent_config.yaml"
        self.agent_thread = AgentThread(config_path)
        self.agent_thread.log_signal.connect(self._log_agent)
        self.agent_thread.status_signal.connect(self._update_agent_status)
        self.agent_thread.start()
        
        self.start_agent_btn.setEnabled(False)
        self.stop_agent_btn.setEnabled(True)
    
    def _stop_agent(self):
        """停止 Agent"""
        if self.agent_thread:
            self.agent_thread.stop()
        self.start_agent_btn.setEnabled(True)
        self.stop_agent_btn.setEnabled(False)
    
    def _log_server(self, msg):
        """服务端日志"""
        self.server_log.append(msg)
        self.log_text.append(msg)
    
    def _log_agent(self, msg):
        """Agent 日志"""
        self.agent_log.append(msg)
        self.log_text.append(msg)
    
    def _update_server_status(self, status):
        """更新服务端状态"""
        if status == "running":
            self.server_status_label.setText("Running")
            self.server_status_label.setStyleSheet("color: #51cf66; font-size: 24px; font-weight: bold;")
        else:
            self.server_status_label.setText("Stopped")
            self.server_status_label.setStyleSheet("color: #ff6b6b; font-size: 24px; font-weight: bold;")
    
    def _update_agent_status(self, status):
        """更新 Agent 状态"""
        if status == "running":
            self.agent_status_label.setText("Connected")
            self.agent_status_label.setStyleSheet("color: #51cf66; font-size: 24px; font-weight: bold;")
        else:
            self.agent_status_label.setText("Disconnected")
            self.agent_status_label.setStyleSheet("color: #ff6b6b; font-size: 24px; font-weight: bold;")
    
    def _refresh_devices(self):
        """刷新设备列表"""
        self.devices_list.clear()
        # TODO: 从服务端获取设备列表
    
    def _save_settings(self):
        """保存设置"""
        import yaml
        
        config = {
            "feishu": {
                "app_id": self.feishu_app_id.text(),
                "app_secret": self.feishu_app_secret.text(),
                "domain": self.feishu_domain.currentText(),
            }
        }
        
        Path("config").mkdir(exist_ok=True)
        with open("config/relay_config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        self.statusBar().showMessage("Settings saved!", 3000)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            # 停止所有线程
            if self.server_thread:
                self.server_thread.stop()
            if self.agent_thread:
                self.agent_thread.stop()
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    
    # 设置应用图标
    if Path("app.ico").exists():
        app.setWindowIcon(QIcon("app.ico"))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
