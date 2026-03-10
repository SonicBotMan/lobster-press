#!/bin/bash
# 智能学习调度器 - 定期优化学习参数
# 建议：每小时执行一次

set -e

LEARNING_DIR="$HOME/.openclaw/workspace/memory/adaptive-learning"
LEARNING_ENGINE="$HOME/adaptive-learning-engine.sh"

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

# 1. 自动调整权重
log "📊 自动调整权重..."
$LEARNING_ENGINE adjust 2>&1 | grep -E "✅|调整" || log "  无需调整"

# 2. 分析时间模式
log "🕐 分析时间模式..."
current_hour=$(date +%H)
if [ $current_hour -ge 9 ] && [ $current_hour -le 18 ]; then
    # 工作时间 - 偏好决策和配置
    $LEARNING_ENGINE record decision 1 2>/dev/null || true
    $LEARNING_ENGINE record config 1 2>/dev/null || true
    log "  工作时间模式：提升决策权重"
else
    # 非工作时间 - 偏好聊天
    $LEARNING_ENGINE record chitchat 1 2>/dev/null || true
    log "  非工作时间模式：降低严格度"
fi

# 3. 检查学习效果
log "📈 学习效果检查..."
if [ -f "$LEARNING_DIR/compression-stats.json" ]; then
    total=$(cat "$LEARNING_DIR/compression-stats.json" | jq '.total_compressions')
    if [ $total -gt 10 ]; then
        log "  已积累 $total 次压缩数据，权重可信度高"
    else
        log "  仅 $total 次压缩数据，继续积累中..."
    fi
fi

# 4. 生成优化建议
log "💡 优化建议..."
recommended=$($LEARNING_ENGINE recommend 80 2>&1 | tail -1)
log "  当前推荐策略: $recommended"

log "✅ 智能学习调度完成"
