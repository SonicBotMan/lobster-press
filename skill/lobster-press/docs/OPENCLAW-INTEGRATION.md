# OpenClaw 集成指南

本文档说明如何将 LobsterPress 与 OpenClaw 的内置 Compaction 功能协调工作，避免重复压缩。

---

## 背景

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
