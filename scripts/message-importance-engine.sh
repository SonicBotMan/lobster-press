#!/bin/bash
# 消息重要性评估引擎 v2 - 修复版
# 多维度评分 + 智能权重 + 用户行为学习

set -e

# 重要性维度配置
declare -A IMPORTANCE_WEIGHTS=(
    ["decision"]=100
    ["error"]=90
    ["config"]=85
    ["preference"]=80
    ["question"]=70
    ["fact"]=60
    ["action"]=50
    ["feedback"]=45
    ["context"]=30
    ["chitchat"]=10
)

# 关键词模式（带权重）
declare -A KEYWORD_PATTERNS=(
    ["决定|决策|选择|确定|确认|同意|批准|执行|实施"]=100
    ["最终方案|选定|采用|启用|关闭|禁用"]=95
    ["错误|失败|异常|崩溃|超时|拒绝"]=90
    ["警告|告警|问题|bug|缺陷|故障"]=85
    ["修复|解决|恢复|回滚"]=80
    ["配置|设置|参数|选项|环境|变量"]=85
    ["安装|部署|更新|升级|卸载"]=80
    ["API|密钥|token|密码|认证"]=90
    ["偏好|喜欢|希望|想要|需要|要求"]=80
    ["习惯|风格|方式|格式|模式"]=75
    ["怎么|如何|为什么|是否|能不能"]=70
    ["什么|哪个|哪里|何时|谁"]=65
)

# 时间衰减函数
time_decay() {
    local timestamp=$1
    local now=$(date +%s)
    local age=$((now - timestamp))
    
    if [ $age -lt 3600 ]; then
        echo 100
    elif [ $age -lt 21600 ]; then
        echo 80
    elif [ $age -lt 86400 ]; then
        echo 60
    elif [ $age -lt 604800 ]; then
        echo 40
    else
        echo 20
    fi
}

# 计算消息重要性分数
calculate_importance() {
    local message=$1
    local timestamp=${2:-$(date +%s)}
    local total_score=0
    
    # 关键词匹配
    for pattern in "${!KEYWORD_PATTERNS[@]}"; do
        if echo "$message" | grep -qE "$pattern"; then
            score=${KEYWORD_PATTERNS[$pattern]}
            total_score=$((total_score + score))
        fi
    done
    
    # 时间衰减
    local decay=$(time_decay $timestamp)
    total_score=$((total_score * decay / 100))
    
    # 长度调整
    local length=${#message}
    if [ $length -lt 20 ]; then
        total_score=$((total_score * 80 / 100))
    elif [ $length -gt 500 ]; then
        total_score=$((total_score * 90 / 100))
    fi
    
    # 用户行为学习
    local user_keywords=$(get_user_important_keywords)
    if [ -n "$user_keywords" ]; then
        if echo "$message" | grep -qE "$user_keywords"; then
            total_score=$((total_score + 30))
        fi
    fi
    
    echo $total_score
}

# 获取用户关注的关键词
get_user_important_keywords() {
    local history_file="$HOME/.openclaw/workspace/memory/compression-history.md"
    local keywords_file="/tmp/user-important-keywords.txt"
    
    if [ -f "$keywords_file" ]; then
        local cache_age=$(($(date +%s) - $(stat -c%Y "$keywords_file")))
        if [ $cache_age -lt 3600 ]; then
            cat "$keywords_file"
            return
        fi
    fi
    
    if [ -f "$history_file" ]; then
        local summaries=$(tail -20 "$history_file" | grep -oE '\-.*节省' | head -20)
        
        # 修复：使用正确的中文正则
        local keywords=$(echo "$summaries" | \
            grep -oE '[一-龥]{2,6}' | \
            sort | uniq -c | sort -rn | \
            head -20 | awk '{print $2}' | tr '\n' '|')
        
        echo "$keywords" | sed 's/|$//' > "$keywords_file"
        cat "$keywords_file"
    fi
}

# 消息分类
classify_message() {
    local message=$1
    
    if echo "$message" | grep -qE "决定|决策|选择|确定|确认|同意|批准|最终"; then
        echo "decision"
        return
    fi
    
    if echo "$message" | grep -qE "错误|失败|异常|崩溃|超时|修复|解决"; then
        echo "error"
        return
    fi
    
    if echo "$message" | grep -qE "配置|设置|参数|安装|部署|API|密钥"; then
        echo "config"
        return
    fi
    
    if echo "$message" | grep -qE "偏好|喜欢|希望|想要|需要|要求"; then
        echo "preference"
        return
    fi
    
    if echo "$message" | grep -qE "怎么|如何|为什么|是否|什么|哪个"; then
        echo "question"
        return
    fi
    
    if echo "$message" | grep -qE "哈哈|嘿嘿|嗯|哦|随便|都行"; then
        echo "chitchat"
        return
    fi
    
    echo "context"
}

# 智能分层提取
smart_layered_extraction() {
    local messages=$1
    local max_count=$2
    
    declare -A category_messages
    
    while IFS= read -r message; do
        [ -z "$message" ] && continue
        
        local category=$(classify_message "$message")
        category_messages[$category]="${category_messages[$category]}$message"$'\n'
    done <<< "$messages"
    
    local result=""
    
    # 优先级 1: 决策、错误、配置
    for cat in decision error config; do
        if [ -n "${category_messages[$cat]}" ]; then
            result="$result${category_messages[$cat]}"
        fi
    done
    
    # 优先级 2: 偏好、问题
    for cat in preference question; do
        if [ -n "${category_messages[$cat]}" ]; then
            local cat_count=$(echo "${category_messages[$cat]}" | grep -c .)
            local keep=$((cat_count * 80 / 100))
            [ $keep -lt 1 ] && keep=1
            
            result="$result$(echo "${category_messages[$cat]}" | head -$keep)"$'\n'
        fi
    done
    
    # 优先级 3: 事实、行动
    for cat in fact action; do
        if [ -n "${category_messages[$cat]}" ]; then
            local cat_count=$(echo "${category_messages[$cat]}" | grep -c .)
            local keep=$((cat_count * 50 / 100))
            
            if [ $keep -gt 0 ]; then
                result="$result$(echo "${category_messages[$cat]}" | head -$keep)"$'\n'
            fi
        fi
    done
    
    # 优先级 4: 上下文
    if [ -n "${category_messages[context]}" ]; then
        local cat_count=$(echo "${category_messages[context]}" | grep -c .)
        local keep=$((cat_count * 30 / 100))
        
        if [ $keep -gt 0 ]; then
            local step=$((cat_count / keep))
            result="$result$(echo "${category_messages[context]}" | awk "NR % $step == 0")"$'\n'
        fi
    fi
    
    # 优先级 5: 闲聊
    if [ -n "${category_messages[chitchat]}" ]; then
        result="$result$(echo "${category_messages[chitchat]}" | head -3)"$'\n'
    fi
    
    echo "$result" | grep -v "^$" | uniq | head -$max_count
}

# 主函数：测试
test_engine() {
    echo "🧪 消息重要性评估测试（v2）"
    echo "===================="
    
    # 测试消息列表
    local test_messages=(
        "决定采用方案A进行系统升级"
        "数据库连接超时，已自动重试"
        "API Key 已更新为 sk-xxx"
        "用户希望每天12点备份"
        "如何提高压缩效率？"
        "当前系统版本 2026.3.2"
        "哈哈，这个方案不错"
    )
    
    for msg in "${test_messages[@]}"; do
        score=$(calculate_importance "$msg")
        category=$(classify_message "$msg")
        echo "[$category] 分数: $score | $msg"
    done
}

if [ "$1" = "test" ]; then
    test_engine
fi
