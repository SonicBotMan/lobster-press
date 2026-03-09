#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压缩净收益校验器
确保压缩操作真正节省 Token

Issue: #25, #32 - Token 成本透明度 + 净收益校验
Author: LobsterPress Team
Version: v1.1.1
"""

import sys
import json
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class CompressionResult:
    """压缩结果"""
    original_tokens: int
    compressed_tokens: int
    compression_cost: int  # 压缩操作消耗的 Token
    messages_kept: int
    messages_removed: int
    strategy: str
    
    @property
    def gross_saving(self) -> int:
        """毛节省"""
        return self.original_tokens - self.compressed_tokens
    
    @property
    def net_saving(self) -> int:
        """净节省（扣除压缩成本）"""
        return self.gross_saving - self.compression_cost
    
    @property
    def gross_saving_rate(self) -> float:
        """毛节省率"""
        if self.original_tokens == 0:
            return 0.0
        return self.gross_saving / self.original_tokens * 100
    
    @property
    def net_saving_rate(self) -> float:
        """净节省率"""
        if self.original_tokens == 0:
            return 0.0
        return self.net_saving / self.original_tokens * 100
    
    @property
    def is_worth_compressing(self) -> bool:
        """是否值得压缩"""
        return self.net_saving > 0


class CompressionValidator:
    """压缩净收益校验器"""
    
    # 压缩成本估算（每次压缩操作的 Token 消耗）
    COMPRESSION_COSTS = {
        "light": 800,    # 轻度压缩成本较低
        "medium": 1600,  # 中度压缩
        "heavy": 2400,   # 深度压缩成本最高
    }
    
    # 最小 Token 阈值（低于此值不建议压缩）
    MIN_TOKEN_THRESHOLDS = {
        "light": 8000,   # Light 策略最小 8k
        "medium": 6400,  # Medium 策略最小 6.4k
        "heavy": 4000,   # Heavy 策略最小 4k
    }
    
    # 预期节省率
    EXPECTED_SAVING_RATES = {
        "light": 0.12,   # Light 策略预期节省 12%
        "medium": 0.27,  # Medium 策略预期节省 27%
        "heavy": 0.43,   # Heavy 策略预期节省 43%
    }
    
    def __init__(self, strategy: str = "medium"):
        """初始化校验器
        
        Args:
            strategy: 压缩策略 (light/medium/heavy)
        """
        self.strategy = strategy
        self.compression_cost = self.COMPRESSION_COSTS.get(strategy, 1600)
        self.min_threshold = self.MIN_TOKEN_THRESHOLDS.get(strategy, 6400)
        self.expected_rate = self.EXPECTED_SAVING_RATES.get(strategy, 0.27)
    
    def should_compress(self, original_tokens: int) -> tuple:
        """判断是否应该压缩
        
        Args:
            original_tokens: 原始 Token 数
        
        Returns:
            (should_compress: bool, reason: str)
        """
        # 检查是否低于最小阈值
        if original_tokens < self.min_threshold:
            return False, f"❌ 上下文太小 ({original_tokens} < {self.min_threshold})，压缩成本高于收益"
        
        # 估算净收益
        expected_gross = int(original_tokens * self.expected_rate)
        expected_net = expected_gross - self.compression_cost
        
        if expected_net <= 0:
            return False, f"❌ 预估净收益为负 ({expected_net} tokens)，不值得压缩"
        
        return True, f"✅ 预估净节省 {expected_net} tokens，建议压缩"
    
    def validate_result(self, result: CompressionResult) -> Dict:
        """验证压缩结果
        
        Args:
            result: 压缩结果
        
        Returns:
            验证报告
        """
        report = {
            "strategy": result.strategy,
            "original_tokens": result.original_tokens,
            "compressed_tokens": result.compressed_tokens,
            "compression_cost": result.compression_cost,
            "gross_saving": result.gross_saving,
            "net_saving": result.net_saving,
            "gross_saving_rate": f"{result.gross_saving_rate:.1f}%",
            "net_saving_rate": f"{result.net_saving_rate:.1f}%",
            "is_worth": result.is_worth_compressing,
            "messages_kept": result.messages_kept,
            "messages_removed": result.messages_removed,
            "recommendation": "",
        }
        
        # 生成建议
        if result.net_saving > 0:
            report["recommendation"] = f"✅ 压缩成功，净节省 {result.net_saving} tokens"
        elif result.net_saving == 0:
            report["recommendation"] = "⚠️ 压缩无收益，建议跳过"
        else:
            report["recommendation"] = f"❌ 压缩亏损 {-result.net_saving} tokens，不应执行"
        
        return report
    
    def calculate_break_even(self) -> Dict:
        """计算盈亏平衡点
        
        Returns:
            盈亏平衡分析
        """
        # 净收益 = 原始 × 节省率 - 成本
        # 盈亏平衡：原始 × 节省率 = 成本
        # 原始 = 成本 / 节省率
        
        break_even_tokens = int(self.compression_cost / self.expected_rate)
        
        return {
            "strategy": self.strategy,
            "compression_cost": self.compression_cost,
            "expected_saving_rate": f"{self.expected_rate * 100:.0f}%",
            "break_even_tokens": break_even_tokens,
            "recommendation": f"上下文 >= {break_even_tokens} tokens 时才值得压缩",
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="压缩净收益校验器")
    parser.add_argument("original_tokens", type=int, help="原始 Token 数")
    parser.add_argument("--strategy", default="medium", choices=["light", "medium", "heavy"],
                       help="压缩策略")
    parser.add_argument("--validate", help="验证压缩结果（JSON 格式）")
    parser.add_argument("--break-even", action="store_true", help="计算盈亏平衡点")
    
    args = parser.parse_args()
    
    validator = CompressionValidator(args.strategy)
    
    if args.break_even:
        # 计算盈亏平衡点
        result = validator.calculate_break_even()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.validate:
        # 验证压缩结果
        try:
            data = json.loads(args.validate)
            result = CompressionResult(**data)
            report = validator.validate_result(result)
            print(json.dumps(report, indent=2, ensure_ascii=False))
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 判断是否应该压缩
        should, reason = validator.should_compress(args.original_tokens)
        print(json.dumps({
            "should_compress": should,
            "reason": reason,
            "strategy": args.strategy,
            "min_threshold": validator.min_threshold,
        }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
