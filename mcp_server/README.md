# LobsterPress MCP Server

> **推荐方式**：如果你在使用 OpenClaw，请优先使用
> [插件安装模式](../README.md#-openclaw-插件推荐)，
> 更简单，无需手动管理进程。
>
> 本文档描述直接运行 MCP Server 的高级用法，适合非 OpenClaw 环境
> 或需要自定义集成的场景。

基于 Model Context Protocol (MCP) 的 OpenClaw 会话压缩服务。

## 安装

```bash
cd lobster-press/mcp_server
pip install -r requirements.txt
```

## 使用方法

### 1. 与 Claude Desktop 集成

在 Claude Desktop 配置文件中添加：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "lobster-press": {
      "command": "python3",
      "args": ["/path/to/lobster-press/mcp_server/lobster_mcp_server.py"]
    }
  }
}
```

### 2. 与 Cursor 集成

在 Cursor 设置中添加 MCP 服务器配置。

### 3. 测试模式

```bash
python3 lobster_mcp_server.py --test
```

## 可用工具

### 1. compress_session

压缩 OpenClaw 会话历史。

```json
{
  "session_id": "abc123",
  "strategy": "medium",
  "dry_run": false
}
```

**参数：**
- `session_id`: 会话 ID（文件名，不含扩展名）
- `strategy`: 压缩策略（light/medium/aggressive）
- `dry_run`: 是否仅预览（默认 false）

**返回：**
```json
{
  "status": "success",
  "original_messages": 1000,
  "compressed_messages": 500,
  "tokens_saved": 50000,
  "compression_ratio": "50%"
}
```

### 2. preview_compression

预览压缩效果。

```json
{
  "session_id": "abc123",
  "strategy": "medium"
}
```

### 3. get_compression_stats

获取压缩统计数据。

### 4. update_weights

更新消息类型权重配置。

```json
{
  "weights": {
    "decision": 0.3,
    "error": 0.25,
    "config": 0.2,
    "preference": 0.15
  }
}
```

### 5. list_sessions

列出所有可压缩的会话。

```json
{
  "min_tokens": 10000
}
```

## 压缩策略

| 策略 | 保留比例 | 适用场景 |
|------|---------|---------|
| light | 70% | 保留大部分信息 |
| medium | 50% | 平衡压缩与保留 |
| aggressive | 30% | 最大压缩 |

## 消息评分

消息按以下权重评分：

| 类型 | 权重 | 示例 |
|------|------|------|
| decision | 0.3 | "决定采用方案A" |
| error | 0.25 | "发生错误：连接超时" |
| config | 0.2 | "API Key 已更新" |
| preference | 0.15 | "用户偏好使用 GLM-4" |
| context | 0.05 | "当前系统版本 2026.3.2" |
| chitchat | 0.02 | "哈哈，不错" |

## 资源访问

MCP 客户端可以通过以下 URI 访问会话资源：

```
lobster://sessions/{session_id}
```

## 示例

### Python 客户端

```python
import json
import subprocess

def call_mcp_tool(tool_name, arguments):
    request = {
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    proc = subprocess.Popen(
        ["python3", "lobster_mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )
    
    stdout, _ = proc.communicate(json.dumps(request))
    return json.loads(stdout)

# 列出会话
result = call_mcp_tool("list_sessions", {"min_tokens": 10000})
print(result)

# 预览压缩
result = call_mcp_tool("preview_compression", {
    "session_id": "abc123",
    "strategy": "medium"
})
print(result)

# 执行压缩
result = call_mcp_tool("compress_session", {
    "session_id": "abc123",
    "strategy": "medium"
})
print(result)
```

## 安全性

- ✅ 自动备份原文件（带时间戳）
- ✅ 仅本地操作，不上传数据
- ✅ 支持预览模式（dry_run）

## 许可证

MIT License

## 相关

- Issue #42: v2.0 架构演进：向 MCP Server 演进
- Issue #28: MCP 协议支持
