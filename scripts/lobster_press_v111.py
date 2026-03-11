#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v1.1.1 - 改进版压缩引擎
集成 Issue #25, #26, #30, #32 的优化

新功能：
1. Token 精确计量（tiktoken）
2. 净收益校验（避免负收益压缩）
3. 上下文连贯性（强制保留最近消息）
4. 动态模型选择（根据策略选择最优模型）

Author: LobsterPress Team
Version: v1.3.0
"""

import sys
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# 导入本地模块
sys.path.insert(0, str(Path(__file__).parent))
from token_counter import TokenCounter
from compression_validator import CompressionValidator, CompressionResult


@dataclass
class Message:
    """消息对象"""
    role: str
    content: str
    timestamp: float = 0
    importance: float = 50
    msg_type: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "msg_type": self.msg_type,
        }


@dataclass
class CompressionConfig:
    """压缩配置"""
    strategy: str = "medium"
    model_mapping: Dict[str, str] = field(default_factory=lambda: {
        "light": "glm-4-flash",
        "medium": "glm-4",
        "heavy": "claude-3-opus",
    })
    recent_window: int = 10  # 强制保留最近 N 条消息
    min_token_threshold: Dict[str, int] = field(default_factory=lambda: {
        "light": 8000,
        "medium": 6400,
        "heavy": 4000,
    })
    importance_weights: Dict[str, int] = field(default_factory=lambda: {
        "decision": 100,
        "error": 90,
        "config": 85,
        "preference": 80,
        "question": 70,
        "fact": 60,
        "action": 50,
        "feedback": 45,
        "context": 30,
        "chitchat": 10,
    })


class LobsterPressV111:
    """LobsterPress v1.1.1 压缩引擎"""
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        """初始化压缩引擎
        
        Args:
            config: 压缩配置
        """
        self.config = config or CompressionConfig()
        self.token_counter = TokenCounter()
        self.validator = CompressionValidator(self.config.strategy)
        
        # 获取策略对应的模型
        self.model = self.config.model_mapping.get(self.config.strategy, "glm-4")
        
        # 获取最小阈值
        self.min_threshold = self.config.min_token_threshold.get(self.config.strategy, 6400)
    
    def compress(self, messages: List[Message]) -> Tuple[List[Message], CompressionResult]:
        """压缩消息列表
        
        Args:
            messages: 原始消息列表
        
        Returns:
            (压缩后的消息列表, 压缩结果)
        """
        # 1. 计算原始 Token 数
        original_tokens = self.token_counter.count_messages([m.to_dict() for m in messages])
        
        # 2. 检查是否值得压缩
        should_compress, reason = self.validator.should_compress(original_tokens)
        if not should_compress:
            # 不压缩，返回原消息
            result = CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_cost=0,
                messages_kept=len(messages),
                messages_removed=0,
                strategy=self.config.strategy,
            )
            print(f"⚠️ {reason}", file=sys.stderr)
            return messages, result
        
        # 3. 评估消息重要性
        scored_messages = self._score_messages(messages)
        
        # 4. 强制保留最近 N 条消息（上下文连贯性）
        recent_messages = scored_messages[-self.config.recent_window:]
        older_messages = scored_messages[:-self.config.recent_window]
        
        # 5. 从历史消息中按重要性选择
        keep_count = self._get_keep_count(len(messages))
        keep_from_older = max(0, keep_count - len(recent_messages))
        
        # 按重要性排序历史消息
        older_sorted = sorted(older_messages, key=lambda m: m.importance, reverse=True)
        kept_older = older_sorted[:keep_from_older]
        
        # 6. 合并并按时间排序（保证顺序）
        final_messages = sorted(kept_older + recent_messages, key=lambda m: m.timestamp)
        
        # 7. 计算压缩后 Token 数
        compressed_tokens = self.token_counter.count_messages([m.to_dict() for m in final_messages])
        
        # 8. 估算压缩成本
        compression_cost = self.validator.compression_cost
        
        # 9. 创建压缩结果
        result = CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_cost=compression_cost,
            messages_kept=len(final_messages),
            messages_removed=len(messages) - len(final_messages),
            strategy=self.config.strategy,
        )
        
        # 10. 验证净收益
        report = self.validator.validate_result(result)
        print(f"📊 压缩报告: {report['recommendation']}", file=sys.stderr)
        
        return final_messages, result
    
    def _score_messages(self, messages: List[Message]) -> List[Message]:
        """评估消息重要性
        
        Args:
            messages: 消息列表
        
        Returns:
            评分后的消息列表
        """
        import time
        
        current_time = time.time()
        
        for msg in messages:
            # 基础分数（关键词匹配）
            base_score = self._match_keywords(msg.content)
            
            # 时间衰减（最多衰减 20 分）
            if msg.timestamp > 0:
                age_hours = (current_time - msg.timestamp) / 3600
                decay = min(20, age_hours * 0.5)
            else:
                decay = 0
            
            msg.importance = max(0, base_score - decay)
        
        return messages
    
    def _match_keywords(self, content: str) -> float:
        """关键词匹配
        
        Args:
            content: 消息内容
        
        Returns:
            基础分数
        """
        content_lower = content.lower()
        
        for msg_type, weight in self.config.importance_weights.items():
            # 简单的关键词匹配
            keywords = {
                "decision": ["决定", "decision", "选择", "确定", "就用"],
                "error": ["错误", "error", "失败", "bug", "问题"],
                "config": ["配置", "config", "设置", "api key", "环境变量"],
                "preference": ["偏好", "喜欢", "prefer", "习惯"],
                "question": ["问题", "怎么", "如何", "为什么", "?"],
                "fact": ["事实", "fact", "信息", "数据"],
                "action": ["执行", "运行", "action", "完成"],
                "feedback": ["反馈", "建议", "feedback"],
                "context": ["上下文", "背景", "context"],
                "chitchat": ["哈哈", "好的", "嗯嗯", "哦"],
            }
            
            if msg_type in keywords:
                for keyword in keywords[msg_type]:
                    if keyword in content_lower:
                        return float(weight)
        
        return 50.0  # 默认分数
    
    def _get_keep_count(self, total_count: int) -> int:
        """获取保留消息数
        
        Args:
            total_count: 总消息数
        
        Returns:
            保留消息数
        """
        rates = {
            "light": 0.85,   # Light 保留 85%
            "medium": 0.70,  # Medium 保留 70%
            "heavy": 0.55,   # Heavy 保留 55%
        }
        
        rate = rates.get(self.config.strategy, 0.70)
        return int(total_count * rate)
    
    def get_model_for_strategy(self) -> str:
        """获取当前策略对应的模型
        
        Returns:
            模型名称
        """
        return self.model


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LobsterPress v1.1.1 压缩引擎")
    parser.add_argument("input_file", help="输入文件（JSON 格式的消息列表）")
    parser.add_argument("--strategy", default="medium", choices=["light", "medium", "heavy"],
                       help="压缩策略")
    parser.add_argument("--output", help="输出文件（默认 stdout）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际压缩")
    parser.add_argument("--report", action="store_true", help="输出详细报告")
    
    args = parser.parse_args()
    
    # 读取输入
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取输入文件: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 转换为 Message 对象
    messages = []
    for item in data:
        msg = Message(
            role=item.get("role", "user"),
            content=item.get("content", ""),
            timestamp=item.get("timestamp", 0),
        )
        messages.append(msg)
    
    # 创建配置
    config = CompressionConfig(strategy=args.strategy)
    
    # 创建压缩引擎
    engine = LobsterPressV111(config)
    
    if args.dry_run:
        # 预览模式
        should, reason = engine.validator.should_compress(
            engine.token_counter.count_messages([m.to_dict() for m in messages])
        )
        print(f"预览: {reason}")
        print(f"模型: {engine.get_model_for_strategy()}")
        sys.exit(0)
    
    # 执行压缩
    compressed, result = engine.compress(messages)
    
    # 输出结果
    output_data = [m.to_dict() for m in compressed]
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已写入 {args.output}", file=sys.stderr)
    else:
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    
    # 输出报告
    if args.report:
        report = engine.validator.validate_result(result)
        print("\n📊 压缩报告:", file=sys.stderr)
        for key, value in report.items():
            print(f"  {key}: {value}", file=sys.stderr)


if __name__ == "__main__":
    main()
