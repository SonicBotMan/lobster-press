#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v1.2.0 - Zero-cost 本地压缩引擎
基于 RFC #34 实现

核心特性：
1. 三层叠加评分（TF-IDF + 结构信号 + 时间衰减）
2. 语义去重（余弦相似度）
3. 提取式摘要（零 API 成本）
4. 分层模式（local/hybrid/api）

API 调用：0 次（local 模式）
压缩成本：$0.00

Author: LobsterPress Team
Version: v1.2.0
"""

import sys
import json
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

# 导入本地模块
sys.path.insert(0, str(Path(__file__).parent))
from tfidf_scorer import TFIDFScorer, ScoredMessage
from semantic_dedup import SemanticDeduplicator
from extractive_summarizer import ExtractiveSummarizer, ExtractedSummary


class CompressionMode(Enum):
    """压缩模式"""
    LOCAL = "local"      # 纯本地，零 API 成本
    HYBRID = "hybrid"    # 混合模式，可选 API 增强
    API = "api"          # API 模式，使用 LLM


@dataclass
class CompressionResult:
    """压缩结果"""
    original_messages: List[Dict]
    compressed_messages: List[Dict]
    summary: str
    removed_count: int
    dedup_count: int
    mode: CompressionMode
    api_calls: int = 0
    api_cost: float = 0.0
    
    @property
    def compression_rate(self) -> float:
        """压缩率"""
        if len(self.original_messages) == 0:
            return 0.0
        return len(self.compressed_messages) / len(self.original_messages)


@dataclass
class CompressionConfig:
    """压缩配置"""
    mode: CompressionMode = CompressionMode.LOCAL
    strategy: str = "medium"  # light/medium/heavy
    recent_window: int = 10   # 强制保留最近 N 条消息
    max_summary_chars: int = 200
    dedup_threshold: float = 0.82
    min_token_threshold: int = 4000  # 最小 token 阈值
    
    # 策略对应的保留率
    keep_rates: Dict[str, float] = field(default_factory=lambda: {
        "light": 0.85,
        "medium": 0.70,
        "heavy": 0.55,
    })


class LobsterPressV120:
    """LobsterPress v1.2.0 压缩引擎
    
    基于 RFC #34 的 Zero-cost 本地方案
    """
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        """初始化压缩引擎
        
        Args:
            config: 压缩配置
        """
        self.config = config or CompressionConfig()
        
        # 初始化组件
        self.scorer = TFIDFScorer()
        self.deduplicator = SemanticDeduplicator(threshold=self.config.dedup_threshold)
        self.summarizer = ExtractiveSummarizer(max_chars=self.config.max_summary_chars)
    
    def compress(self, messages: List[Dict]) -> CompressionResult:
        """压缩消息列表
        
        Args:
            messages: 原始消息列表
        
        Returns:
            压缩结果
        """
        if not messages:
            return CompressionResult(
                original_messages=[],
                compressed_messages=[],
                summary="",
                removed_count=0,
                dedup_count=0,
                mode=self.config.mode,
            )
        
        # 1. 评分
        scored_messages = self.scorer.score_messages(messages)
        
        # 2. 语义去重
        tokens_list = [msg.tokens for msg in scored_messages]
        scores = [msg.final_score for msg in scored_messages]
        
        deduped_messages, removed_indices = self.deduplicator.deduplicate(
            messages, tokens_list, scores
        )
        dedup_count = len(removed_indices)
        
        # 更新评分后的消息（移除重复）
        deduped_scored = [msg for i, msg in enumerate(scored_messages) 
                         if i not in removed_indices]
        
        # 3. 强制保留最近 N 条消息（上下文连贯性）
        recent_window = min(self.config.recent_window, len(deduped_messages))
        recent_messages = deduped_messages[-recent_window:]
        older_messages = deduped_messages[:-recent_window]
        older_scored = deduped_scored[:-recent_window] if deduped_scored else []
        
        # 4. 从历史消息中按重要性选择
        keep_rate = self.config.keep_rates.get(self.config.strategy, 0.70)
        keep_count = int(len(deduped_messages) * keep_rate)
        keep_from_older = max(0, keep_count - len(recent_messages))
        
        # 按重要性排序历史消息
        if older_scored:
            older_with_idx = list(enumerate(older_scored))
            older_sorted = sorted(older_with_idx, key=lambda x: x[1].final_score, reverse=True)
            kept_indices = [idx for idx, _ in older_sorted[:keep_from_older]]
            kept_older = [older_messages[i] for i in sorted(kept_indices)]
        else:
            kept_older = []
        
        # 5. 合并并保持顺序
        # 找到被丢弃的消息
        kept_older_set = set()
        for i, msg in enumerate(older_messages):
            if msg in kept_older:
                kept_older_set.add(i)
        
        dropped_messages = [msg for i, msg in enumerate(older_messages) 
                           if i not in kept_older_set]
        
        # 6. 生成提取式摘要
        dropped_scores = [scores[list(messages).index(msg)] for msg in dropped_messages 
                         if msg in messages]
        summary_result = self.summarizer.summarize(dropped_messages, dropped_scores)
        
        # 7. 组合最终消息
        final_messages = []
        
        # 添加摘要作为系统消息（如果有）
        if summary_result.summary:
            final_messages.append({
                "role": "system",
                "content": summary_result.summary,
                "type": "extractive_summary",
            })
        
        # 添加保留的历史消息
        final_messages.extend(kept_older)
        
        # 添加最近消息
        final_messages.extend(recent_messages)
        
        # 8. 计算结果
        removed_count = len(messages) - len(final_messages) + (1 if summary_result.summary else 0)
        
        return CompressionResult(
            original_messages=messages,
            compressed_messages=final_messages,
            summary=summary_result.summary,
            removed_count=removed_count,
            dedup_count=dedup_count,
            mode=self.config.mode,
            api_calls=0,  # Zero-cost!
            api_cost=0.0,
        )
    
    def get_compression_report(self, result: CompressionResult) -> str:
        """生成压缩报告
        
        Args:
            result: 压缩结果
        
        Returns:
            报告文本
        """
        lines = [
            "📊 LobsterPress v1.2.0 压缩报告",
            "",
            f"模式: {result.mode.value}",
            f"策略: {self.config.strategy}",
            "",
            f"原始消息数: {len(result.original_messages)}",
            f"压缩后消息数: {len(result.compressed_messages)}",
            f"去重移除: {result.dedup_count}",
            f"总移除: {result.removed_count}",
            f"压缩率: {result.compression_rate:.1%}",
            "",
            f"API 调用: {result.api_calls}",
            f"API 成本: ${result.api_cost:.4f}",
            "",
        ]
        
        if result.summary:
            lines.append("提取式摘要:")
            lines.append(f"  {result.summary}")
        
        return "\n".join(lines)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="LobsterPress v1.2.0 - Zero-cost 本地压缩引擎")
    parser.add_argument("input_file", help="输入文件（JSON 格式的消息列表）")
    parser.add_argument("--mode", choices=["local", "hybrid", "api"], default="local",
                       help="压缩模式")
    parser.add_argument("--strategy", choices=["light", "medium", "heavy"], default="medium",
                       help="压缩策略")
    parser.add_argument("--recent-window", type=int, default=10,
                       help="强制保留最近 N 条消息")
    parser.add_argument("--max-summary-chars", type=int, default=200,
                       help="摘要最大字符数")
    parser.add_argument("--dedup-threshold", type=float, default=0.82,
                       help="重复阈值")
    parser.add_argument("--output", help="输出文件")
    parser.add_argument("--report", action="store_true", help="输出详细报告")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    
    args = parser.parse_args()
    
    # 读取输入
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取输入文件: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 创建配置
    config = CompressionConfig(
        mode=CompressionMode(args.mode),
        strategy=args.strategy,
        recent_window=args.recent_window,
        max_summary_chars=args.max_summary_chars,
        dedup_threshold=args.dedup_threshold,
    )
    
    # 创建压缩引擎
    engine = LobsterPressV120(config)
    
    if args.dry_run:
        # 预览模式
        print(f"📊 预览模式")
        print(f"  模式: {config.mode.value}")
        print(f"  策略: {config.strategy}")
        print(f"  输入消息数: {len(messages)}")
        print(f"  预计保留率: {config.keep_rates[config.strategy]:.0%}")
        print(f"  强制保留最近: {config.recent_window} 条")
        sys.exit(0)
    
    # 执行压缩
    result = engine.compress(messages)
    
    # 输出
    if args.report:
        print(engine.get_compression_report(result))
    else:
        output = {
            "original_count": len(result.original_messages),
            "compressed_count": len(result.compressed_messages),
            "removed_count": result.removed_count,
            "dedup_count": result.dedup_count,
            "compression_rate": result.compression_rate,
            "api_calls": result.api_calls,
            "api_cost": result.api_cost,
            "summary": result.summary,
            "messages": result.compressed_messages,
        }
        
        output_json = json.dumps(output, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"✅ 已写入 {args.output}", file=sys.stderr)
        else:
            print(output_json)


if __name__ == "__main__":
    main()
