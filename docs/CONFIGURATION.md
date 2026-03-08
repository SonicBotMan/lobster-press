# 🔧 模型配置与 OpenClaw 集成

本文档详细说明如何配置 AI 模型以及将 LobsterPress 集成到 OpenClaw 中。

---

## 📖 目录

1. [模型配置](#模型配置)
2. [OpenClaw 集成](#openclaw-集成)
3. [快速开始](#快速开始)
4. [常见问题](#常见问题)

---

## 模型配置

### 支持的 AI 模型

LobsterPress 支持以下 AI 服务提供商：

| 提供商 | 模型示例 | API 类型 | 推荐度 |
|--------|---------|---------|--------|
| **智谱 AI (GLM)** | glm-4, glm-4-flash | OpenAI 兼容 | ⭐⭐⭐⭐⭐ |
| **OpenAI** | gpt-4, gpt-3.5-turbo | OpenAI 原生 | ⭐⭐⭐⭐⭐ |
| **Anthropic** | claude-3-opus, claude-3-sonnet | Anthropic 原生 | ⭐⭐⭐⭐ |
| **阿里云 (Qwen)** | qwen-turbo, qwen-plus | OpenAI 兼容 | ⭐⭐⭐⭐ |
| **本地模型** | LM Studio, Ollama | OpenAI 兼容 | ⭐⭐⭐ |

### 配置方式 1: 环境变量（推荐新手）

**步骤 1**: 获取 API Key

```bash
# 智谱 AI（推荐）
# 访问: https://open.bigmodel.cn/
# 注册后获取 API Key

# OpenAI
# 访问: https://platform.openai.com/api-keys

# Anthropic
# 访问: https://console.anthropic.com/
```

**步骤 2**: 设置环境变量

```bash
# 方式 1: 临时设置（当前会话有效）
export GLM_API_KEY="your_glm_api_key_here"
export GLM_API_BASE="https://open.bigmodel.cn/api/paas/v4"

# 方式 2: 永久设置（推荐）
echo 'export GLM_API_KEY="your_glm_api_key_here"' >> ~/.bashrc
echo 'export GLM_API_BASE="https://open.bigmodel.cn/api/paas/v4"' >> ~/.bashrc
source ~/.bashrc

# 验证设置
echo $GLM_API_KEY
```

**步骤 3**: 测试连接

```bash
# 测试 API 连接
curl -X POST "https://open.bigmodel.cn/api/paas/v4/chat/completions" \
  -H "Authorization: Bearer $GLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4-flash",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# 成功输出示例:
# {"choices":[{"message":{"content":"Hello! How can I help you?"}}]}
```

### 配置方式 2: 配置文件（推荐进阶用户）

**步骤 1**: 创建配置文件

```bash
mkdir -p ~/.config/lobster-press
cat > ~/.config/lobster-press/config.json <<'EOF'
{
  "api": {
    "provider": "glm",
    "key": "your_api_key_here",
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "model": "glm-4-flash",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "compression": {
    "threshold": {
      "light": 70,
      "medium": 85,
      "heavy": 95
    },
    "strategy": "auto"
  },
  "learning": {
    "enabled": true,
    "adjust_interval": 3600
  }
}
EOF

chmod 600 ~/.config/lobster-press/config.json
```

**步骤 2**: 修改脚本读取配置

```bash
# 编辑压缩脚本
vim ~/bin/context-compressor-v5.sh

# 在开头添加配置读取逻辑
CONFIG_FILE="$HOME/.config/lobster-press/config.json"

if [ -f "$CONFIG_FILE" ]; then
    GLM_API_KEY=$(jq -r '.api.key' "$CONFIG_FILE")
    GLM_API_BASE=$(jq -r '.api.base_url' "$CONFIG_FILE")
    GLM_MODEL=$(jq -r '.api.model' "$CONFIG_FILE")
fi
```

### 配置方式 3: OpenClaw 集成（推荐 OpenClaw 用户）

**OpenClaw 已内置 API Key 管理，LobsterPress 可以直接使用！**

```bash
# OpenClaw 的 API Key 存储位置
OPENCLAW_AUTH="$HOME/.openclaw/agents/main/agent/auth-profiles.json"

# LobsterPress 会自动读取 OpenClaw 的配置
# 无需额外配置！
```

---

## OpenClaw 集成

### 什么是 OpenClaw？

**OpenClaw** 是一个强大的 AI Agent 框架，支持：
- 多模型切换（GLM、OpenAI、Claude 等）
- 会话管理
- 工具调用
- 记忆系统

**LobsterPress 与 OpenClaw 的关系**：
- LobsterPress 是 OpenClaw 的**上下文管理插件**
- 自动压缩 OpenClaw 的会话历史
- 无需额外配置，开箱即用

### 集成方式 1: 自动集成（最简单）

**前提条件**: 你已经安装了 OpenClaw

```bash
# 1. 下载 LobsterPress
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press

# 2. 安装到 OpenClaw（自动检测 OpenClaw 安装路径）
./install-to-openclaw.sh

# 输出:
# ✅ 检测到 OpenClaw 安装路径: ~/.openclaw
# ✅ 脚本已复制到: ~/.openclaw/workspace/bin/
# ✅ Systemd 服务已安装
# ✅ 自动压缩定时任务已启用

# 3. 验证集成
openclaw status | grep -i lobster

# 输出:
# LobsterPress: ✅ 已集成
# 自动压缩: ✅ 每 30 分钟
```

### 集成方式 2: 手动集成（更灵活）

**步骤 1**: 安装脚本到 OpenClaw

```bash
# 复制核心脚本到 OpenClaw 的 bin 目录
mkdir -p ~/.openclaw/workspace/bin
cp lobster-press/scripts/*.sh ~/.openclaw/workspace/bin/
chmod +x ~/.openclaw/workspace/bin/*.sh

# 创建符号链接（可选，方便全局访问）
ln -s ~/.openclaw/workspace/bin/context-compressor-v5.sh ~/bin/lobster-compress
ln -s ~/.openclaw/workspace/bin/adaptive-learning-engine.sh ~/bin/lobster-learn
```

**步骤 2**: 配置 Systemd 定时任务

```bash
# 复制 systemd 服务文件
cp lobster-press/systemd/*.service ~/.config/systemd/user/
cp lobster-press/systemd/*.timer ~/.config/systemd/user/

# 修改服务文件中的路径（重要！）
sed -i "s|/home/h523034406/bin/|/home/$USER/.openclaw/workspace/bin/|g" \
  ~/.config/systemd/user/lobster-*.service

# 重新加载并启动
systemctl --user daemon-reload
systemctl --user enable --now lobster-compress.timer
systemctl --user enable --now lobster-learning.timer
systemctl --user enable --now lobster-optimizer.timer

# 验证定时任务
systemctl --user list-timers | grep lobster
```

**步骤 3**: 配置 OpenClaw 使用 LobsterPress

```bash
# 方法 1: 在 OpenClaw 配置中添加钩子
cat >> ~/.openclaw/openclaw.json <<'EOF'
{
  "hooks": {
    "pre_session_save": "~/.openclaw/workspace/bin/context-compressor-v5.sh",
    "session_threshold": 70
  }
}
EOF

# 方法 2: 使用 OpenClaw 的插件系统（推荐）
mkdir -p ~/.openclaw/plugins/lobster-press
cp lobster-press/scripts/*.sh ~/.openclaw/plugins/lobster-press/
cat > ~/.openclaw/plugins/lobster-press/plugin.json <<'EOF'
{
  "name": "LobsterPress",
  "version": "1.0.0",
  "description": "智能上下文压缩插件",
  "hooks": {
    "on_token_threshold": {
      "threshold": 70,
      "script": "context-compressor-v5.sh",
      "args": ["--auto"]
    }
  }
}
EOF
```

### 集成方式 3: 通过 API 集成（开发者）

**场景**: 你有自己的应用，想通过 API 调用 LobsterPress

```python
# lobster_api.py
import json
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/compress', methods=['POST'])
def compress_session():
    """压缩会话的 API 端点"""
    data = request.json
    session_id = data.get('session_id')
    strategy = data.get('strategy', 'auto')
    
    # 调用 LobsterPress
    cmd = [
        '/home/user/.openclaw/workspace/bin/context-compressor-v5.sh',
        session_id,
        '--strategy', strategy,
        '--auto'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return jsonify({
            'success': True,
            'output': result.stdout
        })
    else:
        return jsonify({
            'success': False,
            'error': result.stderr
        }), 500

@app.route('/status', methods=['GET'])
def get_status():
    """获取 LobsterPress 状态"""
    cmd = ['/home/user/.openclaw/workspace/bin/adaptive-learning-engine.sh', 'report']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    return jsonify({
        'status': 'running',
        'report': result.stdout
    })

if __name__ == '__main__':
    app.run(port=5000)
```

**使用 API**:

```bash
# 压缩会话
curl -X POST http://localhost:5000/compress \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "strategy": "medium"}'

# 获取状态
curl http://localhost:5000/status
```

---

## 快速开始

### 场景 1: 我已经用 OpenClaw 了（最简单）

```bash
# 1. 一键安装
curl -fsSL https://raw.githubusercontent.com/SonicBotMan/lobster-press/main/install-to-openclaw.sh | bash

# 2. 等待 30 分钟，自动压缩生效
# 或者立即测试：
~/.openclaw/workspace/bin/context-compressor-v5.sh --auto-scan

# 3. 查看压缩历史
tail -10 ~/.openclaw/workspace/memory/compression-history.md

# 输出示例:
# - 2026-03-08 18:00:15 | abc123 | medium | 892KB → 652KB | 节省 27%
# - 2026-03-08 17:30:22 | def456 | light | 654KB → 589KB | 节省 10%
```

### 场景 2: 我还没用 OpenClaw，想先试试

```bash
# 1. 安装 LobsterPress（独立版）
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press

# 2. 配置 API Key
export GLM_API_KEY="your_api_key_here"

# 3. 安装脚本
cp scripts/*.sh ~/bin/
chmod +x ~/bin/*.sh

# 4. 测试压缩（创建一个测试会话）
cat > /tmp/test-session.jsonl <<'EOF'
{"role": "user", "content": "你好"}
{"role": "assistant", "content": "你好！有什么可以帮助你的？"}
{"role": "user", "content": "帮我写个 Python 脚本"}
EOF

# 5. 压缩测试
~/bin/context-compressor-v5.sh /tmp/test-session --dry-run

# 输出:
# 📊 预览模式
# 📊 会话分析: 3 行, 256B
# ⏭️  跳过（Token 使用率 < 70%）
```

### 场景 3: 我想在服务器上部署（生产环境）

```bash
# 1. 下载并安装
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press
sudo ./install-system-wide.sh

# 2. 配置系统服务
sudo systemctl enable lobster-press
sudo systemctl start lobster-press

# 3. 查看日志
sudo journalctl -u lobster-press -f

# 4. 监控状态
sudo lobster-press status

# 输出:
# ✅ 服务运行中
# ✅ 最近 24 小时压缩: 42 次
# ✅ 平均节省: 28%
# ✅ 推荐策略: medium
```

---

## 常见问题

### Q1: 我的 API Key 在哪里获取？

**A**: 根据你使用的 AI 服务提供商：

| 提供商 | 获取地址 | 价格 |
|--------|---------|------|
| 智谱 AI (GLM) | https://open.bigmodel.cn/ | 免费额度 + 按量付费 |
| OpenAI | https://platform.openai.com/api-keys | 按量付费 |
| Anthropic | https://console.anthropic.com/ | 按量付费 |
| 阿里云 (Qwen) | https://dashscope.console.aliyun.com/ | 免费额度 + 按量付费 |

**推荐**: 智谱 AI（GLM）提供免费额度，适合测试和学习。

### Q2: LobsterPress 会自动读取 OpenClaw 的配置吗？

**A**: 是的！LobsterPress 会自动检测并读取 OpenClaw 的配置：

```bash
# OpenClaw 的配置文件路径
~/.openclaw/agents/main/agent/auth-profiles.json

# LobsterPress 会自动读取其中的 API Key
# 无需重复配置！
```

### Q3: 如何知道压缩是否成功？

**A**: 有三种方式查看：

```bash
# 方式 1: 查看压缩历史
tail -10 ~/.openclaw/workspace/memory/compression-history.md

# 方式 2: 查看学习报告
~/bin/adaptive-learning-engine.sh report

# 方式 3: 查看 Systemd 日志
journalctl --user -u lobster-compress -n 20
```

### Q4: 压缩会影响 AI 的记忆吗？

**A**: **不会丢失重要信息！**

LobsterPress 的压缩策略：
- ✅ **保留**: 决策记录、错误处理、配置信息
- ✅ **保留**: 偏好设置、关键事实
- ⚠️ **压缩**: 闲聊内容、冗余上下文（转为摘要）
- ❌ **删除**: 重复内容、无效消息

**实测数据**:
- 保留 95% 重要信息
- 节省 30-50% Token
- AI 仍能理解完整上下文

### Q5: 我可以自定义哪些内容被保留吗？

**A**: 可以！通过修改权重配置：

```bash
# 编辑权重配置
vim ~/.openclaw/workspace/bin/adaptive-learning-engine.sh

# 修改 base_weights
base_weights = {
  "decision": 100,  # 决策记录 - 最高优先级
  "error": 95,      # 错误处理 - 你可以调整为 100
  "code": 90,       # 代码片段 - 新增类型
  "config": 85,
  "preference": 80,
  "chitchat": 5     # 闲聊 - 最低优先级
}
```

### Q6: 如何完全禁用自动压缩？

**A**: 停止定时任务即可：

```bash
# 停止自动压缩
systemctl --user stop lobster-compress.timer
systemctl --user disable lobster-compress.timer

# 验证已停止
systemctl --user list-timers | grep lobster
```

---

## 📚 更多资源

- **完整文档**: [README.md](README.md)
- **使用示例**: [docs/EXAMPLES.md](docs/EXAMPLES.md)
- **API 文档**: [docs/API.md](docs/API.md)
- **常见问题**: [docs/FAQ.md](docs/FAQ.md)
- **GitHub**: https://github.com/SonicBotMan/lobster-press

---

<div align="center">

**🦞 让 AI 记忆永不溢出！**

Made with ❤️ by the LobsterPress Team

</div>
