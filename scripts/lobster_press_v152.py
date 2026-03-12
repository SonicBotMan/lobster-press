#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v1.5.4 - OpenClaw 兼容的压缩引擎
修复 Issue #49：格式兼容、元数据保留、完整内容支持

核心修复：
1. 输入/输出使用 JSONL 格式（OpenClaw 标准）
2. 保留完整的消息元数据（id, parentId, timestamp, type）
3. 支持所有 content 类型（text, toolCall, thinking, toolResult）
4. 摘要作为新消息添加，不破坏原始结构

Author: LobsterPress Team
Version: v1.5.4
"""

import sys
import json
import argparse
import hashlib
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import re


# ======== Step 2: 新增模块导入 ========
try:
    from tfidf_scorer import TFIDFScorer
    from semantic_dedup import SemanticDeduplicator
    from extractive_summarizer import ExtractiveSummarizer
    from message_type_weights import MessageTypeWeights   # 新增
    from tool_result_extractor import ToolResultExtractor # 新增
    from embedding_dedup import EmbeddingDeduplicator     # 新增
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 核心模块导入失败: {e}", file=sys.stderr)
    print("⚠️ 将使用 fallback 模式", file=sys.stderr)
    MODULES_AVAILABLE = False


@dataclass
class CompressionStats:
    """压缩统计"""
    original_lines: int = 0
    compressed_lines: int = 0
    original_bytes: int = 0
    compressed_bytes: int = 0
    messages_removed: int = 0
    content_preserved: Dict[str, int] = field(default_factory=dict)
    
    @property
    def compression_ratio(self) -> float:
        if self.original_bytes == 0:
            return 0.0
        return 1 - (self.compressed_bytes / self.original_bytes)
    
    def to_dict(self) -> Dict:
        return {
            "original_lines": self.original_lines,
            "compressed_lines": self.compressed_lines,
            "original_bytes": self.original_bytes,
            "compressed_bytes": self.compressed_bytes,
            "compression_ratio": f"{self.compression_ratio:.1%}",
            "messages_removed": self.messages_removed,
            "content_preserved": self.content_preserved,
        }


class OpenClawSessionParser:
    """OpenClaw 会话解析器
    
    处理 JSONL 格式的会话文件，保留完整结构
    """
    
    def __init__(self):
        self.lines: List[Dict] = []
        self.header: Optional[Dict] = None
        self.header_index: int = 0            # 新增：记录 header 的行号
        self.messages: List[Tuple[int, Dict]] = []  # 修复：携带原始行索引
        self.other_lines: List[Tuple[int, Dict]] = []
    
    def parse_jsonl(self, content: str) -> None:
        """解析 JSONL 文件
        
        Args:
            content: JSONL 文件内容
        """
        for i, line in enumerate(content.strip().split('\n')):
            if not line.strip():
                continue
            
            try:
                obj = json.loads(line)
                self.lines.append(obj)
                
                # 识别会话头
                if obj.get('type') == 'session':
                    self.header = obj
                    self.header_index = i         # 新增：记录 header 行号
                # 识别消息
                elif obj.get('type') == 'message':
                    self.messages.append((i, obj)) # 修复：携带行号
                # 其他类型（toolResult, thinking 等）
                else:
                    self.other_lines.append((i, obj))
            except json.JSONDecodeError as e:
                print(f"⚠️ 行 {i+1} 解析失败: {e}", file=sys.stderr)
    
    def get_message_content(self, msg: Dict) -> List[Dict]:
        """获取消息的所有内容
        
        支持所有 content 类型：text, toolCall, thinking, toolResult
        
        Args:
            msg: 消息对象
        
        Returns:
            内容列表
        """
        content = msg.get('message', {}).get('content', [])
        if isinstance(content, str):
            return [{'type': 'text', 'text': content}]
        return content if isinstance(content, list) else []
    
    def get_text_content(self, msg: Dict) -> str:
        """获取消息的文本内容（用于摘要）
        
        Args:
            msg: 消息对象
        
        Returns:
            文本内容
        """
        texts = []
        for item in self.get_message_content(msg):
            if item.get('type') == 'text':
                texts.append(item.get('text', ''))
            elif item.get('type') == 'toolCall':
                # 保留工具调用的关键信息
                func = item.get('function', {})
                texts.append(f"[Tool: {func.get('name', 'unknown')}]")
            elif item.get('type') == 'thinking':
                texts.append(f"[Thinking: {item.get('thinking', '')[:100]}...]")
            elif item.get('type') == 'toolResult':
                # 工具结果通常很长，只保留摘要
                result = item.get('content', '')
                
                # ======== Step 3: 使用 ToolResultExtractor 压缩长结果 ========
                if MODULES_AVAILABLE:
                    try:
                        compressed = ToolResultExtractor.compress_tool_result(result, max_length=200)
                        texts.append(compressed)
                    except Exception as e:
                        print(f"⚠️ ToolResult 压缩失败: {e}", file=sys.stderr)
                        texts.append(f"[Result: {result}]")
                else:
                    # Fallback：原有逻辑
                    if len(result) > 200:
                        result = result[:200] + '...'
                    texts.append(f"[Result: {result}]")
        
        return '\n'.join(texts)
    
    def estimate_tokens(self, text: str) -> int:
        """估算 token 数量
        
        Args:
            text: 文本内容
        
        Returns:
            估算的 token 数
        """
        # 简单估算：中文约 1.5 字/token，英文约 4 字/token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)


class CompressionStrategy:
    """压缩策略"""
    
    LIGHT = "light"      # 保留 85%
    MEDIUM = "medium"    # 保留 70%
    HEAVY = "heavy"      # 保留 55%
    
    KEEP_RATES = {
        "light": 0.85,
        "medium": 0.70,
        "heavy": 0.55,
    }
    
    @classmethod
    def from_token_usage(cls, usage_percent: int) -> str:
        """根据 token 使用率选择策略
        
        Args:
            usage_percent: token 使用百分比
        
        Returns:
            策略名称
        """
        if usage_percent < 70:
            return "none"
        elif usage_percent < 85:
            return "light"
        elif usage_percent < 95:
            return "medium"
        else:
            return "heavy"


class LobsterPressV124:
    """LobsterPress v1.5.4 压缩引擎
    
    OpenClaw 兼容版本
    """
    
    def __init__(self, 
                 strategy: str = "medium",
                 recent_window: int = 10,
                 max_summary_chars: int = 500,
                 preserve_all_content: bool = True):
        """初始化压缩引擎
        
        Args:
            strategy: 压缩策略 (light/medium/heavy)
            recent_window: 强制保留最近 N 条消息
            max_summary_chars: 摘要最大字符数
            preserve_all_content: 是否保留所有内容类型
        """
        self.strategy = strategy
        self.recent_window = recent_window
        self.max_summary_chars = max_summary_chars
        self.preserve_all_content = preserve_all_content
        self.stats = CompressionStats()
    
    def _score_message(self, msg: Dict, parser: OpenClawSessionParser) -> float:
        """评分消息重要性
        
        Args:
            msg: 消息对象
            parser: 解析器
        
        Returns:
            重要性分数 (0-1)
        """
        score = 0.5  # 基础分
        
        # ======== Step 4: 使用 TFIDFScorer ========
        if MODULES_AVAILABLE:
            try:
                scorer = TFIDFScorer()
                content = parser.get_text_content(msg)
                role = msg.get('message', {}).get('role', 'user')
                timestamp = msg.get('timestamp', 0)
                scored_msg = scorer.score_message(content, timestamp, role)
                score = scored_msg.score
            except Exception as e:
                print(f"⚠️ TF-IDF 评分失败，使用 fallback: {e}", file=sys.stderr)
        
        # ======== Step 4: 消息类型权重调整 ========
        if MODULES_AVAILABLE:
            try:
                role = msg.get('message', {}).get('role', 'user')
                
                # 从 content items 中推断消息子类型
                content_type = None
                content_items = parser.get_message_content(msg)
                content_text = ""
                
                for item in content_items:
                    if item.get('type') == 'text':
                        content_text += item.get('text', '')
                    elif item.get('type') == 'thinking':
                        content_type = 'thinking'
                        content_text += item.get('thinking', '')
                    elif item.get('type') == 'toolResult':
                        content_type = 'toolResult'
                        content_text += item.get('content', '')
                
                # 分类消息类型
                msg_type = MessageTypeWeights.classify_message(role, content_text, content_type)
                weight_adj = MessageTypeWeights.get_weight_adjustment(msg_type)
                score = min(1.0, max(0.0, score + weight_adj))
            except Exception as e:
                print(f"⚠️ MessageTypeWeights 调整失败，跳过: {e}", file=sys.stderr)
        
        # Fallback：原有逻辑（仅在模块不可用时）
        if not MODULES_AVAILABLE:
            # 角色权重
            role = msg.get('message', {}).get('role', '')
            if role == 'user':
                score += 0.2
            elif role == 'assistant':
                score += 0.1
            
            # 内容类型权重
            content = parser.get_message_content(msg)
            has_tool_call = any(c.get('type') == 'toolCall' for c in content)
            has_thinking = any(c.get('type') == 'thinking' for c in content)
            
            if has_tool_call:
                score += 0.15
            if has_thinking:
                score += 0.1
            
            # 文本长度
            text = parser.get_text_content(msg)
            text_len = len(text)
            if 100 < text_len < 1000:
                score += 0.1
            elif text_len >= 1000:
                score -= 0.05
        
        return min(1.0, max(0.0, score))
    
    def _generate_summary(self, messages: List[Dict], parser: OpenClawSessionParser) -> str:
        """生成摘要（本地提取式）
        
        Args:
            messages: 要摘要的消息列表
            parser: 解析器
        
        Returns:
            摘要文本
        """
        if not messages:
            return ""
        
        # ======== Step 5: 优先使用 ExtractiveSummarizer ========
        if MODULES_AVAILABLE:
            try:
                summarizer = ExtractiveSummarizer()
                summarizer_messages = []
                for msg in messages:
                    c = parser.get_text_content(msg)
                    role = msg.get('message', {}).get('role', 'unknown')
                    summarizer_messages.append({'content': c, 'role': role})
                summary_obj = summarizer.summarize(summarizer_messages)
                return summary_obj.summary
            except Exception as e:
                print(f"⚠️ ExtractiveSummarizer 失败，使用 fallback: {e}", file=sys.stderr)
        
        # Fallback：规则摘要
        # 提取关键信息
        key_points = []
        
        for msg in messages:
            text = parser.get_text_content(msg)
            role = msg.get('message', {}).get('role', 'unknown')
            
            # 提取句子（简单分句）
            sentences = re.split(r'[。！？\n]', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 10:
                    continue
                
                # 识别关键句（包含决策、重要信息）
                is_key = any(kw in sentence for kw in [
                    '决定', '选择', '确认', '同意', '修改', '创建', '删除',
                    '问题', '解决', '错误', '成功', '完成', '重要', '注意'
                ])
                
                if is_key:
                    key_points.append(f"[{role}] {sentence[:100]}")
        
        # 限制摘要长度
        summary = '\n'.join(key_points[:10])
        if len(summary) > self.max_summary_chars:
            summary = summary[:self.max_summary_chars] + "..."
        
        return summary
    
    def _create_summary_message(self, summary: str, strategy: str) -> Dict:
        """创建摘要消息（OpenClaw 格式）
        
        Args:
            summary: 摘要内容
            strategy: 压缩策略
        
        Returns:
            摘要消息对象
        """
        timestamp = datetime.now().isoformat()
        msg_id = f"compress-{int(datetime.now().timestamp())}"
        
        return {
            "type": "message",
            "id": msg_id,
            "parentId": None,
            "timestamp": timestamp,
            "message": {
                "role": "assistant",
                "content": [{
                    "type": "text",
                    "text": f"[历史摘要 - {strategy} - v1.5.4]\n{summary}"
                }],
                "api": "openai-responses",
                "provider": "openclaw",
                "model": "lobster-press-v124",
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
        }
    
    def compress(self, content: str) -> Tuple[str, CompressionStats]:
        """压缩 JSONL 会话
        
        Args:
            content: JSONL 文件内容
        
        Returns:
            (压缩后的 JSONL 内容, 统计信息)
        """
        parser = OpenClawSessionParser()
        parser.parse_jsonl(content)
        
        self.stats.original_lines = len(parser.lines)
        self.stats.original_bytes = len(content.encode('utf-8'))
        
        # 统计内容类型
        for msg in parser.messages:
            for item in parser.get_message_content(msg):
                content_type = item.get('type', 'unknown')
                self.stats.content_preserved[content_type] = \
                    self.stats.content_preserved.get(content_type, 0) + 1
        
        if not parser.messages:
            return content, self.stats
        
        # 计算保留数量
        keep_rate = CompressionStrategy.KEEP_RATES.get(self.strategy, 0.70)
        total_messages = len(parser.messages)
        keep_count = int(total_messages * keep_rate)
        
        # 强制保留最近消息
        recent_count = min(self.recent_window, total_messages)
        older_count = total_messages - recent_count
        keep_from_older = max(0, keep_count - recent_count)
        
        # ======== Step 6: Embedding 去重（在评分之前） ========
        older_messages = parser.messages[:older_count]
        deduplicated_older_messages = older_messages
        
        if MODULES_AVAILABLE and len(older_messages) > 1:
            try:
                deduplicator = EmbeddingDeduplicator()
                scorer = TFIDFScorer()
                
                # 准备去重所需的数据
                dedup_messages = []
                tokens_list = []
                for msg in older_messages:
                    c = parser.get_text_content(msg)
                    role = msg.get('message', {}).get('role', 'user')
                    ts = msg.get('timestamp', 0)
                    dedup_messages.append({
                        'content': c,
                        'role': role,
                        'timestamp': ts,
                        'original_msg': msg
                    })
                    tokens_list.append(scorer.tokenize(c))
                
                # Step 2 修复：计算真实分数后再去重
                scored_for_dedup = scorer.score_messages(dedup_messages)
                real_scores = [sm.score for sm in scored_for_dedup]
                
                deduped_result, removed_indices = deduplicator.deduplicate(
                    [{'content': m['content']} for m in dedup_messages],
                    real_scores,  # 修复：使用真实分数
                    tokens_list
                )
                
                # 根据去重结果过滤
                if removed_indices:
                    removed_set = set(removed_indices)
                    deduplicated_older_messages = [
                        m['original_msg'] for i, m in enumerate(dedup_messages) if i not in removed_set
                    ]
                    print(f"🔄 Embedding 去重: 移除 {len(removed_indices)} 条重复消息", file=sys.stderr)
            except Exception as e:
                print(f"⚠️ EmbeddingDeduplicator 去重失败，跳过: {e}", file=sys.stderr)
        
        # 评分历史消息（去重后）
        scored = [(msg, self._score_message(msg, parser)) for msg in deduplicated_older_messages]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # 选择要保留的历史消息
        kept_older = [msg for msg, score in scored[:keep_from_older]]
        
        # 要压缩的消息
        dropped_messages = [msg for msg, score in scored[keep_from_older:]]
        
        # 生成摘要
        summary = self._generate_summary(dropped_messages, parser)
        
        # Step 3 修复：在 drop 操作之后， 只统计实际保留的消息
        kept_recent = parser.messages[-recent_count:]
        for idx, msg in kept_older:
            for item in parser.get_message_content(msg):
                ct = item.get('type', 'unknown')
                self.stats.content_preserved[ct] = self.stats.content_preserved.get(ct, 0) + 1
        for idx, msg in kept_recent:
            for item in parser.get_message_content(msg):
                ct = item.get('type', 'unknown')
                self.stats.content_preserved[ct] = self.stats.content_preserved.get(ct, 0) + 1
        
        # 构建输出
        output_lines = []
        
        # 1. 添加会话头
        if parser.header:
            output_lines.append(json.dumps(parser.header, ensure_ascii=False))
        
        # 2. 添加其他非消息行
        for _, line in parser.other_lines:
            output_lines.append(json.dumps(line, ensure_ascii=False))
        
        # 3. 添加摘要消息
        if summary:
            summary_msg = self._create_summary_message(summary, self.strategy)
            output_lines.append(json.dumps(summary_msg, ensure_ascii=False))
        
        # 4. 添加保留的历史消息
        for msg in kept_older:
            output_lines.append(json.dumps(msg, ensure_ascii=False))
        
        # 5. 添加最近的完整消息（复用上面已定义的 kept_recent）
        for idx, msg in kept_recent:
            output_lines.append(json.dumps(msg, ensure_ascii=False))
        
        # 构建输出
        result = '\n'.join(output_lines) + '\n'
        
        # 更新统计
        self.stats.compressed_lines = len(output_lines)
        self.stats.compressed_bytes = len(result.encode('utf-8'))
        self.stats.messages_removed = len(dropped_messages)
        
        return result, self.stats
    
    def get_report(self) -> str:
        """生成压缩报告
        
        Returns:
            报告文本
        """
        lines = [
            "📊 LobsterPress v1.5.4 压缩报告",
            "",
            f"策略: {self.strategy}",
            f"保留最近: {self.recent_window} 条消息",
            "",
            f"原始: {self.stats.original_lines} 行, {self.stats.original_bytes}B",
            f"压缩后: {self.stats.compressed_lines} 行, {self.stats.compressed_bytes}B",
            f"压缩率: {self.stats.compression_ratio:.1%}",
            f"移除消息: {self.stats.messages_removed}",
            "",
            "内容类型保留:",
        ]
        
        for content_type, count in self.stats.content_preserved.items():
            lines.append(f"  - {content_type}: {count}")
        
        return '\n'.join(lines)


def main():
    """命令行入口"""
    arg_parser = argparse.ArgumentParser(
        description="LobsterPress v1.5.4 - OpenClaw 兼容的压缩引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 压缩会话
  %(prog)s session.jsonl -o compressed.jsonl
  
  # 使用 heavy 策略
  %(prog)s session.jsonl --strategy heavy -o compressed.jsonl
  
  # 预览模式
  %(prog)s session.jsonl --dry-run
  
  # 查看详细报告
  %(prog)s session.jsonl --report
"""
    )
    
    arg_parser.add_argument("input_file", help="输入文件（OpenClaw JSONL 格式）")
    arg_parser.add_argument("--strategy", "-s", 
                       choices=["light", "medium", "heavy"], 
                       default="medium",
                       help="压缩策略 (default: medium)")
    arg_parser.add_argument("--recent-window", "-r", 
                       type=int, default=10,
                       help="强制保留最近 N 条消息 (default: 10)")
    arg_parser.add_argument("--max-summary-chars", 
                       type=int, default=500,
                       help="摘要最大字符数 (default: 500)")
    arg_parser.add_argument("--output", "-o", 
                       help="输出文件")
    arg_parser.add_argument("--report", 
                       action="store_true",
                       help="输出详细报告")
    arg_parser.add_argument("--dry-run", 
                       action="store_true",
                       help="预览模式，不写入文件")
    arg_parser.add_argument(
        "--backup",
        action="store_true",
        default=False,  # 修复：改回 False
        help="备份原始输入文件（仅当原地压缩时有效，default: False)"
    )
    
    args = arg_parser.parse_args()
    
    # 读取输入
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 无法读取输入文件: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 创建压缩引擎
    engine = LobsterPressV124(
        strategy=args.strategy,
        recent_window=args.recent_window,
        max_summary_chars=args.max_summary_chars,
    )
    
    if args.dry_run:
        # 预览模式
        print(f"📊 预览模式")
        print(f"  输入文件: {args.input_file}")
        print(f"  策略: {args.strategy}")
        print(f"  保留最近: {args.recent_window} 条")
        print(f"  预计保留率: {CompressionStrategy.KEEP_RATES[args.strategy]:.0%}")
        
        # 解析并统计
        session_parser = OpenClawSessionParser()
        session_parser.parse_jsonl(content)
        print(f"  消息数: {len(session_parser.messages)}")
        print(f"  总行数: {len(session_parser.lines)}")
        sys.exit(0)
    
    # 执行压缩
    result, stats = engine.compress(content)
    
    # 输出
    if args.report:
        print(engine.get_report())
        print()
        print("前 5 行预览:")
        for i, line in enumerate(result.split('\n')[:5]):
            if line:
                try:
                    obj = json.loads(line)
                    print(f"  {i+1}. type={obj.get('type', 'unknown')}")
                except:
                    print(f"  {i+1}. [parse error]")
    else:
        if args.output:
            # 修复：恢复原地检查
            if args.backup and args.output == args.input_file:
                backup_file = f"{args.input_file}.backup.{int(datetime.now().timestamp())}"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"📦 已备份: {backup_file}", file=sys.stderr)
            elif args.backup and args.output != args.input_file:
                print("⚠️ --backup 仅在原地压缩（-o 与输入文件相同）时有效，本次已忽略",
                      file=sys.stderr)
            
            # 写入
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"✅ 已写入 {args.output}", file=sys.stderr)
            print(f"📊 压缩率: {stats.compression_ratio:.1%}", file=sys.stderr)
        else:
            print(result)


if __name__ == "__main__":
    main()
