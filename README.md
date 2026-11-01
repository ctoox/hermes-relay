# Hermes Relay - 远程控制系统

基于飞书的远程电脑控制系统，支持自然语言操作、命令审批、多设备群控。

## 功能特性

- 🚀 **飞书集成** - 通过飞书消息控制远程电脑
- 🤖 **自然语言** - 支持中英文自然语言命令
- ✅ **命令审批** - 危险命令需要飞书端确认
- 📱 **多设备管理** - 支持一对多群控
- 🔄 **自动重连** - 断线自动重连，保证稳定性
- 📊 **系统监控** - 实时监控设备状态

## 项目结构

```
hermes-relay/
├── hermes_relay.py          # Python 版主入口
├── relay_server/            # 中转站服务端
│   ├── main.py              # 服务端主模块
│   ├── config.py            # 配置管理
│   ├── feishu/              # 飞书通信层
│   ├── device/              # 设备管理
│   ├── command/             # 命令执行
│   ├── nlp/                 # 自然语言解析
│   └── websocket/           # WebSocket 服务
├── agent_client/            # 被控端 Agent
│   ├── main.py              # Agent 主模块
│   ├── config.py            # 配置管理
│   ├── executor/            # 命令执行器
│   ├── websocket/           # WebSocket 客户端
│   └── system/              # 系统信息
├── shared/                  # 共享协议
├── config/                  # 配置文件示例
└── scripts/                 # 启动脚本

hermes-relay-rust/           # Rust 性能版
├── Cargo.toml
└── src/
    ├── main.rs              # 主入口
    ├── protocol/            # 协议定义
    ├── server/              # 服务端
    ├── client/              # 客户端
    ├── device/              # 设备管理
    ├── command/             # 命令执行
    ├── nlp/                 # NLP 解析
    └── feishu/              # 飞书通信
```

## 快速开始

### Python 稳定版

1. 安装依赖：
```bash
cd hermes-relay
pip install -r requirements.txt
```

2. 配置飞书应用：
   - 访问 [飞书开放平台](https://open.feishu.cn/)
   - 创建应用，获取 App ID 和 App Secret
   - 配置事件订阅和机器人能力

3. 配置中转站：
```bash
cp config/relay_config.example.yaml config/relay_config.yaml
# 编辑配置文件，填入飞书凭据
```

4. 启动中转站：
```bash
python hermes_relay.py server --config config/relay_config.yaml
```

5. 配置被控端：
```bash
cp config/agent_config.example.yaml config/agent_config.yaml
# 编辑配置文件，填入中转站地址
```

6. 启动被控端：
```bash
python hermes_relay.py agent --config config/agent_config.yaml
```

### Rust 性能版

1. 安装 Rust：
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. 编译：
```bash
cd hermes-relay-rust
cargo build --release
```

3. 运行：
```bash
# 启动服务端
./target/release/hermes-relay server --config config.toml

# 启动被控端
./target/release/hermes-relay agent --server ws://localhost:8765 --name "我的电脑"
```

## 使用方法

### 飞书命令示例

**设备管理：**
- `设备列表` - 查看所有设备
- `设备状态` - 查看设备详情

**系统操作：**
- `查看IP` / `ipconfig` - 查看网络配置
- `查看进程` / `tasklist` - 查看运行进程
- `系统信息` / `systeminfo` - 查看系统信息

**自然语言：**
- `打开记事本` → 启动 notepad
- `查看当前目录` → 执行 dir
- `测试到百度的连接` → ping baidu.com

**需要审批的命令：**
- `关闭 chrome` - 需要确认
- `删除文件 xxx` - 需要确认
- `重启电脑` - 需要确认

### 审批流程

当执行危险命令时：
1. 飞书收到审批卡片
2. 显示命令详情和风险等级
3. 选择：允许一次 / 本次会话 / 永久允许 / 拒绝
4. 命令执行或取消

## 配置说明

### 中转站配置 (relay_config.yaml)

```yaml
ws_host: "0.0.0.0"        # WebSocket 监听地址
ws_port: 8765              # WebSocket 监听端口

feishu:
  app_id: "cli_xxx"        # 飞书应用 ID
  app_secret: "xxx"        # 飞书应用密钥
  domain: "feishu"         # feishu(中国) / lark(国际)

heartbeat_timeout: 60      # 心跳超时(秒)
approval_timeout: 300      # 审批超时(秒)
```

### 被控端配置 (agent_config.yaml)

```yaml
device_name: "我的电脑"     # 设备名称
device_group: "default"    # 设备组
server_url: "ws://192.168.1.100:8765"  # 中转站地址

heartbeat_interval: 30     # 心跳间隔(秒)
command_timeout: 60        # 命令超时(秒)
```

## 版本对比

| 特性 | Python 版 | Rust 版 |
|------|-----------|---------|
| 开发速度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 运行性能 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 内存占用 | 中等 | 极低 |
| 启动速度 | 快 | 极快 |
| 并发能力 | 中等 | 极强 |
| 稳定性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 生态丰富 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**推荐：**
- 功能开发、快速原型 → Python 版
- 高性能、低资源 → Rust 版

## 安全建议

1. **使用认证令牌** - 配置 `auth_token` 防止未授权连接
2. **启用加密** - 生产环境建议启用 TLS 加密
3. **限制命令** - 根据需要调整命令白名单/黑名单
4. **网络隔离** - 将中转站部署在内网，使用飞书访问

## 常见问题

**Q: 飞书收不到消息？**
A: 检查飞书应用配置，确保已启用机器人能力和事件订阅。

**Q: 被控端连不上中转站？**
A: 检查网络连通性，确保防火墙开放 WebSocket 端口。

**Q: 命令执行超时？**
A: 调整 `command_timeout` 配置，或检查命令是否正确。

## 许可证

MIT License
