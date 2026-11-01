"""
Hermes Relay - 主入口
根据参数启动服务端、被控端或运行设置向导
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Hermes Relay - 远程控制系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行设置向导
  python hermes_relay.py setup
  
  # 快速设置 (一键配置)
  python hermes_relay.py quick
  
  # 启动中转站服务端
  python hermes_relay.py server --config config/relay_config.yaml
  
  # 启动被控端 Agent
  python hermes_relay.py agent --config config/agent_config.yaml
  
  # 扫码配置飞书
  python hermes_relay.py onboard
        """
    )
    
    subparsers = parser.add_subparsers(dest="mode", help="运行模式")
    
    # 设置向导
    subparsers.add_parser("setup", help="运行设置向导")
    
    # 快速设置
    subparsers.add_parser("quick", help="快速设置 (一键配置)")
    
    # 扫码配置
    onboard_parser = subparsers.add_parser("onboard", help="扫码配置飞书机器人")
    onboard_parser.add_argument("--domain", default="feishu", choices=["feishu", "lark"],
                               help="域名 (feishu/lark)")
    onboard_parser.add_argument("--timeout", type=int, default=600, help="超时时间(秒)")
    
    # 服务端子命令
    server_parser = subparsers.add_parser("server", help="启动中转站服务端")
    server_parser.add_argument("--config", help="配置文件路径")
    server_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    server_parser.add_argument("--port", type=int, default=8765, help="监听端口")
    
    # 被控端子命令
    agent_parser = subparsers.add_parser("agent", help="启动被控端 Agent")
    agent_parser.add_argument("--config", help="配置文件路径")
    agent_parser.add_argument("--server", help="服务端地址 (ws://host:port)")
    agent_parser.add_argument("--name", help="设备名称")
    agent_parser.add_argument("--group", default="default", help="设备组")
    agent_parser.add_argument("--token", help="认证令牌")
    
    # 一键启动
    subparsers.add_parser("start", help="一键启动 (服务端 + Agent)")
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
    
    if args.mode == "setup":
        from relay_server.setup import SetupWizard
        wizard = SetupWizard()
        wizard.run()
        
    elif args.mode == "quick":
        from relay_server.setup import quick_setup
        quick_setup()
        
    elif args.mode == "onboard":
        from relay_server.feishu.onboard import qr_register, print_setup_result
        result = qr_register(initial_domain=args.domain, timeout_seconds=args.timeout)
        if result:
            print_setup_result(result)
        else:
            print("❌ 扫码注册失败")
            sys.exit(1)
        
    elif args.mode == "server":
        from relay_server.main import RelayServer
        from relay_server.config import load_config
        
        config = load_config(args.config) if args.config else load_config()
        if args.host:
            config.ws_host = args.host
        if args.port:
            config.ws_port = args.port
        
        import asyncio
        server = RelayServer(config)
        asyncio.run(server.run())
        
    elif args.mode == "agent":
        from agent_client.main import RelayAgent
        from agent_client.config import load_config
        
        config = load_config(args.config) if args.config else load_config()
        if args.server:
            config.server_url = args.server
        if args.name:
            config.device_name = args.name
        if args.group:
            config.device_group = args.group
        if args.token:
            config.auth_token = args.token
        
        import asyncio
        agent = RelayAgent(config)
        asyncio.run(agent.run())
        
    elif args.mode == "start":
        # 一键启动
        import subprocess
        import os
        
        config_dir = "config"
        server_config = os.path.join(config_dir, "relay_config.yaml")
        agent_config = os.path.join(config_dir, "agent_config.yaml")
        
        if not os.path.exists(server_config):
            print("❌ 未找到服务端配置，请先运行: python hermes_relay.py setup")
            sys.exit(1)
        
        print("🚀 一键启动 Hermes Relay...")
        
        # 启动服务端
        print("\n📡 启动中转站服务端...")
        server_proc = subprocess.Popen([
            sys.executable, "hermes_relay.py", "server",
            "--config", server_config
        ])
        
        # 等待服务端启动
        import time
        time.sleep(3)
        
        # 启动 Agent
        if os.path.exists(agent_config):
            print("💻 启动被控端 Agent...")
            agent_proc = subprocess.Popen([
                sys.executable, "hermes_relay.py", "agent",
                "--config", agent_config
            ])
        
        print("\n✅ 启动完成!")
        print("  服务端 PID:", server_proc.pid)
        if os.path.exists(agent_config):
            print("  Agent PID:", agent_proc.pid)
        print("\n按 Ctrl+C 停止...")
        
        try:
            server_proc.wait()
        except KeyboardInterrupt:
            print("\n正在停止...")
            server_proc.terminate()
            if os.path.exists(agent_config):
                agent_proc.terminate()


if __name__ == "__main__":
    main()
