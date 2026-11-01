"""
Hermes Relay - 初始设置向导
提供交互式配置和一键启动功能
"""

from __future__ import annotations

import json
import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SetupWizard:
    """
    初始设置向导
    
    引导用户完成:
    1. 飞书机器人配置 (扫码或手动)
    2. 中转站服务端配置
    3. 被控端 Agent 配置
    4. 一键启动
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self) -> None:
        """运行设置向导"""
        print("\n" + "=" * 60)
        print("🚀 Hermes Relay - 初始设置向导")
        print("=" * 60)
        
        print("\n请选择要配置的组件:")
        print("  1. 中转站服务端 (需要飞书机器人)")
        print("  2. 被控端 Agent (连接到中转站)")
        print("  3. 完整设置 (服务端 + 被控端)")
        print("  0. 退出")
        
        choice = input("\n请选择 [0-3]: ").strip()
        
        if choice == "1":
            self._setup_server()
        elif choice == "2":
            self._setup_agent()
        elif choice == "3":
            self._setup_full()
        elif choice == "0":
            print("退出设置")
        else:
            print("无效选择")
    
    def _setup_server(self) -> None:
        """设置中转站服务端"""
        print("\n" + "-" * 50)
        print("📡 中转站服务端设置")
        print("-" * 50)
        
        # 飞书配置
        feishu_config = self._setup_feishu()
        
        # 服务端配置
        server_config = self._get_server_config()
        
        # 保存配置
        config = {
            "ws_host": server_config["ws_host"],
            "ws_port": server_config["ws_port"],
            "feishu": feishu_config,
            "heartbeat_timeout": server_config.get("heartbeat_timeout", 60),
            "approval_timeout": server_config.get("approval_timeout", 300),
            "log_level": "INFO",
        }
        
        config_path = self.config_dir / "relay_config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"\n✅ 配置已保存到: {config_path}")
        
        # 询问是否立即启动
        if input("\n是否立即启动服务端? [Y/n]: ").strip().lower() != "n":
            self._start_server(config_path)
    
    def _setup_feishu(self) -> Dict[str, Any]:
        """设置飞书配置"""
        print("\n📌 飞书机器人配置:")
        print("  1. 扫码自动创建 (推荐)")
        print("  2. 手动输入凭据")
        
        choice = input("\n请选择 [1-2]: ").strip()
        
        if choice == "1":
            return self._setup_feishu_qr()
        else:
            return self._setup_feishu_manual()
    
    def _setup_feishu_qr(self) -> Dict[str, Any]:
        """扫码配置飞书"""
        from .feishu.onboard import qr_register, print_setup_result
        
        print("\n📱 扫码配置飞书机器人:")
        print("  请使用飞书/Lark 手机版扫描二维码")
        
        # 选择域名
        print("\n  请选择:")
        print("  1. 飞书 (中国版)")
        print("  2. Lark (国际版)")
        
        domain_choice = input("\n请选择 [1-2]: ").strip()
        domain = "lark" if domain_choice == "2" else "feishu"
        
        # 运行扫码注册
        result = qr_register(initial_domain=domain, timeout_seconds=600)
        
        if result:
            print_setup_result(result)
            return {
                "app_id": result["app_id"],
                "app_secret": result["app_secret"],
                "domain": result["domain"],
                "encrypt_key": "",
                "verification_token": "",
            }
        else:
            print("\n❌ 扫码注册失败，切换到手动配置")
            return self._setup_feishu_manual()
    
    def _setup_feishu_manual(self) -> Dict[str, Any]:
        """手动配置飞书"""
        print("\n📝 手动配置飞书机器人:")
        print("  请访问 https://open.feishu.cn 创建应用")
        
        app_id = input("\n  App ID: ").strip()
        app_secret = input("  App Secret: ").strip()
        
        print("\n  请选择域名:")
        print("  1. feishu (中国版)")
        print("  2. lark (国际版)")
        
        domain_choice = input("  请选择 [1-2]: ").strip()
        domain = "lark" if domain_choice == "2" else "feishu"
        
        encrypt_key = input("  Encrypt Key (可选，直接回车跳过): ").strip()
        verification_token = input("  Verification Token (可选，直接回车跳过): ").strip()
        
        return {
            "app_id": app_id,
            "app_secret": app_secret,
            "domain": domain,
            "encrypt_key": encrypt_key,
            "verification_token": verification_token,
        }
    
    def _get_server_config(self) -> Dict[str, Any]:
        """获取服务端配置"""
        print("\n⚙️ 服务端配置:")
        
        ws_host = input("  监听地址 [0.0.0.0]: ").strip() or "0.0.0.0"
        ws_port = input("  监听端口 [8765]: ").strip() or "8765"
        heartbeat_timeout = input("  心跳超时(秒) [60]: ").strip() or "60"
        approval_timeout = input("  审批超时(秒) [300]: ").strip() or "300"
        
        return {
            "ws_host": ws_host,
            "ws_port": int(ws_port),
            "heartbeat_timeout": int(heartbeat_timeout),
            "approval_timeout": int(approval_timeout),
        }
    
    def _setup_agent(self) -> None:
        """设置被控端 Agent"""
        print("\n" + "-" * 50)
        print("💻 被控端 Agent 设置")
        print("-" * 50)
        
        # 获取配置
        config = self._get_agent_config()
        
        # 保存配置
        config_path = self.config_dir / "agent_config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"\n✅ 配置已保存到: {config_path}")
        
        # 询问是否立即启动
        if input("\n是否立即启动 Agent? [Y/n]: ").strip().lower() != "n":
            self._start_agent(config_path)
    
    def _get_agent_config(self) -> Dict[str, Any]:
        """获取 Agent 配置"""
        print("\n⚙️ Agent 配置:")
        
        import socket
        default_name = socket.gethostname()
        
        server_url = input("  中转站地址 [ws://localhost:8765]: ").strip() or "ws://localhost:8765"
        device_name = input(f"  设备名称 [{default_name}]: ").strip() or default_name
        device_group = input("  设备组 [default]: ").strip() or "default"
        auth_token = input("  认证令牌 (可选): ").strip()
        heartbeat_interval = input("  心跳间隔(秒) [30]: ").strip() or "30"
        command_timeout = input("  命令超时(秒) [60]: ").strip() or "60"
        
        return {
            "server_url": server_url,
            "device_name": device_name,
            "device_group": device_group,
            "auth_token": auth_token,
            "heartbeat_interval": int(heartbeat_interval),
            "command_timeout": int(command_timeout),
            "max_concurrent_commands": 5,
            "log_level": "INFO",
            "reconnect_interval": 5,
            "max_reconnect_attempts": 0,
        }
    
    def _setup_full(self) -> None:
        """完整设置"""
        print("\n" + "=" * 50)
        print("🔧 完整设置 (服务端 + 被控端)")
        print("=" * 50)
        
        print("\n--- 第一步: 配置中转站服务端 ---")
        self._setup_server()
        
        print("\n--- 第二步: 配置被控端 Agent ---")
        self._setup_agent()
        
        print("\n" + "=" * 50)
        print("✅ 完整设置完成!")
        print("=" * 50)
        print("\n启动顺序:")
        print("  1. 先启动中转站服务端: python hermes_relay.py server")
        print("  2. 再启动被控端 Agent: python hermes_relay.py agent")
    
    def _start_server(self, config_path: Path) -> None:
        """启动服务端"""
        print("\n🚀 启动中转站服务端...")
        os.system(f"python hermes_relay.py server --config {config_path}")
    
    def _start_agent(self, config_path: Path) -> None:
        """启动 Agent"""
        print("\n🚀 启动被控端 Agent...")
        os.system(f"python hermes_relay.py agent --config {config_path}")


def quick_setup() -> None:
    """快速设置 (一键)"""
    print("\n🚀 Hermes Relay 快速设置")
    print("-" * 40)
    
    wizard = SetupWizard()
    
    # 扫码配置飞书
    print("\n📱 步骤 1: 配置飞书机器人")
    from .feishu.onboard import qr_register, print_setup_result
    
    result = qr_register(initial_domain="feishu", timeout_seconds=600)
    if not result:
        print("❌ 扫码失败，请手动配置")
        return
    
    print_setup_result(result)
    
    # 生成配置
    import socket
    hostname = socket.gethostname()
    
    server_config = {
        "ws_host": "0.0.0.0",
        "ws_port": 8765,
        "feishu": {
            "app_id": result["app_id"],
            "app_secret": result["app_secret"],
            "domain": result["domain"],
            "encrypt_key": "",
            "verification_token": "",
        },
        "heartbeat_timeout": 60,
        "approval_timeout": 300,
        "log_level": "INFO",
    }
    
    agent_config = {
        "server_url": "ws://localhost:8765",
        "device_name": hostname,
        "device_group": "default",
        "auth_token": "",
        "heartbeat_interval": 30,
        "command_timeout": 60,
        "max_concurrent_commands": 5,
        "log_level": "INFO",
        "reconnect_interval": 5,
        "max_reconnect_attempts": 0,
    }
    
    # 保存配置
    config_dir = Path("config")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    with open(config_dir / "relay_config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(server_config, f, default_flow_style=False, allow_unicode=True)
    
    with open(config_dir / "agent_config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(agent_config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"\n✅ 配置已保存到 {config_dir}/")
    
    # 询问启动
    print("\n请选择:")
    print("  1. 启动服务端")
    print("  2. 启动 Agent")
    print("  3. 退出")
    
    choice = input("\n请选择 [1-3]: ").strip()
    
    if choice == "1":
        os.system(f"python hermes_relay.py server --config {config_dir / 'relay_config.yaml'}")
    elif choice == "2":
        os.system(f"python hermes_relay.py agent --config {config_dir / 'agent_config.yaml'}")
