# VNC代理服务器

一个智能的VNC代理服务器，支持单用户连接控制和用户决策机制。

## 主要功能

✅ **单用户连接控制** - 同时只允许一个客户端连接VNC服务器
✅ **智能决策机制** - 新用户连接时弹出5秒倒计时决策窗口
✅ **用户友好界面** - 大号按钮："我还要继续使用"、"让新用户连接"
✅ **1分钟冷却期** - 被断开或拒绝的用户都有60秒冷却期
✅ **标准RFB协议** - 完全符合VNC协议规范
✅ **中文提示消息** - VNC客户端显示友好的中文拒绝原因

## 系统要求

- Python 3.8+
- macOS / Windows / Linux
- VNC服务器（如TightVNC、RealVNC等）

## 安装步骤

```bash
# 克隆项目
git clone <repository-url>
cd vnc_proxy2

# 同步库及虚拟环境
uv sync
```

## 使用方法

### 启动代理服务器

```bash
# GUI模式（推荐）
uv run python vnc_proxy.py

# 命令行模式
uv run python vnc_proxy.py --no-gui

# 自定义参数
uv run python vnc_proxy.py --vnc-host 192.168.1.100 --proxy-port 5902
```

### 命令行参数

- `--vnc-host` - VNC服务器地址（默认：127.0.0.1）
- `--vnc-port` - VNC服务器端口（默认：5900）
- `--proxy-port` - 代理服务器端口（默认：5901）
- `--no-gui` - 不启动GUI界面（仅命令行模式）

## 工作流程

1. **首个用户连接** → 直接建立VNC会话
2. **新用户请求连接** → 显示决策对话框（5秒倒计时）
3. **用户选择**：
   - "我还要继续使用" → 新用户被拒绝并进入1分钟冷却期
   - "让新用户连接" → 老用户断开并进入1分钟冷却期，新用户获得连接
4. **冷却期保护** → 1分钟内重连显示中文拒绝消息

## 文件结构

```
vnc_proxy2/
├── vnc_proxy.py       # 主程序
├── pyproject.toml     # 项目配置
├── README.md          # 使用说明
├── requirements.txt   # 依赖列表
└── vnc_proxy.log      # 运行日志
```

## 错误消息

- **服务器被占用** → "服务器正被其他用户使用，请稍后再试。"
- **VNC连接失败** → "无法连接到VNC服务器，请稍后再试。"

## 许可证

MIT License