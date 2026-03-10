#!/bin/bash
# 龙虾饼 + OpenClaw 协调器 v1
# 检测 OpenClaw compaction 历史，避免重复压缩
# 
# 用法:
#   ./lobster-openclaw-coordinator.sh scan              # 扫描所有会话
#   ./lobster-openclaw-coordinator.sh check <file>      # 检查单个会话
#   ./lobster-openclaw-coordinator.sh recommend <file> <usage>  # 获取建议

set -e

SESSIONS_DIR="${SESSIONS_DIR:-$HOME/.openclaw/agents/main/sessions}"
COORDINATION_FILE="${COORDINATION_FILE:-$HOME/.lobster-press/openclaw-compaction-cache.json}"
SKIP_WINDOW_SECONDS="${SKIP_WINDOW_SECONDS:-3600}"  # 默认 1 小时内跳过

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
ORANGE='\033[0;33m'
NC='\033[0m' # No Color

# 初始化协调缓存
init_cache() {
    mkdir -p "$(dirname "$COORDINATION_FILE")" 2>/dev/null || true
    if [ ! -f "$COORDINATION_FILE" ]; then
        echo '{"sessions":{},"last_update":""}' > "$COORDINATION_FILE"
    fi
}

# 检查会话是否被 OpenClaw 压缩过
check_openclaw_compaction() {
    local session_file=$1
    local session_id=$(basename "$session_file" .jsonl)
    
    if [ ! -f "$session_file" ]; then
        echo "error:file_not_found"
        return 1
    fi
    
    init_cache
    
    # 检查文件中是否有 OpenClaw compaction 标记
    # OpenClaw 的 compaction 摘要通常包含特定标记
    if grep -qE "compaction|Compaction summary|🧹|历史摘要" "$session_file" 2>/dev/null; then
        # 获取最后一次压缩的时间戳
        local last_compact_line=$(grep -E "compaction|🧹|历史摘要" "$session_file" | tail -1)
        local last_compact=$(echo "$last_compact_line" | \
            jq -r '.timestamp // .message.timestamp // empty' 2>/dev/null)
        
        if [ -n "$last_compact" ]; then
            local compact_ts=$(date -d "$last_compact" +%s 2>/dev/null || echo 0)
            local now=$(date +%s)
            local age=$((now - compact_ts))
            
            # 在跳过窗口内，返回跳过
            if [ $age -lt $SKIP_WINDOW_SECONDS ]; then
                echo "skip:$age"
                return 0
            fi
        fi
    fi
    
    echo "proceed"
    return 1
}

# 记录压缩动作
record_action() {
    local session_id=$1
    local action=$2  # lobster / openclaw
    local details=${3:-""}
    local timestamp=$(date -Iseconds)
    
    init_cache
    
    local cache=$(cat "$COORDINATION_FILE")
    local entry="{\"action\":\"$action\",\"timestamp\":\"$timestamp\",\"details\":\"$details\"}"
    cache=$(echo "$cache" | jq ".sessions.\"$session_id\" = $entry")
    cache=$(echo "$cache" | jq ".last_update = \"$timestamp\"")
    echo "$cache" > "$COORDINATION_FILE"
}

# 计算 Token 使用率
get_token_usage() {
    local session_file=$1
    local file_size=$(stat -c%s "$session_file" 2>/dev/null || stat -f%z "$session_file" 2>/dev/null || echo 0)
    # 估算：每 4 字节约 1 token，模型上下文窗口默认 200k
    local estimated_tokens=$((file_size / 4))
    local context_window="${CONTEXT_WINDOW:-200000}"
    local usage=$((estimated_tokens * 100 / context_window))
    echo "$usage"
}

# 获取协调建议
get_recommendation() {
    local session_file=$1
    local token_usage=${2:-$(get_token_usage "$session_file")}
    
    local check_result=$(check_openclaw_compaction "$session_file")
    
    if [[ "$check_result" == skip:* ]]; then
        local age=${check_result#skip:}
        local age_min=$((age / 60))
        echo -e "${GREEN}✅ OpenClaw 已在 ${age_min}分钟前压缩过，建议跳过${NC}"
        return 0
    fi
    
    # 根据使用率给出建议
    if [ $token_usage -lt 60 ]; then
        echo -e "${GREEN}✅ Token 使用率正常（${token_usage}%），无需处理${NC}"
    elif [ $token_usage -lt 80 ]; then
        echo -e "${YELLOW}📊 Token 使用率 ${token_usage}%，建议：龙虾饼监控模式${NC}"
    elif [ $token_usage -lt 90 ]; then
        echo -e "${ORANGE}⚠️ Token 使用率 ${token_usage}%，建议：龙虾饼轻度压缩（light）${NC}"
    elif [ $token_usage -lt 95 ]; then
        echo -e "${ORANGE}🔶 Token 使用率 ${token_usage}%，建议：龙虾饼中度压缩 或 等待 OpenClaw${NC}"
    else
        echo -e "${RED}🔴 Token 使用率 ${token_usage}%，建议：让 OpenClaw 立即处理 或 手动 /compact${NC}"
    fi
}

# 获取应该执行的动作
get_action() {
    local session_file=$1
    local token_usage=${2:-$(get_token_usage "$session_file")}
    
    local check_result=$(check_openclaw_compaction "$session_file")
    
    if [[ "$check_result" == skip:* ]]; then
        echo "skip"
        return 0
    fi
    
    if [ $token_usage -lt 80 ]; then
        echo "none"
    elif [ $token_usage -lt 90 ]; then
        echo "light"
    elif [ $token_usage -lt 95 ]; then
        echo "medium"
    else
        echo "defer"  # 让 OpenClaw 处理
    fi
}

# 扫描所有会话并生成协调报告
scan_and_report() {
    echo -e "🔍 ${GREEN}龙虾饼 + OpenClaw 协调报告${NC}"
    echo "================================"
    echo ""
    
    local total=0
    local safe=0
    local need_attention=0
    local recently_compacted=0
    
    for session_file in "$SESSIONS_DIR"/*.jsonl; do
        [[ "$session_file" == *.backup.* ]] && continue
        [[ "$session_file" == *.deleted.* ]] && continue
        [[ "$session_file" == *.reset.* ]] && continue
        [ ! -f "$session_file" ] && continue
        
        total=$((total + 1))
        local session_id=$(basename "$session_file" .jsonl)
        
        # 计算 Token 使用率
        local token_usage=$(get_token_usage "$session_file")
        
        # 检查 OpenClaw 压缩状态
        local check_result=$(check_openclaw_compaction "$session_file")
        
        if [[ "$check_result" == skip:* ]]; then
            recently_compacted=$((recently_compacted + 1))
            continue
        fi
        
        # 分类统计
        if [ $token_usage -lt 60 ]; then
            safe=$((safe + 1))
        elif [ $token_usage -gt 80 ]; then
            need_attention=$((need_attention + 1))
            echo "📁 $session_id"
            echo "   $(get_recommendation "$session_file" $token_usage)"
            echo ""
        fi
    done
    
    echo "================================"
    echo "📊 统计:"
    echo "   总会话数: $total"
    echo "   🟢 安全 (< 60%): $safe"
    echo "   🔴 需关注 (> 80%): $need_attention"
    echo "   ✅ 近期已压缩: $recently_compacted"
}

# JSON 格式输出（供程序调用）
json_report() {
    local sessions_array="[]"
    
    for session_file in "$SESSIONS_DIR"/*.jsonl; do
        [[ "$session_file" == *.backup.* ]] && continue
        [[ "$session_file" == *.deleted.* ]] && continue
        [[ "$session_file" == *.reset.* ]] && continue
        [ ! -f "$session_file" ] && continue
        
        local session_id=$(basename "$session_file" .jsonl)
        local token_usage=$(get_token_usage "$session_file")
        local check_result=$(check_openclaw_compaction "$session_file")
        local action=$(get_action "$session_file" $token_usage)
        
        local entry="{\"id\":\"$session_id\",\"usage\":$token_usage,\"action\":\"$action\"}"
        sessions_array=$(echo "$sessions_array" | jq ". += [$entry]")
    done
    
    echo "{\"sessions\":$sessions_array,\"timestamp\":\"$(date -Iseconds)\"}"
}

# 主函数
case "${1:-}" in
    "check")
        check_openclaw_compaction "$2"
        ;;
    "record")
        record_action "$2" "$3" "$4"
        ;;
    "recommend")
        get_recommendation "$2" "${3:-}"
        ;;
    "action")
        get_action "$2" "${3:-}"
        ;;
    "scan")
        scan_and_report
        ;;
    "json")
        json_report
        ;;
    "usage")
        get_token_usage "$2"
        ;;
    *)
        echo "龙虾饼 + OpenClaw 协调器 v1"
        echo ""
        echo "用法:"
        echo "  $0 scan                      # 扫描并生成报告"
        echo "  $0 check <session_file>      # 检查是否需要压缩"
        echo "  $0 recommend <file> [usage]  # 获取协调建议"
        echo "  $0 action <file> [usage]     # 获取应执行的动作"
        echo "  $0 record <session> <action> [details]  # 记录压缩动作"
        echo "  $0 json                      # JSON 格式报告"
        echo "  $0 usage <file>              # 获取 Token 使用率"
        echo ""
        echo "环境变量:"
        echo "  SESSIONS_DIR        - OpenClaw 会话目录"
        echo "  SKIP_WINDOW_SECONDS - 跳过窗口（秒），默认 3600"
        echo "  CONTEXT_WINDOW      - 模型上下文窗口，默认 200000"
        ;;
esac
