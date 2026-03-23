# LobsterPress 手动记忆管理指南

> **状态**: 临时方案（等待 OpenClaw Issue #52810 修复）
> **版本**: v4.0.49+

由于 OpenClaw lifecycle hooks（`api.on()`）当前不触发，你需要显式调用 MCP 工具来管理记忆。

---

## 核心工具

| 工具 | 用途 | 何时调用 |
|------|------|----------|
| `lobster_assemble` | 召回历史记忆 | 对话开始前 / 需要记忆时 |
| `lobster_ingest` | 保存新消息 | 对话结束后 |
| `lobster_compress` | 压缩旧消息 | 消息数过多时（可选） |

---

## 使用场景

### 场景 1：新对话开始

在开始新对话前，调用 `lobster_assemble` 获取相关历史记忆：

```json
{
  "tool": "lobster_assemble",
  "arguments": {
    "conversation_id": "conv_123",
    "token_budget": 128000
  }
}
```

返回示例：
```json
{
  "assembled": [
    {"tier": "semantic", "content": "用户偏好使用 PostgreSQL 作为主数据库"},
    {"tier": "episodic", "content": "上次讨论了用户认证方案"},
    {"tier": "recent", "content": "最近的对话内容..."}
  ],
  "total_tokens": 2500
}
```

### 场景 2：对话结束

对话结束后，调用 `lobster_ingest` 保存新消息：

```json
{
  "tool": "lobster_ingest",
  "arguments": {
    "conversation_id": "conv_123",
    "messages": [
      {
        "id": "msg_001",
        "role": "user",
        "content": "我们决定用 Redis 做缓存",
        "timestamp": "2026-03-23T10:00:00Z"
      },
      {
        "id": "msg_002",
        "role": "assistant",
        "content": "好的，Redis 是一个很好的选择...",
        "timestamp": "2026-03-23T10:00:30Z"
      }
    ]
  }
}
```

返回示例：
```json
{
  "ingested": 2,
  "conversation_id": "conv_123"
}
```

### 场景 3：消息数过多

当消息数超过 50 条时，调用 `lobster_compress` 压缩旧消息：

```json
{
  "tool": "lobster_compress",
  "arguments": {
    "conversation_id": "conv_123",
    "force": false
  }
}
```

---

## 推荐工作流

### Agent 启动时

```
1. 接收用户消息
2. 调用 lobster_assemble 获取历史记忆
3. 将记忆注入上下文
4. 生成回复
5. 调用 lobster_ingest 保存本轮对话
```

### 心跳检查时

```
1. 调用 lobster_describe 检查消息数
2. 如果消息数 > 50，调用 lobster_compress
```

---

## 配置选项

在 OpenClaw 配置中，你可以设置以下参数：

```json
{
  "plugins": {
    "entries": {
      "lobster-press": {
        "enabled": true,
        "config": {
          "lifecycleEnabled": false,  // 禁用自动 lifecycle hooks
          "llmProvider": "deepseek",
          "llmModel": "deepseek-chat",
          "llmApiKey": "${LOBSTER_LLM_API_KEY}",
          "contextThreshold": 0.8,
          "freshTailCount": 32,
          "namespace": "default"
        }
      }
    }
  }
}
```

---

## 常见问题

### Q: 为什么要手动调用？

A: OpenClaw 的 lifecycle hooks（`before_agent_start`、`agent_end`）当前不触发（Issue #52810）。这是临时方案。

### Q: 会影响记忆质量吗？

A: 不会。手动调用和自动调用的效果完全相同，只是触发方式不同。

### Q: 什么时候会恢复自动模式？

A: 等待 OpenClaw 修复 Issue #52810 后，我们会重新启用 lifecycle hooks。

---

## 相关链接

- [OpenClaw Issue #52810](https://github.com/openclaw/openclaw/issues/52810)
- [LobsterPress README](../README.md)
- [API 文档](API.md)
