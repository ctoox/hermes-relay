"""
Hermes Relay - 轻量级 CLI
用于快速启动和管理
"""

import sys
import os
import argparse
from pathlib import Path


def print_banner():
    """打印横幅"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██╗  ██╗███████╗██████╗ ███╗   ███╗███████╗███████╗    ║
║   ██║  ██║██╔════╝██╔══██╗████╗ ████║██╔════╝██╔════╝    ║
║   ███████║█████╗  ██████╔╝██╔████╔██║█████╗  ███████╗    ║
║   ██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══╝  ╚════██║    ║
║   ██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗███████║    ║
║   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝    ║
║                                                           ║
║              Relay - Remote Control System                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)


def cmd_server(args):
    """启动服务端"""
    from relay_server.main import RelayServer
    from relay_server.config import load_config
    import asyncio
    
    config = load_config(args.config) if args.config else load_config()
    if args.host:
        config.ws_host = args.host
    if args.port:
        config.ws_port = args.port
    
    server = RelayServer(config)
    asyncio.run(server.run())


def cmd_agent(args):
    """启动 Agent"""
    from agent_client.main import RelayAgent
    from agent_client.config import load_config
    import asyncio
    
    config = load_config(args.config) if args.config else load_config()
    if args.server:
        config.server_url = args.server
    if args.name:
        config.device_name = args.name
    if args.group:
        config.device_group = args.group
    
    agent = RelayAgent(config)
    asyncio.run(agent.run())


def cmd_setup(args):
    """运行设置向导"""
    from relay_server.setup import SetupWizard
    wizard = SetupWizard()
    wizard.run()


def cmd_quick(args):
    """快速设置"""
    from relay_server.setup import quick_setup
    quick_setup()


def cmd_onboard(args):
    """扫码配置"""
    from relay_server.feishu.onboard import qr_register, print_setup_result
    
    result = qr_register(initial_domain=args.domain, timeout_seconds=args.timeout)
    if result:
        print_setup_result(result)
    else:
        print("❌ 扫码注册失败")
        sys.exit(1)


def cmd_status(args):
    """查看状态"""
    import psutil
    
    print("\n📊 System Status")
    print("-" * 40)
    print(f"CPU: {psutil.cpu_percent()}%")
    print(f"Memory: {psutil.virtual_memory().percent}%")
    print(f"Disk: {psutil.disk_usage('/').percent}%")
    print()


def cmd_gui(args):
    """启动桌面端"""
    try:
        from desktop_app import main
        main()
    except ImportError:
        print("❌ PySide6 not installed. Run: pip install PySide6")
        sys.exit(1)


def main():
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="Hermes Relay - Remote Control System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Server
    server_parser = subparsers.add_parser("server", help="Start relay server")
    server_parser.add_argument("--config", help="Config file path")
    server_parser.add_argument("--host", default="0.0.0.0", help="Listen host")
    server_parser.add_argument("--port", type=int, default=8765, help="Listen port")
    
    # Agent
    agent_parser = subparsers.add_parser("agent", help="Start agent")
    agent_parser.add_argument("--config", help="Config file path")
    agent_parser.add_argument("--server", help="Relay server URL")
    agent_parser.add_argument("--name", help="Device name")
    agent_parser.add_argument("--group", default="default", help="Device group")
    
    # Setup
    subparsers.add_parser("setup", help="Run setup wizard")
    
    # Quick
    subparsers.add_parser("quick", help="Quick setup (QR code)")
    
    # Onboard
    onboard_parser = subparsers.add_parser("onboard", help="QR code setup")
    onboard_parser.add_argument("--domain", default="feishu", choices=["feishu", "lark"])
    onboard_parser.add_argument("--timeout", type=int, default=600)
    
    # Status
    subparsers.add_parser("status", help="Show system status")
    
    # GUI
    subparsers.add_parser("gui", help="Launch desktop app")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        print("\nQuick start:")
        print("  hermes-relay setup    # Run setup wizard")
        print("  hermes-relay server   # Start server")
        print("  hermes-relay agent    # Start agent")
        print("  hermes-relay gui      # Launch desktop app")
        sys.exit(0)
    
    commands = {
        "server": cmd_server,
        "agent": cmd_agent,
        "setup": cmd_setup,
        "quick": cmd_quick,
        "onboard": cmd_onboard,
        "status": cmd_status,
        "gui": cmd_gui,
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
