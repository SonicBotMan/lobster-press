#!/bin/bash
# LobsterPress 集成示例 - 展示如何集成到现有系统

set -e

# 导入 LobsterPress 函数
LOBSTER_BIN=~/bin
source $LOBSTER_BIN/message-importance-engine.sh

echo "🦞 LobsterPress 集成示例"
echo "========================="
echo ""

# ============================================
# 示例 1: 作为 Python 脚本使用
# ============================================
cat << 'PYTHON_EXAMPLE'
import subprocess
import json

def compress_session(session_id, strategy='auto'):
    """压缩单个会话"""
    cmd = ['~/bin/context-compressor-v5.sh']
    
    if strategy != 'auto':
        cmd.extend(['--strategy', strategy])
    
    cmd.append(session_id)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return {
            'success': True,
            'output': result.stdout
        }
    else:
        return {
            'success': False,
            'error': result.stderr
        }

# 使用示例
result = compress_session('abc123', 'medium')
if result['success']:
    print("压缩成功:", result['output'])
else:
    print("压缩失败:", result['error'])
PYTHON_EXAMPLE

echo ""
echo "---"
echo ""

# ============================================
# 示例 2: 作为 Node.js 模块使用
# ============================================
cat << 'NODE_EXAMPLE'
const { exec } = require('child_tree');
const util = require('util');
const execPromise = util.promisify(exec);

async function compressSession(sessionId, strategy = 'auto') {
  try {
    let cmd = `~/bin/context-compressor-v5.sh ${sessionId}`;
    
    if (strategy !== 'auto') {
      cmd = `~/bin/context-compressor-v5.sh --strategy ${strategy} ${sessionId}`;
    }
    
    const { stdout, stderr } = await execPromise(cmd);
    
    return {
      success: true,
      output: stdout
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

// 使用示例
(async () => {
  const result = await compressSession('abc123', 'medium');
  if (result.success) {
    console.log('压缩成功:', result.output);
  } else {
    console.error('压缩失败:', result.error);
  }
})();
NODE_EXAMPLE

echo ""
echo "---"
echo ""

# ============================================
# 示例 3: 作为 Bash 函数使用
# ============================================
cat << 'BASH_EXAMPLE'
# 导入函数
source ~/bin/message-importance-engine.sh

# 评估消息重要性
score=$(calculate_importance "这是重要的决策记录")
echo "重要性分数: $score"

# 分类消息类型
type=$(classify_message "修复了配置错误")
echo "消息类型: $type"

# 获取推荐策略
source ~/bin/adaptive-learning-engine.sh
strategy=$(recommend_strategy 80)
echo "推荐策略: $strategy"
BASH_EXAMPLE

echo ""
echo "---"
echo ""

# ============================================
# 示例 4: Webhook 通知
# ============================================
cat << 'WEBHOOK_EXAMPLE'
# 在压缩完成后发送通知

compress_and_notify() {
    local session_id=$1
    local webhook_url="https://your-webhook-url"
    
    # 执行压缩
    result=$($LOBSTER_BIN/context-compressor-v5.sh "$session_id" 2>&1)
    
    # 发送通知
    curl -X POST "$webhook_url" \
         -H "Content-Type: application/json" \
         -d "{\"text\": \"LobsterPress 压缩完成\\n会话: $session_id\\n结果: $result\"}"
}

# 使用示例
compress_and_notify "session123"
WEBHOOK_EXAMPLE

echo ""
echo "---"
echo ""

# ============================================
# 示例 5: 定时任务集成
# ============================================
cat << 'CRON_EXAMPLE'
# 添加到 crontab

# 每30分钟执行预测性压缩
*/30 * * * * ~/bin/predictive-compressor.sh

# 每小时执行学习调度
0 * * * * ~/bin/smart-learning-scheduler.sh

# 每天执行成本优化
0 0 * * * ~/bin/cost-optimizer.sh

# 查看定时任务
crontab -l
CRON_EXAMPLE

echo ""
echo "---"
echo ""

# ============================================
# 示例 6: 监控系统集成
# ============================================
cat << 'MONITOR_EXAMPLE'
# 导出 Prometheus 指标

export_prometheus_metrics() {
    local metrics_file="/var/lib/node_exporter/textfile_collector/lobster_press.prom"
    
    # 获取统计数据
    local total=$(cat ~/.lobster-press/adaptive-learning/compression-stats.json | jq '.total_compressions')
    local light_count=$(cat ~/.lobster-press/adaptive-learning/compression-stats.json | jq '.by_strategy.light.count')
    local medium_count=$(cat ~/.lobster-press/adaptive-learning/compression-stats.json | jq '.by_strategy.medium.count')
    local heavy_count=$(cat ~/.lobster-press/adaptive-learning/compression-stats.json | jq '.by_strategy.heavy.count')
    
    # 写入指标
    cat <<EOF > "$metrics_file"
lobster_press_compressions_total{strategy="light"} $light_count
lobster_press_compressions_total{strategy="medium"} $medium_count
lobster_press_compressions_total{strategy="heavy"} $heavy_count
lobster_press_compressions_total{strategy="all"} $total
EOF
}

# 每分钟更新指标
export_prometheus_metrics
MONITOR_EXAMPLE

echo ""
echo "✅ 集成示例完成"
echo ""
echo "更多集成方式请参考:"
echo "- docs/API.md"
echo "- docs/CUSTOMIZATION.md"
