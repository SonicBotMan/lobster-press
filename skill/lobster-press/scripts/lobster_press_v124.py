#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v1.2.4-hotfix5 - Issue #60 完整修复

修复内容:
1. Bug 1 (高危): kept_older + other_lines 索引空间冲突
2. Bug 2 (中危): 版本号 hotfix3 → hotfix5
3. Logic 1 (中危): parser 命名冲突
4. Logic 2 (中危): 评分逻辑偏差
5. 建议 (低危): --recent-window 边界校验
6. [PR fix] summary_index 使用实际最大索引+1，修复空行场景下的位置错乱
7. [PR fix] 删除 _generate_summary 中未使用的 decisions 死代码
8. [PR fix] --backup 静默忽略时添加 stderr 警告
9. [PR fix] content_preserved 统计移至 drop 操作后，反映实际保留量

Author: LobsterPress Team
Version: v1.2.4-hotfix5
"""

import sys
import json
import argparse
import hashlib
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import re


# Bug 2 修复：统一版本常量
VERSION = "v1.2.4-hotfix5"


@dataclass
class CompressionStats:
    """压缩统计"""
    original_lines: int = 0
    original_bytes: int = 0
    compressed_lines: int = 0
    compressed_bytes: int = 0
    messages_removed: int = 0
    content_preserved: Dict[str, int] = field(default_factory=dict)
    
    @property
    def compression_ratio(self) -> float:
        """压缩率"""
        if self.original_bytes == 0:
            return 0.0
        return 1 - (self.compressed_bytes / self.original_bytes)


class OpenClawSessionParser:
    """OpenClaw 会话解析器
    
    Bug 1 修复：为所有行记录原始索引
    """
    
    def __init__(self):
        self.lines: List[Dict] = []
        self.header: Optional[Dict] = None
        self.messages: List[Tuple[int, Dict]] = []  # (原始索引, 消息)
        self.other_lines: List[Tuple[int, Dict]] = []  # (原始索引, 行数据)
    
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
                # 识别消息（Bug 1 修复：记录原始索引）
                elif obj.get('type') == 'message':
                    self.messages.append((i, obj))
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
                # Logic 2 修复：记录完整长度，而非截断后的长度
                result = item.get('content', '')
                texts.append(f"[Result: {result}]")  # 保留完整内容用于评分
        
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
    """LobsterPress v1.2.4 压缩引擎
    
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
        
        Logic 2 修复：调整评分权重，避免工具调用优先级过高
        
        Args:
            msg: 消息对象
            parser: 解析器
        
        Returns:
            重要性分数 (0-1)
        """
        score = 0.5  # 基础分
        
        # 角色权重（调整：user 权重提高）
        role = msg.get('message', {}).get('role', '')
        if role == 'user':
            score += 0.25  # 提高 user 权重（原 0.2）
        elif role == 'assistant':
            score += 0.1
        
        # 内容分析
        has_tool_call = False
        has_thinking = False
        text_len = 0
        
        for item in parser.get_message_content(msg):
            if item.get('type') == 'toolCall':
                has_tool_call = True
            elif item.get('type') == 'thinking':
                has_thinking = True
            elif item.get('type') == 'text':
                text_len += len(item.get('text', ''))
            elif item.get('type') == 'toolResult':
                # Logic 2 修复：使用完整长度，而非截断后的长度
                text_len += len(item.get('content', ''))
        
        # 工具调用权重（降低）
        if has_tool_call:
            score += 0.1  # 降低权重（原 0.15）
        if has_thinking:
            score += 0.1
        
        # 文本长度判断
        if 100 < text_len < 1000:
            score += 0.1
        elif text_len >= 1000:
            score -= 0.05  # 过长可能冗余
        
        return min(1.0, score)
    
    def _generate_summary(self, messages: List[Dict], parser: OpenClawSessionParser) -> str:
        """生成消息摘要
        
        Args:
            messages: 要压缩的消息列表
            parser: 解析器
        
        Returns:
            摘要文本
        """
        if not messages:
            return ""
        
        # 提取关键信息
        # PR fix: 移除从未使用的 decisions 死代码变量
        topics = []
        
        for msg in messages:
            text = parser.get_text_content(msg)
            role = msg.get('message', {}).get('role', '')
            
            # 简单摘要：提取前 100 字符
            if len(text) > 100:
                text = text[:100] + '...'
            
            topics.append(f"[{role}] {text}")
        
        summary = f"压缩了 {len(messages)} 条消息:\n" + '\n'.join(topics[:5])
        
        if len(summary) > self.max_summary_chars:
            summary = summary[:self.max_summary_chars] + '...'
        
        return summary
    
    def _create_summary_message(self, summary: str, strategy: str) -> Dict:
        """创建摘要消息
        
        Bug 3 修复：只调用一次 datetime.now()
        Bug 2 修复：使用 VERSION 常量
        
        Args:
            summary: 摘要文本
            strategy: 压缩策略
        
        Returns:
            摘要消息对象
        """
        # Bug 3 修复：只调用一次 datetime.now()
        now = datetime.now()
        timestamp = now.isoformat()
        msg_id = f"compress-{int(now.timestamp())}"
        
        return {
            "type": "message",
            "id": msg_id,
            "parentId": None,
            "timestamp": timestamp,
            "message": {
                "role": "assistant",
                "content": [{
                    "type": "text",
                    "text": f"[历史摘要 - {strategy} - {VERSION}]\n{summary}"  # Bug 2 修复
                }],
                "api": "openai-responses",
                "provider": "openclaw",
                "model": "lobster-press-v124",
                "timestamp": int(now.timestamp() * 1000)
            }
        }
    
    def compress(self, content: str) -> Tuple[str, CompressionStats]:
        """压缩 JSONL 会话
        
        Bug 1 修复：使用原始索引，避免索引空间冲突
        PR fix：summary_index 使用已有索引最大值+1，而非 len(parser.lines)+1
        PR fix：content_preserved 统计移至 drop 操作后，反映实际保留量
        
        Args:
            content: JSONL 文件内容
        
        Returns:
            (压缩后的 JSONL 内容, 统计信息)
        """
        parser = OpenClawSessionParser()
        parser.parse_jsonl(content)
        
        self.stats.original_lines = len(parser.lines)
        self.stats.original_bytes = len(content.encode('utf-8'))
        
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
        
        # Bug 1 修复：评分历史消息时保留原始索引
        older_messages = parser.messages[:older_count]  # [(idx, msg), ...]
        scored = [(idx, msg, self._score_message(msg, parser)) for idx, msg in older_messages]
        scored.sort(key=lambda x: x[2], reverse=True)
        
        # 选择要保留的历史消息（Bug 1 修复：保留原始索引）
        kept_older = [(idx, msg) for idx, msg, score in scored[:keep_from_older]]
        
        # 要压缩的消息
        dropped_indices = set(idx for idx, msg, score in scored[keep_from_older:])
        dropped_messages = [msg for idx, msg in older_messages if idx in dropped_indices]
        
        # 生成摘要
        summary = self._generate_summary(dropped_messages, parser)
        
        # PR fix：content_preserved 统计实际保留的消息内容类型（drop 操作后）
        kept_recent = parser.messages[-recent_count:]
        for idx, msg in kept_older:
            for item in parser.get_message_content(msg):
                ct = item.get('type', 'unknown')
                self.stats.content_preserved[ct] = self.stats.content_preserved.get(ct, 0) + 1
        for idx, msg in kept_recent:
            for item in parser.get_message_content(msg):
                ct = item.get('type', 'unknown')
                self.stats.content_preserved[ct] = self.stats.content_preserved.get(ct, 0) + 1
        
        # PR fix：Bug 1 修复不完整 — summary_index 使用已有索引最大值+1，而非 len(parser.lines)+1
        # 原代码：summary_index = len(parser.lines) + 1
        # 问题：parse_jsonl 跳过空行，len(parser.lines) 与实际最大原始行索引 i 不等
        # 修复：取所有已记录索引的最大值，确保 summary_index 不与任何现有索引冲突
        all_existing_indices = (
            ([0] if parser.header else []) +
            [idx for idx, _ in parser.other_lines] +
            [idx for idx, _ in parser.messages]
        )
        max_existing_index = max(all_existing_indices) if all_existing_indices else 0
        
        # Bug 1 修复：构建输出时使用原始索引
        all_indexed_lines = []
        
        # 1. 添加 header（如果有）
        if parser.header:
            all_indexed_lines.append((0, parser.header))
        
        # 2. 添加 other_lines（已有原始索引）
        all_indexed_lines.extend(parser.other_lines)
        
        # 3. 添加摘要消息（分配新索引，放在所有消息之后）
        if summary:
            summary_index = max_existing_index + 1  # PR fix：使用实际最大索引+1
            summary_msg = self._create_summary_message(summary, self.strategy)
            all_indexed_lines.append((summary_index, summary_msg))
        
        # 4. 添加保留的历史消息（使用原始索引）
        all_indexed_lines.extend(kept_older)
        
        # 5. 添加最近的完整消息（使用原始索引）
        all_indexed_lines.extend(kept_recent)
        
        # 按原始索引排序并输出
        all_indexed_lines.sort(key=lambda x: x[0])
        output_lines = []
        for _, line in all_indexed_lines:
            output_lines.append(json.dumps(line, ensure_ascii=False))
        
        # 构建输出
        result = '\n'.join(output_lines) + '\n'
        
        # 更新统计
        self.stats.compressed_lines = len(output_lines)
        self.stats.compressed_bytes = len(result.encode('utf-8'))
        self.stats.messages_removed = len(dropped_messages)
        
        return result, self.stats
    
    def get_report(self) -> str:
        """生成压缩报告
        
        Bug 2 修复：使用 VERSION 常量
        
        Returns:
            报告文本
        """
        lines = [
            f"📊 LobsterPress {VERSION} 压缩报告",  # Bug 2 修复
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
    """命令行入口
    
    Logic 1 修复：重命名 argparse parser 为 arg_parser
    """
    # Logic 1 修复：重命名以避免冲突
    arg_parser = argparse.ArgumentParser(
        description=f"LobsterPress {VERSION} - OpenClaw 兼容的压缩引擎",  # Bug 2 修复
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
    arg_parser.add_argument("--backup", 
                       action="store_true",
                       default=False,
                       help="备份原始输入文件（仅当原地压缩时有效，default: False)")
    
    args = arg_parser.parse_args()  # Logic 1 修复
    
    # Bug 5 修复：--recent-window 边界校验
    if args.recent_window < 1:
        print("❌ --recent-window 必须 >= 1", file=sys.stderr)
        sys.exit(1)
    
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
        # Bug E 修复：防止 KeyError
        keep_rate = CompressionStrategy.KEEP_RATES.get(args.strategy, 0.70)
        print(f"  预计保留率: {keep_rate:.0%}")
        
        # Logic 1 修复：重命名以避免冲突
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
            # 备份
            if args.backup and args.output == args.input_file:
                # Bug 6 修复：仅当原地压缩时才备份
                backup_file = f"{args.input_file}.backup.{int(datetime.now().timestamp())}"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"📦 已备份: {backup_file}", file=sys.stderr)
            elif args.backup and args.output != args.input_file:
                # PR fix：--backup 在非原地压缩时被忽略，给出明确提示
                print(f"⚠️ --backup 仅在原地压缩（-o 与输入文件相同）时有效，本次已忽略", file=sys.stderr)
            
            # 写入
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"✅ 已写入 {args.output}", file=sys.stderr)
            print(f"📊 压缩率: {stats.compression_ratio:.1%}", file=sys.stderr)
        else:
            print(result)


if __name__ == "__main__":
    main()
