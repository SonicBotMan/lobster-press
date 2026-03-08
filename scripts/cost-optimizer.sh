#!/bin/bash
# 成本优化器 - 减少API调用，优化Token使用
# 建议：每天执行一次

set -e

METRICS_FILE="/tmp/compress-metrics.json"
LEARNING_DIR="$HOME/.openclaw/workspace/memory/adaptive-learning"
OPTIMIZATION_LOG="$HOME/.openclaw/workspace/memory/cost-optimization.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$OPTIMIZATION_LOG"
}

log "💰 成本优化分析开始..."

# 1. 分析API调用频率
log "📊 API调用分析..."
if [ -f "$METRICS_FILE" ]; then
    total_calls=$(cat "$METRICS_FILE" | jq '.sessions | length' 2>/dev/null || echo 0)
    log "  总压缩次数: $total_calls"
    
    # 计算平均节省率
    if [ $total_calls -gt 0 ]; then
        avg_saved=$(cat "$METRICS_FILE" | jq '[.sessions[].saved_percent // 0] | add / length' 2>/dev/null || echo 0)
        log "  平均节省率: ${avg_saved}%"
    fi
fi

# 2. 分析学习数据
log "🧠 学习数据分析..."
if [ -f "$LEARNING_DIR/compression-stats.json" ]; then
    light_count=$(cat "$LEARNING_DIR/compression-stats.json" | jq '.by_strategy.light.count // 0')
    medium_count=$(cat "$LEARNING_DIR/compression-stats.json" | jq '.by_strategy.medium.count // 0')
    heavy_count=$(cat "$LEARNING_DIR/compression-stats.json" | jq '.by_strategy.heavy.count // 0')
    
    log "  策略使用: light=$light_count, medium=$medium_count, heavy=$heavy_count"
    
    # 推荐最经济的策略
    if [ $light_count -gt $medium_count ] && [ $light_count -gt $heavy_count ]; then
        log "  💡 推荐: light 策略最经济"
    elif [ $medium_count -gt 0 ]; then
        log "  💡 推荐: medium 策略平衡成本与效果"
    fi
fi

# 3. Token 优化建议
log "🎯 Token优化建议..."
log "  1. 使用缓存减少重复调用"
log "  2. 批量处理会话"
log "  3. 设置更高的压缩阈值（85% → 90%）"

# 4. 缓存清理
log "🧹 缓存维护..."
cache_size=$(du -sh /tmp/compress-cache 2>/dev/null | awk '{print $1}')
if [ -n "$cache_size" ]; then
    log "  缓存大小: $cache_size"
    # 清理7天前的缓存
    find /tmp/compress-cache -type f -mtime +7 -delete 2>/dev/null && log "  ✅ 已清理过期缓存"
fi

# 5. 成本预测
log "💵 成本预测..."
current_day=$(date +%d)
if [ $current_day -eq 1 ]; then
    # 每月1日重置统计
    log "  📅 新月开始，重置成本统计"
    echo '{"monthly_calls": 0, "monthly_tokens_saved": 0}' > /tmp/monthly-cost.json
fi

log "✅ 成本优化分析完成"
log ""
