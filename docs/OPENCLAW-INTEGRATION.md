# OpenClaw 集成指南

本文档说明如何将 LobsterPress 与 OpenClaw 集成，包括：
1. **ContextEngine 集成**（v3.3.0+）：自动上下文监测与压缩
2. **Compaction 协调**：与 OpenClaw 内置 Compaction 功能协调工作

---

## 🚀 ContextEngine 集成（v3.3.0+）⭐

### 概述

LobsterPress v3.3.0+ 实现了 OpenClaw 的 **ContextEngine 接口**，可以：
- ✅ 自动监测上下文使用率（每次 turn 后）
- ✅ 智能触发压缩（超过阈值时）
- ✅ 使用真实 DAG 压缩（语义理解）
- ✅ 异步执行（不阻塞用户）

### 架构

```
┌─────────────────────────────────────────────────────────────┐
│                  OpenClaw Context Pipeline                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Message → AI Response → afterTurn() Hook             │
│                                    │                        │
│                                    ↓                        │
│                          LobsterPress ContextEngine        │
│                                    │                        │
│                      ┌─────────────┴─────────────┐        │
│                      │                           │        │
│                Usage < 75%                 Usage >= 75%   │
│                      │                           │        │
│                      ↓                           ↓        │
│                   无操作                    compact()      │
│                                                │           │
│                                                ↓           │
│                                      DAGCompressor         │
│                                      (真实 DAG 压缩)        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 核心方法

#### 1. `afterTurn(messages, sessionFile)`

**功能**：每次 turn 后自动调用，检查上下文使用率

**返回值**：

```typescript
{
  shouldCompact: boolean,  // 是否应该压缩
  currentTokens: number,   // 当前 token 数
  tokenBudget: number,     // token 预算
  usageRatio: number       // 使用率（0-1）
}
```

**触发逻辑**：
- 默认阈值：75%（可配置）
- 当 `usageRatio >= 0.75` 时，`shouldCompact = true`
- OpenClaw 会自动调用 `compact()` 方法

#### 2. `compact(currentTokenCount, tokenBudget, force)`

**功能**：执行实际的压缩操作

**参数**：
- `currentTokenCount`: 当前 token 数
- `tokenBudget`: token 预算
- `force`: 是否强制压缩（可选，默认 false）

**返回值**：

```typescript
{
  compressed: boolean,      // 是否执行了压缩
  tokensBefore: number,     // 压缩前 token 数
  tokensAfter: number,      // 压缩后 token 数
  force: boolean           // 是否强制压缩
}
```

**实现细节**：
- 调用 `lobster_compress` MCP 工具
- 使用真实的 `DAGCompressor.incremental_compact()`
- 异步执行，不阻塞用户 turn
- 错误处理和重试机制（v3.3.1+）

### 配置

在 `~/.openclaw/openclaw.json` 中配置：

```json
{
  "agents": {
    "defaults": {
      "plugins": {
        "slots": {
          "contextEngine": "lobster-press"
        }
      },
      "compaction": {
        "mode": "safeguard",
        "reserveTokens": 8000
      }
    }
  },
  "plugins": {
    "lobster-press": {
      "path": "@sonicbotman/lobster-press",
      "config": {
        "contextThreshold": 0.75,
        "strategy": "medium",
        "tokenBudget": 128000
      }
    }
  }
}
```

**配置说明**：
- `slots.contextEngine`: 指定使用 LobsterPress 作为 ContextEngine
- `contextThreshold`: 压缩阈值（默认 0.75）
- `strategy`: 压缩策略（light/medium/aggressive）
- `tokenBudget`: token 预算（默认 128000）

### 优势对比

| 特性 | OpenClaw 内置 Compaction | LobsterPress ContextEngine |
|------|-------------------------|---------------------------|
| 触发方式 | 手动 `/compact` 或达到限制 | 自动监测 + 智能触发 |
| 压缩算法 | 基于规则 | DAG 语义压缩 |
| 理解能力 | 有限（关键词） | 深度语义理解 |
| 可配置性 | 中等 | 高（策略、阈值、权重） |
| 重试机制 | 无 | ✅ 3 次重试 + 指数退避 |
| 错误处理 | 基础 | ✅ 详细错误信息 |
| 性能影响 | 低 | 中（异步执行） |

### 使用示例

#### 1. 自动压缩（推荐）

配置后，LobsterPress 会自动监测和压缩：

```bash
# 1. 安装 LobsterPress
npm install -g @sonicbotman/lobster-press

# 2. 配置 OpenClaw（如上）

# 3. 重启 OpenClaw
openclaw restart

# 4. 正常使用，LobsterPress 自动工作
```

#### 2. 手动触发

也可以手动调用 `lobster_compress` 工具：

```json
{
  "name": "lobster_compress",
  "arguments": {
    "conversation_id": "current-session",
    "current_tokens": 100000,
    "token_budget": 128000,
    "force": false
  }
}
```

#### 3. 强制压缩

即使未达到阈值，也可以强制压缩：

```json
{
  "name": "lobster_compress",
  "arguments": {
    "conversation_id": "current-session",
    "current_tokens": 50000,
    "token_budget": 128000,
    "force": true
  }
}
```

### 监控和日志

LobsterPress 会记录压缩历史到数据库：

```bash
# 查看压缩统计
sqlite3 ~/.openclaw/lobster.db "
SELECT
  conversation_id,
  COUNT(*) as compression_count,
  SUM(tokens_saved) as total_saved
FROM compression_history
GROUP BY conversation_id
ORDER BY total_saved DESC
LIMIT 10;
"
```

### 故障排查

#### 问题 1：压缩未触发

**检查**：
1. 确认 `contextEngine` 插件已配置
2. 检查 `contextThreshold` 设置
3. 查看 OpenClaw 日志

```bash
openclaw logs | grep -i lobster
```

#### 问题 2：压缩失败

**检查**：
1. 确认数据库路径正确
2. 检查磁盘空间
3. 查看错误信息

```bash
# 查看最近的错误
sqlite3 ~/.openclaw/lobster.db "
SELECT * FROM compression_history
WHERE status = 'error'
ORDER BY created_at DESC
LIMIT 5;
"
```

#### 问题 3：性能影响

**优化**：
1. 调高 `contextThreshold`（例如 0.8）
2. 使用 `light` 策略
3. 禁用自动压缩，手动触发

---

## 🔄 Compaction 协调（遗留）

OpenClaw 从 2026.3 版本开始内置了 **Compaction** 功能：
- 自动在接近上下文窗口限制时压缩会话
- 支持手动 `/compact` 命令
- 支持 safeguard 模式保护重要上下文

LobsterPress 提供了更精细的控制：
- 预测性压缩
- 智能重要性评估
- 自适应学习
- 压缩历史追踪

两者可以配合使用，互不冲突。

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                    分层压缩策略                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  0% ─────────── 60% ───────── 80% ───────── 90% ───── 95% ─── 100% │
│  │               │             │            │          │          │
│  │   🟢 安全     │  🟡 注意    │  🟠 警告   │  🔴 危险  │  ⚫ 紧急 │
│  │               │             │            │          │          │
│  │   无操作      │ 龙虾饼报告  │ 龙虾饼压缩 │ OpenClaw │  强制    │
│  │               │             │   (可选)   │  压缩    │  /reset  │
│  │               │             │            │          │          │
│  └───────────────┴─────────────┴────────────┴──────────┴──────────┘
│                                                                     │
│  龙虾饼角色：预警系统 + 智能分析 + 按需压缩                          │
│  OpenClaw角色：自动兜底 + safeguard 保护                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 安装协调器

```bash
# 1. 复制协调器脚本
cp scripts/lobster-openclaw-coordinator.sh ~/bin/
chmod +x ~/bin/lobster-openclaw-coordinator.sh

# 2. 测试
~/bin/lobster-openclaw-coordinator.sh scan
```

---

## 配置优化

### 1. LobsterPress 配置

修改 `~/.config/lobster-press/config.json`：

```json
{
  "threshold": {
    "report": 60,
    "light": 80,
    "medium": 90,
    "heavy": 95
  },
  "integration": {
    "openclaw_compaction": {
      "enabled": true,
      "skip_if_recent": 3600,
      "coordinate_threshold": 90
    }
  }
}
```

### 2. Systemd 服务优化

修改 `lobster-compress.service`：

```ini
[Service]
Environment=AUTO_APPLY=false
Environment=REPORT_THRESHOLD=60
```

修改 `lobster-compress.timer`（降低频率）：

```ini
[Timer]
OnCalendar=*:0/30
```

### 3. OpenClaw Compaction 配置

在 `~/.openclaw/openclaw.json` 中：

```json
{
  "agents": {
    "defaults": {
      "compaction": {
        "mode": "safeguard",
        "reserveTokens": 8000,
        "keepRecentTokens": 6000,
        "maxHistoryShare": 0.5,
        "recentTurnsPreserve": 5,
        "memoryFlush": {
          "enabled": true
        }
      }
    }
  }
}
```

---

## 使用方式

### 扫描报告

```bash
# 查看所有会话的压缩状态
~/bin/lobster-openclaw-coordinator.sh scan
```

输出示例：
```
🔍 龙虾饼 + OpenClaw 协调报告
================================

📁 abc123-def456
   ⚠️ Token 使用率 82%，建议：龙虾饼轻度压缩（light）

📁 xyz789-uvw012
   🔶 Token 使用率 91%，建议：龙虾饼中度压缩 或 等待 OpenClaw

================================
📊 统计:
   总会话数: 69
   🟢 安全 (< 60%): 45
   🔴 需关注 (> 80%): 2
   ✅ 近期已压缩: 3
```

### 检查单个会话

```bash
~/bin/lobster-openclaw-coordinator.sh recommend <session_file> <usage>
```

### JSON 格式（供程序调用）

```bash
~/bin/lobster-openclaw-coordinator.sh json
```

---

## 协调逻辑

协调器会检测：

1. **OpenClaw 压缩标记**：检查会话文件中是否有 `compaction`、`🧹` 等标记
2. **时间窗口**：如果在 `SKIP_WINDOW_SECONDS`（默认 1 小时）内压缩过，跳过
3. **建议动作**：
   - `skip` - 跳过（近期已压缩）
   - `none` - 无需处理
   - `light` - 轻度压缩
   - `medium` - 中度压缩
   - `defer` - 让 OpenClaw 处理

---

## 最佳实践

### 1. 分工明确

| 场景 | 处理方式 |
|------|----------|
| Token < 60% | 无需处理 |
| Token 60-80% | 龙虾饼报告 |
| Token 80-90% | 龙虾饼轻度压缩（可选） |
| Token 90-95% | 等待 OpenClaw 或龙虾饼压缩 |
| Token > 95% | OpenClaw 自动压缩 或 `/reset` |

### 2. 避免重复压缩

- 龙虾饼检测到 OpenClaw 在 1 小时内压缩过 → 跳过
- OpenClaw 的 safeguard 模式会保护最近对话

### 3. 监控优先

推荐配置：
- 龙虾饼：监控 + 报告（AUTO_APPLY=false）
- OpenClaw：自动压缩兜底

---

## 故障排除

### Q: 两个系统同时压缩了怎么办？

A: 检查：
1. 协调器是否正常运行
2. `SKIP_WINDOW_SECONDS` 配置是否合理
3. OpenClaw compaction 标记是否被正确识别

### Q: 如何完全禁用 LobsterPress？

```bash
systemctl --user stop lobster-compress.timer
systemctl --user disable lobster-compress.timer
```

### Q: 如何只使用 LobsterPress？

在 OpenClaw 配置中禁用自动压缩：

```json
{
  "compaction": {
    "mode": "default",
    "reserveTokens": 0
  }
}
```

---

## 更新日志

- **v1.0.0** (2026-03-09)
  - 初始版本
  - OpenClaw compaction 检测
  - 协调报告功能
  - JSON API 支持
