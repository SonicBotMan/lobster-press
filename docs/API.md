# API 文档

## 📖 概述

LobsterPress 提供两种 API：
1. **MCP 工具 API**（推荐）：通过 OpenClaw MCP 协议调用
2. **命令行 API**：通过 Bash 脚本调用（遗留）

---

## 🔌 MCP 工具 API（v3.3.0+）

### 概述

LobsterPress 通过 MCP (Model Context Protocol) 协议提供以下工具：

| 工具名称 | 功能 | 版本 |
|---------|------|------|
| `lobster_compress` | 自动上下文压缩（真实 DAG） | v3.3.0+ |
| `compress_session` | 会话压缩（真实 DAG） | v3.3.1+ |
| `preview_compression` | 预览压缩效果 | v3.2.0+ |
| `get_compression_stats` | 获取压缩统计 | v3.2.0+ |
| `update_weights` | 更新评分权重 | v3.2.0+ |
| `list_sessions` | 列出可压缩会话 | v3.2.0+ |
| `lobster_grep` | 全文搜索历史对话 | v3.2.2+ |
| `lobster_describe` | 查看 DAG 摘要结构 | v3.2.2+ |
| `lobster_expand` | 展开摘要节点 | v3.2.2+ |

---

### `lobster_compress` - 自动上下文压缩 ⭐ v3.3.0+

**功能**：检查上下文使用率，超过阈值时执行真实的 DAG 压缩

**参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `conversation_id` | string | 是 | 对话 ID |
| `current_tokens` | integer | 是 | 当前 token 数量 |
| `token_budget` | integer | 是 | token 预算 |
| `force` | boolean | 否 | 是否强制压缩（默认 false） |

**返回值**：

```json
{
  "compressed": true,
  "conversation_id": "abc123",
  "current_tokens": 100000,
  "token_budget": 128000,
  "threshold": 0.75,
  "attempt": 1
}
```

**触发逻辑**：
- 默认阈值：75%（`token_budget * 0.75`）
- 当 `current_tokens >= threshold` 或 `force=true` 时触发压缩
- 使用真实的 `DAGCompressor.incremental_compact()`

**错误处理**（v3.3.1+）：
- 最多重试 3 次
- 指数退避：1s, 2s, 3s
- 失败时返回详细错误信息

**示例**：

```json
{
  "name": "lobster_compress",
  "arguments": {
    "conversation_id": "session-123",
    "current_tokens": 100000,
    "token_budget": 128000,
    "force": false
  }
}
```

---

### `compress_session` - 会话压缩 ⭐ v3.3.1+

**功能**：使用真实 DAG 压缩指定会话

**参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `session_id` | string | 是 | 会话 ID |
| `strategy` | string | 否 | 压缩策略：light/medium/aggressive（默认 medium） |
| `dry_run` | boolean | 否 | 预览模式（默认 false） |

**策略映射**（v3.3.1+）：

| 策略 | 阈值 | 说明 |
|------|------|------|
| `light` | 90% | 轻度压缩，保留更多上下文 |
| `medium` | 75% | 中度压缩，平衡保留与压缩 |
| `aggressive` | 50% | 激进压缩，最大化节省 token |

**返回值**：

```json
{
  "status": "success",
  "session_id": "abc123",
  "strategy": "medium",
  "threshold": 0.75,
  "compressed": true,
  "message_count": 150,
  "estimated_tokens": 45000,
  "method": "real_dag_v3.3.0",
  "attempt": 1
}
```

**重要变更**（v3.3.1）：
- ✅ 使用真实的 `DAGCompressor`（不再使用假 DAG）
- ✅ 调用 `incremental_compact()` 方法
- ✅ 错误处理和重试机制

**示例**：

```json
{
  "name": "compress_session",
  "arguments": {
    "session_id": "session-123",
    "strategy": "medium",
    "dry_run": false
  }
}
```

---

### `preview_compression` - 预览压缩效果

**功能**：预览压缩效果（不实际应用）

**参数**：同 `compress_session`

**返回值**：

```json
{
  "status": "preview",
  "session_id": "abc123",
  "original_messages": 200,
  "compressed_messages": 100,
  "original_tokens": 80000,
  "compressed_tokens": 40000,
  "tokens_saved": 40000,
  "compression_ratio": "50.0%",
  "strategy": "medium"
}
```

---

### `lobster_grep` - 全文搜索

**功能**：在 LobsterPress 记忆库中全文搜索历史对话（FTS5 + TF-IDF 重排序）

**参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 搜索关键词或短语 |
| `conversation_id` | string | 否 | 限定搜索范围的会话 ID |
| `limit` | integer | 否 | 最多返回条数（默认 5） |

**返回值**：

```json
{
  "results": [
    {
      "message_id": "msg-123",
      "conversation_id": "conv-456",
      "content": "相关消息内容...",
      "score": 0.95,
      "timestamp": "2026-03-19T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

### `lobster_describe` - 查看 DAG 结构

**功能**：查看 LobsterPress 的 DAG 摘要层级结构

**参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `conversation_id` | string | 否 | 会话 ID（可选，留空查全局） |

**返回值**：

```json
{
  "summaries": [
    {
      "summary_id": "sum-123",
      "depth": 0,
      "message_count": 10,
      "content": "摘要内容...",
      "created_at": "2026-03-19T10:30:00Z"
    }
  ]
}
```

---

### `lobster_expand` - 展开摘要节点

**功能**：将 DAG 摘要节点展开，还原其对应的原始消息（无损检索）

**参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `summary_id` | string | 是 | 要展开的摘要节点 ID |
| `max_depth` | integer | 否 | 最大展开层数（默认 2） |

**返回值**：

```json
{
  "summary_id": "sum-123",
  "messages": [
    {
      "message_id": "msg-1",
      "role": "user",
      "content": "原始消息内容...",
      "timestamp": "2026-03-19T10:00:00Z"
    }
  ]
}
```

---

## 🔧 命令行 API（遗留）

### `context-compressor-v5.sh`

主压缩引擎，处理单个会话或批量压缩。

#### 用法

```bash
./context-compressor-v5.sh [OPTIONS] <session_id>
```

#### 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `session_id` | string | 是 | 会话 ID（不带 .jsonl 扩展名） |
| `--strategy` | string | 否 | 压缩策略：light/medium/heavy |
| `--dry-run` | flag | 否 | 预览模式，不实际应用 |
| `--auto-scan` | flag | 否 | 自动扫描所有会话 |
| `--help` | flag | 否 | 显示帮助信息 |

#### 示例

```bash
# 压缩单个会话（自动选择策略）
./context-compressor-v5.sh abc123

# 使用 medium 策略
./context-compressor-v5.sh --strategy medium abc123

# 预览压缩效果
./context-compressor-v5.sh --dry-run abc123

# 自动扫描并压缩
./context-compressor-v5.sh --auto-scan
```

#### 返回值

- `0`: 成功
- `1`: 失败（参数错误、文件不存在等）
- `2`: 警告（压缩未应用、无变化等）

#### 输出示例

```
📊 会话分析: 155 行, 546270B, Token 使用率 68%
🎯 选择策略: light
✅ 已应用压缩
📊 693952B → 581713B | 节省 17%
```

---

## 🧠 消息重要性评估 API

### `message-importance-engine.sh`

评估消息重要性分数。

#### 用法

```bash
source ./message-importance-engine.sh
calculate_importance <message>
```

#### 函数

##### `calculate_importance(message)`

计算单条消息的重要性分数。

**参数**:
- `message` (string): 消息文本

**返回**:
- `0-100`: 重要性分数

**示例**:

```bash
source ./message-importance-engine.sh

score=$(calculate_importance "这是重要的决策记录")
echo "重要性分数: $score"
# 输出: 重要性分数: 85
```

##### `classify_message(message)`

分类消息类型。

**参数**:
- `message` (string): 消息文本

**返回**:
- `string`: 消息类型（decision/error/config 等）

**示例**:

```bash
type=$(classify_message "修复了配置错误")
echo "消息类型: $type"
# 输出: 消息类型: error
```

---

## 🎓 自适应学习 API

### `adaptive-learning-engine.sh`

管理学习数据和参数。

#### 用法

```bash
./adaptive-learning-engine.sh <command> [arguments]
```

#### 命令

| 命令 | 参数 | 说明 |
|------|------|------|
| `init` | - | 初始化学习系统 |
| `record` | `<type> [value]` | 记录用户行为 |
| `stats` | `<session> <strategy> <saved>` | 记录压缩统计 |
| `adjust` | - | 自动调整权重 |
| `recommend` | `<usage>` | 推荐最佳策略 |
| `feedback` | `<session> <type> [details]` | 学习用户反馈 |
| `report` | - | 生成学习报告 |
| `weights` | - | 获取当前权重 |

#### 示例

```bash
# 初始化
./adaptive-learning-engine.sh init

# 记录行为
./adaptive-learning-engine.sh record decision 1

# 记录压缩统计
./adaptive-learning-engine.sh stats session123 medium 25

# 推荐策略
./adaptive-learning-engine.sh recommend 80
# 输出: light

# 生成报告
./adaptive-learning-engine.sh report
```

---

## 🔮 预测性压缩 API

### `predictive-compressor.sh`

预测 Token 需求并提前压缩。

#### 用法

```bash
./predictive-compressor.sh
```

#### 行为

1. 扫描所有会话
2. 预测 Token 增长速度
3. 计算达到阈值的时间
4. 提前执行压缩（如果需要）

#### 输出示例

```
[16:30:00] 🔮 预测性压缩分析...
[16:30:01] ⚠️  会话 abc123 预计 25 分钟后需要压缩
[16:30:02] 🚀 执行预测性压缩...
[16:30:05] ✅ 已应用压缩
[16:30:06] ✅ 预测分析完成
```

---

## 💰 成本优化 API

### `cost-optimizer.sh`

分析 API 调用成本并提供优化建议。

#### 用法

```bash
./cost-optimizer.sh
```

#### 功能

1. 分析 API 调用频率
2. 计算平均节省率
3. 推荐最经济的策略
4. 清理过期缓存
5. 生成成本报告

#### 输出示例

```
[2026-03-08 16:00:00] 💰 成本优化分析开始...
[2026-03-08 16:00:01] 📊 API调用分析...
[2026-03-08 16:00:01]   总压缩次数: 25
[2026-03-08 16:00:01]   平均节省率: 18%
[2026-03-08 16:00:02] 🧠 学习数据分析...
[2026-03-08 16:00:02]   策略使用: light=15, medium=8, heavy=2
[2026-03-08 16:00:02]   💡 推荐: light 策略最经济
[2026-03-08 16:00:03] ✅ 成本优化分析完成
```

---

## ⏰ 智能学习调度 API

### `smart-learning-scheduler.sh`

定期执行学习任务。

#### 用法

```bash
./smart-learning-scheduler.sh
```

#### 功能

1. 自动调整权重
2. 分析时间模式
3. 检查学习效果
4. 生成优化建议

---

## 🔄 返回值约定

| 代码 | 含义 |
|------|------|
| `0` | 成功 |
| `1` | 一般错误 |
| `2` | 警告（可继续） |
| `3` | 配置错误 |
| `4` | 网络错误 |
| `5` | 权限错误 |

---

## 📝 日志格式

所有脚本使用统一日志格式：

```
[时间戳] [级别] 消息
```

级别：
- `INFO`: 一般信息
- `WARN`: 警告
- `ERROR`: 错误
- `DEBUG`: 调试信息

---

## 🔌 集成示例

### Python 集成

```python
import subprocess

def compress_session(session_id):
    result = subprocess.run(
        ['./context-compressor-v5.sh', session_id],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("压缩成功:", result.stdout)
    else:
        print("压缩失败:", result.stderr)
```

### Node.js 集成

```javascript
const { exec } = require('child_process');

function compressSession(sessionId) {
  exec(`./context-compressor-v5.sh ${sessionId}`, (error, stdout, stderr) => {
    if (error) {
      console.error('压缩失败:', error);
      return;
    }
    console.log('压缩成功:', stdout);
  });
}
```

---

## 🚫 错误处理

### 常见错误

#### 1. 会话文件不存在

```bash
❌ 错误: 会话文件不存在: abc123.jsonl
```

**解决**: 检查会话 ID 是否正确

#### 2. API Key 未配置

```bash
❌ 错误: 未找到 API Key
```

**解决**: 设置 `GLM_API_KEY` 环境变量

#### 3. 权限不足

```bash
❌ 错误: 权限被拒绝
```

**解决**: `chmod +x *.sh`

---

详细错误代码请参考源代码。
