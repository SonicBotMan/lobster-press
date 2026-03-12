#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息类型权重配置 v1.5.0
Issue #76 - 消息类型差异化压缩

定义不同消息类型的评分权重和保护策略
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import re


@dataclass
class MessageTypeConfig:
    """消息类型配置"""
    name: str
    base_score: float
    protection_level: str  # high, medium, low
    compression_strategy: str  # full, extract, aggressive
    keywords: List[str]


class MessageTypeWeights:
    """消息类型权重管理器
    
    根据消息类型和内容特征调整评分权重
    """
    
    # 消息类型配置
    TYPE_CONFIGS: Dict[str, MessageTypeConfig] = {
        "user": MessageTypeConfig(
            name="user",
            base_score=0.7,
            protection_level="high",
            compression_strategy="full",
            keywords=[]
        ),
        "assistant_decision": MessageTypeConfig(
            name="assistant_decision",
            base_score=0.8,
            protection_level="high",
            compression_strategy="full",
            keywords=["决定", "采用", "chosen", "will use", "config", "chosen", "确定", "选择"]
        ),
        "assistant_normal": MessageTypeConfig(
            name="assistant_normal",
            base_score=0.5,
            protection_level="medium",
            compression_strategy="extract",
            keywords=[]
        ),
        "assistant_chitchat": MessageTypeConfig(
            name="assistant_chitchat",
            base_score=0.1,
            protection_level="low",
            compression_strategy="aggressive",
            keywords=["好的", "ok", "嗯", "👍", "谢谢", "got it", "嗯嗯", "哦哦", "收到"]
        ),
        "thinking": MessageTypeConfig(
            name="thinking",
            base_score=0.3,
            protection_level="low",
            compression_strategy="aggressive",
            keywords=[]
        ),
        "tool_result": MessageTypeConfig(
            name="tool_result",
            base_score=0.4,
            protection_level="medium",
            compression_strategy="extract",
            keywords=[]
        ),
    }
    
    # 决策关键词
    DECISION_KEYWORDS = [
        "决定", "采用", "chosen", "will use", "config", "chosen",
        "确定", "选择", "配置", "设置", "使用"
    ]
    
    # 闲聊关键词
    CHITCHAT_PATTERNS = [
        r'^(好的|ok|嗯|👍|谢谢|got it|嗯嗯|哦哦|收到|好|是|对)$',
        r'^(好的|ok|收到)[。，]?$',
    ]
    
    @classmethod
    def classify_message(cls, role: str, content: str) -> str:
        """分类消息类型
        
        Args:
            role: 消息角色 (user/assistant)
            content: 消息内容
        
        Returns:
            消息类型名称
        """
        # user 消息总是高保护
        if role == "user":
            return "user"
        
        # assistant 消息需要进一步分类
        if role == "assistant":
            # 检查是否是决策类消息
            content_lower = content.lower()
            if any(kw in content_lower for kw in cls.DECISION_KEYWORDS):
                return "assistant_decision"
            
            # 检查是否是闲聊
            content_stripped = content.strip().lower()
            for pattern in cls.CHITCHAT_PATTERNS:
                if re.match(pattern, content_stripped):
                    return "assistant_chitchat"
            
            # 普通 assistant 消息
            return "assistant_normal"
        
        # thinking 消息
        if role == "thinking":
            return "thinking"
        
        # tool_result 消息
        if role == "tool_result":
            return "tool_result"
        
        return "assistant_normal"
    
    @classmethod
    def get_weight_adjustment(cls, message_type: str) -> float:
        """获取权重调整值
        
        Args:
            message_type: 消息类型
        
        Returns:
            权重调整值 (-1.0 ~ 1.0)
        """
        config = cls.TYPE_CONFIGS.get(message_type)
        if not config:
            return 0.0
        
        # 根据保护级别调整
        protection_multipliers = {
            "high": 0.3,
            "medium": 0.0,
            "low": -0.2,
        }
        
        return protection_multipliers.get(config.protection_level, 0.0)
    
    @classmethod
    def should_compress_aggressively(cls, message_type: str) -> bool:
        """判断是否应该激进压缩
        
        Args:
            message_type: 消息类型
        
        Returns:
            是否激进压缩
        """
        config = cls.TYPE_CONFIGS.get(message_type)
        if not config:
            return False
        
        return config.compression_strategy == "aggressive"
    
    @classmethod
    def should_extract_facts(cls, message_type: str) -> bool:
        """判断是否应该提取事实（用于 toolResult）
        
        Args:
            message_type: 消息类型
        
        Returns:
            是否提取事实
        """
        config = cls.TYPE_CONFIGS.get(message_type)
        if not config:
            return False
        
        return config.compression_strategy == "extract"
    
    @classmethod
    def is_decision_message(cls, content: str) -> bool:
        """判断是否是决策消息
        
        Args:
            content: 消息内容
        
        Returns:
            是否是决策消息
        """
        content_lower = content.lower()
        return any(kw in content_lower for kw in cls.DECISION_KEYWORDS)
    
    @classmethod
    def is_chitchat(cls, content: str) -> bool:
        """判断是否是闲聊消息
        
        Args:
            content: 消息内容
        
        Returns:
            是否是闲聊
        """
        content_stripped = content.strip().lower()
        for pattern in cls.CHITCHAT_PATTERNS:
            if re.match(pattern, content_stripped):
                return True
        return False


def main():
    """测试入口"""
    test_messages = [
        ("user", "我想了解一下 Python 编程"),
        ("assistant", "决定采用 FastAPI 框架"),
        ("assistant", "好的，收到了"),
        ("assistant", "这是一个很长的解释..."),
        ("thinking", "让我思考一下这个问题"),
        ("tool_result", "[Result: success]"),
    ]
    
    print("📊 消息类型分类测试:")
    print("-" * 60)
    
    for role, content in test_messages:
        msg_type = MessageTypeWeights.classify_message(role, content)
        weight_adj = MessageTypeWeights.get_weight_adjustment(msg_type)
        aggressive = MessageTypeWeights.should_compress_aggressively(msg_type)
        extract = MessageTypeWeights.should_extract_facts(msg_type)
        
        print(f"Role: {role:15} | Type: {msg_type:20}")
        print(f"  Content: {content[:40]}")
        print(f"  Weight Adj: {weight_adj:+.1f} | Aggressive: {aggressive} | Extract: {extract}")
        print()


if __name__ == "__main__":
    main()
