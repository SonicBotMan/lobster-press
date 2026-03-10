#!/bin/bash
# 预测性压缩引擎 - 根据使用模式提前压缩
# 建议：每30分钟执行一次

set -e

SESSIONS_DIR="$HOME/.openclaw/agents/main/sessions"
COMPRESSOR="$HOME/bin/context-compressor-v5.sh"
METRICS_FILE="/tmp/predictive-metrics.json"

# 初始化指标
[ ! -f "$METRICS_FILE" ] && echo '{"predictions": [], "accuracy": 0}' > "$METRICS_FILE"

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

# 预测 Token 增长速度
predict_growth() {
    local session_file=$1
    
    if [ ! -f "$session_file" ]; then
        echo "0"
        return
    fi
    
    # 获取文件大小
    local current_size=$(wc -c < "$session_file")
    
    # 检查5分钟前的大小
    local size_file="/tmp/size-$(basename $session_file).txt"
    local old_size=0
    
    if [ -f "$size_file" ]; then
        old_size=$(cat "$size_file")
    fi
    
    # 保存当前大小
    echo $current_size > "$size_file"
    
    # 计算增长速度（字节/分钟）
    local growth_rate=$((current_size - old_size))
    echo $growth_rate
}

# 预测何时需要压缩
predict_compression_time() {
    local session_file=$1
    local threshold=$2  # 例如 70%
    
    local current_size=$(wc -c < "$session_file" 2>/dev/null || echo 0)
    local growth_rate=$(predict_growth "$session_file")
    
    if [ $growth_rate -le 0 ]; then
        echo "999"  # 无增长，不需要预测
        return
    fi
    
    # 基于实际 token 窗口 (200k tokens ≈ 800k bytes)
    local max_size=${MAX_CONTEXT_SIZE:-800000}
    local current_percent=$((current_size * 100 / max_size))
    local remaining=$((max_size - current_size))
    
    # 预计达到阈值的时间（分钟）
    local minutes_to_threshold=$((remaining / growth_rate))
    
    echo $minutes_to_threshold
}

# 主逻辑
log "🔮 预测性压缩分析..."

for session_file in "$SESSIONS_DIR"/*.jsonl; do
    if [[ "$session_file" == *.backup.* ]] || [[ "$session_file" == *.reset.* ]]; then
        continue
    fi
    
    [ ! -f "$session_file" ] && continue
    
    session_id=$(basename "$session_file" .jsonl)
    
    # 预测压缩时间
    minutes=$(predict_compression_time "$session_file" 70)
    
    if [ $minutes -lt 30 ]; then
        log "⚠️  会话 $session_id 预计 ${minutes} 分钟后需要压缩"
        
        # 提前压缩
        if [ $minutes -lt 5 ]; then
            log "🚀 执行预测性压缩..."
            # 移除 grep 过滤，保留完整输出以检测错误
            if AUTO_APPLY=true timeout 60 $COMPRESSOR "$session_id" 2>&1; then
                log "✅ 预测性压缩成功"
            else
                log "❌ 预测性压缩失败，退出码: $?"
            fi
        fi
    fi
done

log "✅ 预测分析完成"
