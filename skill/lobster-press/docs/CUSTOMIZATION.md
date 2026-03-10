# 自定义指南

## 🎨 自定义权重

### 修改基础权重

编辑 `~/bin/adaptive-learning-engine.sh`：

```bash
base_weights = {
  "decision": 100,    # 决策记录
  "error": 90,        # 错误处理
  "config": 85,       # 配置信息
  "preference": 80,   # 偏好设置
  "question": 70,     # 问题回答
  "fact": 60,         # 事实陈述
  "action": 50,       # 执行动作
  "feedback": 45,     # 用户反馈
  "context": 30,      # 上下文信息
  "chitchat": 10      # 闲聊内容
}
```

### 根据场景调整

#### 场景 1: 技术支持

```bash
# 更关注错误和配置
base_weights = {
  "error": 100,
  "config": 95,
  "decision": 90,
  ...
}
```

#### 场景 2: 项目管理

```bash
# 更关注决策和任务
base_weights = {
  "decision": 100,
  "action": 90,
  "feedback": 85,
  ...
}
```

#### 场景 3: 学习辅导

```bash
# 更关注问题和事实
base_weights = {
  "question": 100,
  "fact": 95,
  "feedback": 90,
  ...
}
```

---

## ⚙️ 自定义压缩策略

### 修改策略参数

编辑 `~/bin/context-compressor-v5.sh`：

```bash
# Light 策略
STRATEGY_LIGHT_MAX_MESSAGES=150      # 保留消息数
STRATEGY_LIGHT_SUMMARY_RATIO=0.3     # 摘要比例

# Medium 策略
STRATEGY_MEDIUM_MAX_MESSAGES=100
STRATEGY_MEDIUM_SUMMARY_RATIO=0.5

# Heavy 策略
STRATEGY_HEAVY_MAX_MESSAGES=70
STRATEGY_HEAVY_SUMMARY_RATIO=0.7
```

### 自定义策略

添加新策略：

```bash
# Ultra-Heavy 策略
STRATEGY_ULTRAHEAVY_MAX_MESSAGES=50
STRATEGY_ULTRAHEAVY_SUMMARY_RATIO=0.8

case $strategy in
  ultraheavy) max_messages=50 ;;
  ...
esac
```

---

## 🔧 自定义压缩阈值

### 修改触发阈值

编辑 `~/bin/context-compressor-v5.sh`：

```bash
# Token 使用率阈值
THRESHOLD_LIGHT=70    # Light 策略触发点
THRESHOLD_MEDIUM=85   # Medium 策略触发点
THRESHOLD_HEAVY=95    # Heavy 策略触发点
```

### 保守配置

```bash
# 更早触发压缩
THRESHOLD_LIGHT=60
THRESHOLD_MEDIUM=75
THRESHOLD_HEAVY=90
```

### 激进配置

```bash
# 更晚触发压缩
THRESHOLD_LIGHT=80
THRESHOLD_MEDIUM=90
THRESHOLD_HEAVY=98
```

---

## 🧠 自定义学习算法

### 修改学习率

编辑 `~/bin/adaptive-learning-engine.sh`：

```bash
# 学习率（0-1）
LEARNING_RATE=0.1

# 权重调整因子
BOOST_FACTOR=20
PENALTY_FACTOR=5
```

### 调整学习频率

编辑 systemd 定时器：

```bash
# ~/.config/systemd/user/lobster-learning.timer

[Timer]
OnCalendar=*:0/15    # 每15分钟
# OnCalendar=hourly  # 每小时
# OnCalendar=daily   # 每天
```

---

## 🎯 自定义消息分类

### 添加新的消息类型

编辑 `~/bin/message-importance-engine.sh`：

```bash
# 添加新的关键词模式
PATTERNS[new_type]="new_keyword|another_keyword"

# 设置权重
base_weights["new_type"]=75
```

### 示例：添加"安全"类型

```bash
# 安全相关消息
PATTERNS[security]="安全|security|漏洞|vulnerability|攻击|attack"
base_weights["security"]=95
```

---

## 📊 自定义报告格式

### 修改学习报告

编辑 `~/bin/adaptive-learning-engine.sh`：

```bash
generate_learning_report() {
    # 自定义报告格式
    echo "📊 自定义学习报告"
    echo "=================="
    echo ""
    
    # 添加更多统计
    echo "### 最近 7 天统计:"
    # ...
}
```

### 导出为 JSON

```bash
# 添加 JSON 导出功能
generate_json_report() {
    cat <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "user_behavior": $(cat "$USER_BEHAVIOR_FILE"),
  "compression_stats": $(cat "$STATS_FILE"),
  "weights": $(cat "$WEIGHTS_FILE")
}
EOF
}
```

---

## 🔌 集成外部系统

### Webhook 通知

添加压缩完成通知：

```bash
# 在 context-compressor-v5.sh 中添加
send_notification() {
    local message=$1
    curl -X POST https://your-webhook-url \
         -H "Content-Type: application/json" \
         -d "{\"text\": \"$message\"}"
}

# 在压缩成功后调用
send_notification "✅ 压缩完成: $session_id, 节省 $saved_percent%"
```

### 集成到监控系统

```bash
# 导出 Prometheus 指标
export_metrics() {
    cat <<EOF > /var/lib/node_exporter/textfile_collector/lobster_press.prom
lobster_press_compressions_total{strategy="light"} $light_count
lobster_press_compressions_total{strategy="medium"} $medium_count
lobster_press_compressions_total{strategy="heavy"} $heavy_count
lobster_press_tokens_saved_percent $avg_saved
EOF
}
```

---

## 🎨 自定义 UI 输出

### 修改颜色主题

编辑脚本中的颜色定义：

```bash
# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 使用
echo -e "${GREEN}✅ 成功${NC}"
echo -e "${YELLOW}⚠️  警告${NC}"
echo -e "${RED}❌ 错误${NC}"
```

### 简洁模式

添加简洁输出选项：

```bash
QUIET_MODE=false

if [ "$1" = "--quiet" ]; then
    QUIET_MODE=true
fi

log() {
    if [ "$QUIET_MODE" = false ]; then
        echo "$1"
    fi
}
```

---

## 🔒 安全配置

### API Key 加密

```bash
# 加密 API Key
echo "your_api_key" | openssl enc -aes-256-cbc -salt -out ~/.config/lobster-press/api_key.enc

# 解密使用
API_KEY=$(openssl enc -aes-256-cbc -d -in ~/.config/lobster-press/api_key.enc)
```

### 限制访问权限

```bash
# 设置文件权限
chmod 700 ~/.config/lobster-press
chmod 600 ~/.config/lobster-press/config.json
chmod 700 ~/bin/*.sh
```

---

## 📝 自定义日志

### 日志级别

```bash
LOG_LEVEL="INFO"  # DEBUG, INFO, WARN, ERROR

log_debug() {
    [ "$LOG_LEVEL" = "DEBUG" ] && echo "[DEBUG] $1"
}

log_info() {
    [ "$LOG_LEVEL" != "ERROR" ] && [ "$LOG_LEVEL" != "WARN" ] && echo "[INFO] $1"
}
```

### 日志轮转

```bash
# 添加到 logrotate
sudo tee /etc/logrotate.d/lobster-press <<EOF
/var/log/lobster-press/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

---

## 🚀 高级技巧

### 批量优化

```bash
# 批量压缩所有会话
for session in ~/.openclaw/agents/main/sessions/*.jsonl; do
    session_id=$(basename "$session" .jsonl)
    ./context-compressor-v5.sh --auto "$session_id"
done
```

### 性能调优

```bash
# 并行处理
find ~/.openclaw/agents/main/sessions -name "*.jsonl" | \
    parallel -j 4 ./context-compressor-v5.sh {.}
```

### 数据分析

```bash
# 分析压缩效果
grep "节省" ~/.lobster-press/compression-history.md | \
    awk '{print $NF}' | \
    sed 's/%//' | \
    awk '{sum+=$1; count++} END {print "平均节省:", sum/count "%"}'
```

---

更多自定义选项请参考源代码注释。
