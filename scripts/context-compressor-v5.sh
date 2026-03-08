#!/bin/bash
# 会话历史智能压缩脚本 v5 - 集成消息重要性评估引擎
# 新特性：多维评分 + 智能分类 + 动态配额 + 用户行为学习

set -e

# 默认配置（可被环境变量覆盖）
AUTO_APPLY=${AUTO_APPLY:-true}
LOG_LEVEL=${LOG_LEVEL:-INFO}

SESSIONS_DIR="$HOME/.openclaw/agents/main/sessions"
GLM_API="https://open.bigmodel.cn/api/paas/v4/chat/completions"
CACHE_DIR="/tmp/compress-cache"
METRICS_FILE="/tmp/compress-metrics.json"
HISTORY_FILE="$HOME/.lobster-press/compression-history.md"
ENGINE_SH="$HOME/bin/message-importance-engine.sh"

# 引入重要性评估引擎和自适应学习引擎
source "$ENGINE_SH" 2>/dev/null || true
source ~/bin/adaptive-learning-engine.sh 2>/dev/null || true

# 创建必要目录和文件
mkdir -p "$CACHE_DIR" "$(dirname "$HISTORY_FILE")" 2>/dev/null || true
touch "$HISTORY_FILE" 2>/dev/null || true

# 自动读取 API Key
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

get_glm_key() {
    # 优先从 OpenClaw 配置读取
    local key=$(cat ~/.openclaw/agents/main/agent/auth-profiles.json 2>/dev/null | \
        jq -r '.profiles."zai:default".key' 2>/dev/null)
    
    # fallback 到环境变量
    if [ -z "$key" ] || [ "$key" = "null" ]; then
        key=$GLM_API_KEY
    fi
    
    echo "$key"
}

GLM_KEY=$(get_glm_key)

# Token 估算
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

estimate_tokens() {
    local text=$1
    local char_count=$(echo "$text" | wc -c)
    echo $((char_count / 3))
}

# 获取会话 token 使用率
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

get_token_usage() {
    local session_file=$1
    local file_size=$(stat -c%s "$session_file" 2>/dev/null || echo 0)
    local estimated_tokens=$((file_size / 4))
    local usage=$((estimated_tokens * 100 / 200000))
    echo "$usage"
}

# 根据使用率决定压缩策略
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

get_compress_strategy() {
    local usage=$1
    
    if [ $usage -lt 70 ]; then
        echo "none"
    elif [ $usage -lt 85 ]; then
        echo "light"
    elif [ $usage -lt 95 ]; then
        echo "medium"
    else
        echo "heavy"
    fi
}

# 智能提取消息（集成重要性评估）
extract_messages_v5() {
    local session_file=$1
    local max_messages=$2
    local strategy=${3:-"medium"}
    
    # 提取所有消息
    local all_messages=$(cat "$session_file" | \
        jq -r 'select(.type == "message") | .message.content[]? | select(.type == "text") | .text' 2>/dev/null | \
        grep -v "^#" | grep -v "^$")
    
    # 根据策略调整最大消息数
    case $strategy in
        light)   max_messages=$((max_messages * 120 / 100)) ;;  # 保留更多
        medium)  ;;  # 不变
        heavy)   max_messages=$((max_messages * 80 / 100)) ;;   # 保留更少
    esac
    
    # 使用智能分层提取
    if type smart_layered_extraction &>/dev/null; then
        smart_layered_extraction "$all_messages" $max_messages
    else
        # 回退到简单提取
        echo "$all_messages" | head -$max_messages
    fi
}

# 检查缓存
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

check_cache() {
    local content_hash=$1
    local cache_file="$CACHE_DIR/$content_hash.txt"
    
    if [ -f "$cache_file" ]; then
        local cache_age=$(($(date +%s) - $(stat -c%Y "$cache_file")))
        if [ $cache_age -lt 3600 ]; then
            cat "$cache_file"
            return 0
        fi
    fi
    return 1
}

# 保存缓存
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

save_cache() {
    local content_hash=$1
    local summary=$2
    local cache_file="$CACHE_DIR/$content_hash.txt"
    
    echo "$summary" > "$cache_file"
    
    ls -t "$CACHE_DIR"/*.txt 2>/dev/null | tail -n +101 | xargs rm -f 2>/dev/null || true
}

# 记录压缩历史
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

record_history() {
    local session_id=$1
    local strategy=$2
    local original_size=$3
    local compressed_size=$4
    local saved_percent=$5
    local details=${6:-""}
    
    local record="- $(date '+%Y-%m-%d %H:%M:%S') | $session_id | $strategy | ${original_size}B → ${compressed_size}B | 节省 ${saved_percent}% | $details"
    
    echo "$record" >> "$HISTORY_FILE"
    
    tail -100 "$HISTORY_FILE" > "${HISTORY_FILE}.tmp"
    mv "${HISTORY_FILE}.tmp" "$HISTORY_FILE"
}

# 更新指标
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

update_metrics() {
    local session_id=$1
    local action=$2
    local saved=${3:-0}
    
    if [ ! -f "$METRICS_FILE" ]; then
        echo '{"total":0,"compressed":0,"skipped":0,"failed":0,"total_saved":0,"by_strategy":{}}' > "$METRICS_FILE"
    fi
    
    local metrics=$(cat "$METRICS_FILE")
    local total=$(echo "$metrics" | jq '.total')
    local compressed=$(echo "$metrics" | jq '.compressed')
    local skipped=$(echo "$metrics" | jq '.skipped')
    local failed=$(echo "$metrics" | jq '.failed')
    local total_saved=$(echo "$metrics" | jq '.total_saved')
    
    total=$((total + 1))
    
    case $action in
        compress)
            compressed=$((compressed + 1))
            total_saved=$((total_saved + saved))
            
            # 按策略统计
            local strategy=$4
            local strategy_count=$(echo "$metrics" | jq ".by_strategy.$strategy // 0")
            strategy_count=$((strategy_count + 1))
            metrics=$(echo "$metrics" | jq ".by_strategy.$strategy = $strategy_count")
            ;;
        skip) skipped=$((skipped + 1)) ;;
        fail) failed=$((failed + 1)) ;;
    esac
    
    cat > "$METRICS_FILE" <<EOF
{
  "total": $total,
  "compressed": $compressed,
  "skipped": $skipped,
  "failed": $failed,
  "total_saved": $total_saved,
  "last_update": "$(date -Iseconds)",
  "by_strategy": $(echo "$metrics" | jq '.by_strategy')
}
EOF
}

# 压缩会话历史（主函数）
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

compress_session() {
    # 获取并发锁，防止同时压缩同一会话
    local session_id=$(basename "$session_file" .jsonl)
    exec 200>"/tmp/compress-.lock"
    if ! flock -n 200; then
        echo "❌ 会话正在被压缩，跳过"
        return 1
    fi

    local session_id=$1
    local session_file="$SESSIONS_DIR/${session_id}.jsonl"
    
    if [ ! -f "$session_file" ]; then
        echo "❌ 会话文件不存在: $session_id"
        update_metrics "$session_id" "fail"
        return 1
    fi
    
    local total_lines=$(wc -l < "$session_file")
    local file_size=$(stat -c%s "$session_file")
    local token_usage=$(get_token_usage "$session_file")
    
    echo "📊 会话分析: $total_lines 行, ${file_size}B, Token 使用率 ${token_usage}%"
    
    # 决定压缩策略
    local strategy=$(get_compress_strategy $token_usage)
    
    if [ "$strategy" = "none" ]; then
        echo "⏭️ Token 使用率正常（${token_usage}% < 70%），跳过"
        update_metrics "$session_id" "skip"
        return 0
    fi
    
    # 根据策略调整压缩比例
    local keep_ratio
    case $strategy in
        light)  keep_ratio=90 ;;
        medium) keep_ratio=80 ;;
        heavy)  keep_ratio=60 ;;
    esac
    
    local compress_lines=$((total_lines * (100 - keep_ratio) / 100))
    local keep_lines=$((total_lines - compress_lines))
    
    echo "🎯 压缩策略: $strategy (保留 ${keep_ratio}%)"
    echo "📝 将压缩: 前 $compress_lines 行"
    echo "📌 保留: 后 $keep_lines 行"
    
    # 智能提取消息（v5 引擎）
    local max_messages=50
    [ "$strategy" = "heavy" ] && max_messages=30
    [ "$strategy" = "light" ] && max_messages=70
    
    local old_messages=$(extract_messages_v5 "$session_file" $max_messages "$strategy")
    
    if [ -z "$old_messages" ]; then
        echo "⚠️ 没有可压缩的消息"
        update_metrics "$session_id" "skip"
        return 0
    fi
    
    # 检查缓存
    local content_hash=$(echo "$old_messages" | md5sum | cut -d' ' -f1)
    local cached_summary
    local use_cache=false
    
    if cached_summary=$(check_cache "$content_hash"); then
        echo "✅ 使用缓存结果"
        local summary="$cached_summary"
        use_cache=true
    fi
    
    if [ "$use_cache" = "false" ]; then
        # 计算原始大小
        local original_size=$(echo "$old_messages" | wc -c)
        echo "📏 原始大小: $original_size 字节"
        
        # 调用 GLM-4-Flash 压缩（带重试机制）
        echo "🤖 正在调用 GLM-4-Flash 压缩（策略: $strategy + 智能评估）..."
        
        local max_tokens=800
        [ "$strategy" = "heavy" ] && max_tokens=500
        [ "$strategy" = "light" ] && max_tokens=1000
        
        local prompt="请将以下对话历史压缩成摘要，保留关键决策、重要信息和用户偏好。
压缩级别：$strategy
要求：
- light: 500 字以内，保留细节
- medium: 300 字以内，保留关键点
- heavy: 200 字以内，只保留核心

只输出摘要内容："
        
        prompt="$prompt

$old_messages"
        
        # 重试配置
        local max_retries=3
        local retry_delay=2
        local retry_count=0
        local response=""
        local summary=""
        
        while [ $retry_count -lt $max_retries ]; do
            response=$(curl -s -m 30 -X POST "$GLM_API" \
                -H "Authorization: Bearer $GLM_KEY" \
                -H "Content-Type: application/json" \
                -d "{
                    \"model\": \"glm-4-flash\",
                    \"messages\": [{\"role\": \"user\", \"content\": $(echo "$prompt" | jq -Rs .)}],
                    \"max_tokens\": $max_tokens,
                    \"temperature\": 0.3
                }" 2>&1)
            
            # 提取压缩结果
            summary=$(echo "$response" | jq -r '.choices[0].message.content // empty' 2>/dev/null)
            
            # 检查是否成功
            if [ -n "$summary" ] && [ "$summary" != "null" ]; then
                break
            fi
            
            # 检查是否是限流错误
            if echo "$response" | grep -q "速率限制\|rate limit\|1302"; then
                retry_count=$((retry_count + 1))
                if [ $retry_count -lt $max_retries ]; then
                    echo "⏳ API 限流，等待 ${retry_delay}s 后重试（$retry_count/$max_retries）..."
                    sleep $retry_delay
                    retry_delay=$((retry_delay * 2))  # 指数退避
                fi
            else
                # 其他错误直接退出
                break
            fi
        done
        
        # 提取压缩结果
        local summary=$(echo "$response" | jq -r '.choices[0].message.content // empty' 2>/dev/null)
        
        if [ -z "$summary" ] || [ "$summary" = "null" ]; then
            echo "❌ 压缩失败: $(sanitize_response "$response" | head -100)"
            
            # 容错：回退到本地压缩
            echo "🔄 尝试本地压缩..."

            # 跨平台中文字符提取（兼容 GNU grep 和 BSD grep）
            if grep --version 2>&1 | grep -q "GNU"; then
                # GNU grep 支持 -P (Perl 正则)
                summary=$(echo "$old_messages" | \
                    grep -oP '[\x{4e00}-\x{9fa5}]{2,10}' | \
                    sort | uniq -c | sort -rn | \
                    head -30 | awk '{print $2}' | tr '\n' ' ')
            else
                # BSD/macOS grep 使用传统正则
                summary=$(echo "$old_messages" | \
                    LC_ALL=UTF-8 grep -o '[一-龥]\{2,10\}' | \
                    sort | uniq -c | sort -rn | \
                    head -30 | awk '{print $2}' | tr '\n' ' ')
            fi

            if [ -z "$summary" ]; then
                # 最后的 fallback：直接取前 5 条消息的关键词
                summary=$(echo "$old_messages" | head -5 | tr ' ' '\n' | \
                    grep -E '^[a-zA-Z0-9_-]{3,}$' | head -20 | tr '\n' ' ')
            fi

            if [ -z "$summary" ]; then
                return 1
            fi
        fi
        
        # 保存缓存
        echo "$summary" > "$CACHE_DIR/$content_hash.txt"
    fi
    
    local summary_size=$(echo "$summary" | wc -c)
    
    if [ "$use_cache" = "false" ]; then
        local saved=$((100 - summary_size * 100 / original_size))
        echo ""
        echo "✅ 压缩成功（$original_size → $summary_size 字节，节省 $saved%）"
    else
        echo ""
        echo "✅ 压缩成功（$summary_size 字节，使用缓存）"
    fi
    echo ""
    echo "--- 压缩结果 ---"
    echo "$summary"
    echo "----------------"
    echo ""
    
    # 创建新的会话文件
    local timestamp=$(date +%s000)
    local iso_timestamp=$(date -Iseconds)
    
    local summary_message="{\"type\":\"message\",\"id\":\"compress-$(date +%s)\",\"parentId\":null,\"timestamp\":\"$iso_timestamp\",\"message\":{\"role\":\"assistant\",\"content\":[{\"type\":\"text\",\"text\":\"[历史摘要 - $strategy - v5智能] $summary\"}],\"api\":\"openai-responses\",\"provider\":\"openclaw\",\"model\":\"compressor-v5\",\"timestamp\":$timestamp}}"
    
    # 备份原文件
    cp "$session_file" "${session_file}.backup.$(date +%s)"
    
    # 组合：压缩摘要 + 最近消息
    {
        head -5 "$session_file"
        echo "$summary_message"
        tail -$keep_lines "$session_file"
    } > "${session_file}.compressed"
    
    # 计算文件级别节省
    local old_file_size=$(stat -c%s "$session_file")
    local new_file_size=$(stat -c%s "${session_file}.compressed")
    local file_saved=$((100 - new_file_size * 100 / old_file_size))
    
    echo "📉 文件压缩效果: $old_file_size → $new_file_size 字节（节省 $file_saved%）"
    
    # 应用压缩
    if [ "$AUTO_APPLY" = "true" ]; then
        mv "${session_file}.compressed" "$session_file"
        echo "✅ 已应用压缩"
        
        # 记录历史和指标（包含详细信息）
        local details="重要性评估引擎v2 + 自适应学习"
        record_history "$session_id" "$strategy" "$old_file_size" "$new_file_size" "$file_saved" "$details"
        update_metrics "$session_id" "compress" "$file_saved" "$strategy"
        
        # 记录到自适应学习系统
        ~/adaptive-learning-engine.sh stats "$session_id" "$strategy" "$file_saved" 2>/dev/null || true
        
        # 自动调整权重
        ~/adaptive-learning-engine.sh adjust 2>/dev/null || true
    else
        read -p "是否应用压缩结果？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mv "${session_file}.compressed" "$session_file"
            echo "✅ 已应用压缩"
            
            local details="重要性评估引擎v1"
            record_history "$session_id" "$strategy" "$old_file_size" "$new_file_size" "$file_saved" "$details"
            update_metrics "$session_id" "compress" "$file_saved" "$strategy"
        else
            echo "❌ 已取消"
            rm "${session_file}.compressed"
            update_metrics "$session_id" "skip"
        fi
    fi
}

# 预防性扫描
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

scan_and_compress() {
    echo "🔍 预防性扫描开始（v5 智能引擎）..."
    local compressed=0
    local skipped=0
    local total=0
    
    for session_file in "$SESSIONS_DIR"/*.jsonl; do
        if [[ "$session_file" == *.backup.* ]] || [[ "$session_file" == *.reset.* ]] || [[ "$session_file" == *.deleted.* ]]; then
            continue
        fi
        
        if [ ! -f "$session_file" ]; then
            continue
        fi
        
        total=$((total + 1))
        
        local token_usage=$(get_token_usage "$session_file")
        local session_id=$(basename "$session_file" .jsonl)
        
        if [ $token_usage -gt 70 ]; then
            echo ""
            echo "===================="
            echo "📁 处理会话: $session_id (Token: ${token_usage}%)"
            AUTO_APPLY=true compress_session "$session_id" && compressed=$((compressed + 1)) || skipped=$((skipped + 1))
        fi
    done
    
    echo ""
    echo "===================="
    echo "✅ 扫描完成（v5 智能引擎）"
    echo "📊 统计: 总计 $total 个会话, 压缩 $compressed 个, 跳过 $skipped 个"
    
    if [ -f "$METRICS_FILE" ]; then
        echo ""
        echo "--- 历史指标 ---"
        cat "$METRICS_FILE" | jq '.'
    fi
}

# 显示指标
# 清理 API 响应中的敏感信息
sanitize_response() {
    local response=$1
    echo "$response" | sed -E 's/(api[_-]?key|token|authorization|bearer)[^,}]*/1=***REDACTED***/gi'
}

show_metrics() {
    if [ -f "$METRICS_FILE" ]; then
        echo "📊 压缩指标统计（v5）"
        echo "================"
        cat "$METRICS_FILE" | jq '.'
    else
        echo "❌ 暂无指标数据"
    fi
}

# 主函数
case "${1:-}" in
    "test")
        echo "🔍 查找测试会话..."
        local test_file=$(ls -t "$SESSIONS_DIR"/*.jsonl 2>/dev/null | \
            grep -v ".backup\|.reset\|.deleted" | head -1)
        
        if [ -z "$test_file" ]; then
            echo "❌ 没有找到会话文件"
            exit 1
        fi
        
        local session_id=$(basename "$test_file" .jsonl)
        echo "📁 测试会话: $session_id"
        echo ""
        compress_session "$session_id"
        ;;
    
    "scan")
        scan_and_compress
        ;;
    
    "metrics")
        show_metrics
        ;;
    
    "all")
        scan_and_compress
        ;;
    
    *)
        if [ -n "$1" ]; then
            compress_session "$1"
        else
            echo "会话历史智能压缩脚本 v5（集成重要性评估引擎）"
            echo ""
            echo "用法:"
            echo "  $0 scan              # 预防性扫描（推荐用于定时任务）"
            echo "  $0 test              # 测试压缩（选最新的会话）"
            echo "  $0 all               # 批量压缩所有会话"
            echo "  $0 metrics           # 查看压缩指标"
            echo "  $0 <session_id>      # 压缩指定会话"
            echo ""
            echo "v5 新特性:"
            echo "  ✅ 多维重要性评分（决策>错误>配置>偏好>问题>事实>行动>上下文>闲聊）"
            echo "  ✅ 智能消息分类（10 个类别）"
            echo "  ✅ 动态配额分配（根据分类结果调整）"
            echo "  ✅ 用户行为学习（从历史提取关键词）"
            echo "  ✅ 时间衰减（越新越重要）"
        fi
        ;;
esac
