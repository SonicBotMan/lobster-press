#!/bin/bash
# LobsterPress 基础用法示例

# 设置路径
LOBSTER_BIN=~/bin

echo "🦞 LobsterPress 基础用法示例"
echo "============================="
echo ""

# 示例 1: 手动压缩单个会话
echo "📌 示例 1: 手动压缩单个会话"
echo "命令: $LOBSTER_BIN/context-compressor-v5.sh your_session_id"
echo ""

# 示例 2: 预览压缩效果
echo "📌 示例 2: 预览压缩效果（不实际应用）"
echo "命令: $LOBSTER_BIN/context-compressor-v5.sh --dry-run your_session_id"
echo ""

# 示例 3: 使用指定策略
echo "📌 示例 3: 使用指定策略压缩"
echo "命令: $LOBSTER_BIN/context-compressor-v5.sh --strategy medium your_session_id"
echo ""

# 示例 4: 自动扫描并压缩
echo "📌 示例 4: 自动扫描所有会话并压缩"
echo "命令: $LOBSTER_BIN/context-compressor-v5.sh --auto-scan"
echo ""

# 示例 5: 查看学习报告
echo "📌 示例 5: 查看学习报告"
echo "命令: $LOBSTER_BIN/adaptive-learning-engine.sh report"
echo ""

# 示例 6: 推荐策略
echo "📌 示例 6: 获取策略推荐"
echo "命令: $LOBSTER_BIN/adaptive-learning-engine.sh recommend 80"
echo ""

# 示例 7: 执行预测性压缩
echo "📌 示例 7: 执行预测性压缩"
echo "命令: $LOBSTER_BIN/predictive-compressor.sh"
echo ""

# 示例 8: 执行成本优化分析
echo "📌 示例 8: 执行成本优化分析"
echo "命令: $LOBSTER_BIN/cost-optimizer.sh"
echo ""

echo "✅ 更多示例请参考 docs/API.md"
