#!/bin/bash
# 自适应学习引擎 v1
# 根据用户行为和反馈自动调整压缩策略

set -e

LEARNING_DIR="$HOME/.openclaw/workspace/memory/adaptive-learning"
USER_BEHAVIOR_FILE="$LEARNING_DIR/user-behavior.json"
FEEDBACK_FILE="$LEARNING_DIR/feedback.json"
WEIGHTS_FILE="$LEARNING_DIR/adaptive-weights.json"
STATS_FILE="$LEARNING_DIR/compression-stats.json"

# 创建目录
mkdir -p "$LEARNING_DIR" 2>/dev/null || true

# 初始化文件
init_learning() {
    if [ ! -f "$USER_BEHAVIOR_FILE" ]; then
        cat > "$USER_BEHAVIOR_FILE" <<'EOF'
{
  "message_type_focus": {
    "decision": 0,
    "error": 0,
    "config": 0,
    "preference": 0,
    "question": 0,
    "fact": 0,
    "action": 0,
    "feedback": 0,
    "context": 0,
    "chitchat": 0
  },
  "strategy_usage": {
    "light": 0,
    "medium": 0,
    "heavy": 0
  },
  "time_patterns": {},
  "last_update": ""
}
EOF
    fi
    
    if [ ! -f "$WEIGHTS_FILE" ]; then
        cat > "$WEIGHTS_FILE" <<'EOF'
{
  "base_weights": {
    "decision": 100,
    "error": 90,
    "config": 85,
    "preference": 80,
    "question": 70,
    "fact": 60,
    "action": 50,
    "feedback": 45,
    "context": 30,
    "chitchat": 10
  },
  "adaptive_adjustments": {},
  "user_boost": {},
  "penalty": {},
  "last_adjustment": ""
}
EOF
    fi
    
    if [ ! -f "$STATS_FILE" ]; then
        cat > "$STATS_FILE" <<'EOF'
{
  "total_compressions": 0,
  "by_strategy": {
    "light": {"count": 0, "avg_saved": 0},
    "medium": {"count": 0, "avg_saved": 0},
    "heavy": {"count": 0, "avg_saved": 0}
  },
  "by_session": {},
  "quality_scores": [],
  "best_practices": []
}
EOF
    fi
}

# 记录用户行为
record_user_behavior() {
    local behavior_type=$1
    local value=${2:-1}
    local timestamp=$(date -Iseconds)
    
    init_learning
    
    # 读取当前数据
    local data=$(cat "$USER_BEHAVIOR_FILE")
    
    # 更新对应类型
    local current=$(echo "$data" | jq ".message_type_focus.$behavior_type // 0")
    current=$((current + value))
    
    data=$(echo "$data" | jq ".message_type_focus.$behavior_type = $current")
    data=$(echo "$data" | jq ".last_update = \"$timestamp\"")
    
    # 保存
    echo "$data" > "$USER_BEHAVIOR_FILE"
}

# 记录压缩统计
record_compression_stats() {
    local session_id=$1
    local strategy=$2
    local saved_percent=$3
    
    init_learning
    
    local stats=$(cat "$STATS_FILE")
    
    # 更新总数
    local total=$(echo "$stats" | jq '.total_compressions')
    total=$((total + 1))
    stats=$(echo "$stats" | jq ".total_compressions = $total")
    
    # 更新策略统计
    local count=$(echo "$stats" | jq ".by_strategy.$strategy.count // 0")
    local avg=$(echo "$stats" | jq ".by_strategy.$strategy.avg_saved // 0")
    
    count=$((count + 1))
    avg=$(( (avg * (count - 1) + saved_percent) / count ))
    
    stats=$(echo "$stats" | jq ".by_strategy.$strategy.count = $count")
    stats=$(echo "$stats" | jq ".by_strategy.$strategy.avg_saved = $avg")
    
    # 更新会话统计
    local session_count=$(echo "$stats" | jq ".by_session.\"$session_id\" // 0")
    session_count=$((session_count + 1))
    stats=$(echo "$stats" | jq ".by_session.\"$session_id\" = $session_count")
    
    echo "$stats" > "$STATS_FILE"
}

# 计算自适应权重
get_adaptive_weights() {
    init_learning
    
    local base_weights=$(cat "$WEIGHTS_FILE")
    local user_behavior=$(cat "$USER_BEHAVIOR_FILE")
    
    # 获取用户最关注的类型（前3个）
    local top_types=$(echo "$user_behavior" | \
        jq -r '.message_type_focus | to_entries | sort_by(.value) | reverse | .[0:3] | .[].key')
    
    # 为这些类型增加权重
    local boost_factor=20
    for type in $top_types; do
        local current=$(echo "$base_weights" | jq ".base_weights.$type // 50")
        local boosted=$((current + boost_factor))
        base_weights=$(echo "$base_weights" | jq ".user_boost.$type = $boosted")
    done
    
    # 输出调整后的权重
    echo "$base_weights" | jq '.base_weights * .user_boost // .base_weights'
}

# 推荐最佳策略
recommend_strategy() {
    local token_usage=$1
    
    init_learning
    
    local stats=$(cat "$STATS_FILE")
    
    # 分析历史数据
    local light_avg=$(echo "$stats" | jq '.by_strategy.light.avg_saved // 0')
    local medium_avg=$(echo "$stats" | jq '.by_strategy.medium.avg_saved // 0')
    local heavy_avg=$(echo "$stats" | jq '.by_strategy.heavy.avg_saved // 0')
    
    # 根据历史效果和当前使用率推荐
    if [ $token_usage -lt 70 ]; then
        echo "none"
    elif [ $token_usage -lt 85 ]; then
        # 如果 light 效果好，继续用；否则尝试 medium
        if [ $light_avg -gt 5 ]; then
            echo "light"
        else
            echo "medium"
        fi
    elif [ $token_usage -lt 95 ]; then
        # 如果 medium 效果好，继续用；否则升级到 heavy
        if [ $medium_avg -gt 10 ]; then
            echo "medium"
        else
            echo "heavy"
        fi
    else
        echo "heavy"
    fi
}

# 自动调整权重（每天执行一次）
auto_adjust_weights() {
    init_learning
    
    local timestamp=$(date -Iseconds)
    
    # 分析用户行为
    local user_behavior=$(cat "$USER_BEHAVIOR_FILE")
    local weights=$(cat "$WEIGHTS_FILE")
    
    # 获取最常关注的类型
    local top_focus=$(echo "$user_behavior" | \
        jq -r '.message_type_focus | to_entries | sort_by(.value) | reverse | .[0:3]')
    
    # 获取最常忽略的类型
    local bottom_focus=$(echo "$user_behavior" | \
        jq -r '.message_type_focus | to_entries | sort_by(.value) | .[0:3]')
    
    # 调整权重（提升常用类型，降低忽略类型）
    echo "$top_focus" | jq -r '.[].key' | while read type; do
        local current=$(echo "$weights" | jq ".base_weights.$type // 50")
        local adjusted=$((current + 5))
        [ $adjusted -gt 150 ] && adjusted=150  # 上限
        
        weights=$(echo "$weights" | jq ".adaptive_adjustments.$type = $adjusted")
    done
    
    echo "$bottom_focus" | jq -r '.[].key' | while read type; do
        local current=$(echo "$weights" | jq ".base_weights.$type // 50")
        local adjusted=$((current - 3))
        [ $adjusted -lt 0 ] && adjusted=0  # 下限
        
        weights=$(echo "$weights" | jq ".penalty.$type = $adjusted")
    done
    
    # 保存
    weights=$(echo "$weights" | jq ".last_adjustment = \"$timestamp\"")
    echo "$weights" > "$WEIGHTS_FILE"
    
    echo "✅ 权重已自动调整（$timestamp）"
}

# 学习用户反馈
learn_from_feedback() {
    local session_id=$1
    local feedback_type=$2  # good/bad
    local details=${3:-""}
    
    init_learning
    
    local timestamp=$(date -Iseconds)
    local feedback_record="{\"session\":\"$session_id\",\"type\":\"$feedback_type\",\"details\":\"$details\",\"timestamp\":\"$timestamp\"}"
    
    # 保存反馈
    if [ -f "$FEEDBACK_FILE" ]; then
        local feedback=$(cat "$FEEDBACK_FILE")
        feedback=$(echo "$feedback" | jq ". += [$feedback_record]")
        echo "$feedback" > "$FEEDBACK_FILE"
    else
        echo "[$feedback_record]" > "$FEEDBACK_FILE"
    fi
    
    # 根据反馈调整
    if [ "$feedback_type" = "good" ]; then
        # 增强当前策略
        record_user_behavior "strategy_success" 1
    else
        # 降低当前策略权重
        record_user_behavior "strategy_failure" 1
    fi
}

# 生成学习报告
generate_learning_report() {
    init_learning
    
    echo "📊 自适应学习报告"
    echo "=================="
    echo ""
    
    # 用户行为分析
    echo "### 用户关注的消息类型 TOP3:"
    cat "$USER_BEHAVIOR_FILE" | \
        jq -r '.message_type_focus | to_entries | sort_by(.value) | reverse | .[0:3] | .[] | "  - \(.key): \(.value) 次"'
    
    echo ""
    echo "### 策略使用统计:"
    cat "$STATS_FILE" | \
        jq -r '.by_strategy | to_entries[] | select(.value.count > 0) | "  - \(.key): \(.value.count) 次, 平均节省 \(.value.avg_saved)%"'
    
    echo ""
    echo "### 推荐策略:"
    local recommended=$(recommend_strategy 80)
    echo "  当前推荐: $recommended"
    
    echo ""
    echo "### 权重调整:"
    cat "$WEIGHTS_FILE" | \
        jq -r '.adaptive_adjustments | to_entries[] | "  - \(.key): +\(.value) (调整后)"' 2>/dev/null || \
        echo "  暂无调整"
    
    echo ""
    echo "=================="
    echo "更新时间: $(cat "$USER_BEHAVIOR_FILE" | jq -r '.last_update')"
}

# 主函数
case "${1:-}" in
    "init")
        init_learning
        echo "✅ 自适应学习系统已初始化"
        ;;
    
    "record")
        record_user_behavior "$2" "${3:-1}"
        ;;
    
    "stats")
        record_compression_stats "$2" "$3" "$4"
        ;;
    
    "adjust")
        auto_adjust_weights
        ;;
    
    "recommend")
        recommend_strategy "${2:-80}"
        ;;
    
    "feedback")
        learn_from_feedback "$2" "$3" "$4"
        ;;
    
    "report")
        generate_learning_report
        ;;
    
    "weights")
        get_adaptive_weights
        ;;
    
    *)
        echo "自适应学习引擎 v1"
        echo ""
        echo "用法:"
        echo "  $0 init                    # 初始化学习系统"
        echo "  $0 record <type> [value]   # 记录用户行为"
        echo "  $0 stats <session> <strategy> <saved>  # 记录压缩统计"
        echo "  $0 adjust                  # 自动调整权重"
        echo "  $0 recommend <usage>       # 推荐最佳策略"
        echo "  $0 feedback <session> <type> [details]  # 学习用户反馈"
        echo "  $0 report                  # 生成学习报告"
        echo "  $0 weights                 # 获取自适应权重"
        ;;
esac
