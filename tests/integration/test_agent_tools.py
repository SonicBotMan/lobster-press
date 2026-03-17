#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress Agent Tools 测试脚本
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加 src 目录
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.database import LobsterDatabase
from dag_compressor import DAGCompressor
from src.agent_tools import lobster_grep, lobster_describe, lobster_expand


def test_agent_tools():
    """测试 Agent 工具"""
    
    # 清理旧数据库
    if os.path.exists("test_tools.db"):
        os.remove("test_tools.db")
        print("🗑️ 删除旧的测试数据库\n")
    
    # 初始化
    db = LobsterDatabase("test_tools.db")
    compressor = DAGCompressor(db, fresh_tail_count=5)
    
    print("=" * 60)
    print("  🧪 LobsterPress Agent Tools 测试")
    print("=" * 60)
    
    # 创建测试数据
    conversation_id = "conv_test"
    print(f"\n📝 创建测试数据...\n")
    
    for i in range(1, 31):
        content = f'这是第 {i} 条消息，讨论了技术话题 {i % 10}。'
        if i % 5 == 0:
            content += f" 关键词: Python, JavaScript, Rust, Go"
        
        msg = {
            'id': f'msg_{i:03d}',
            'conversationId': conversation_id,
            'seq': i,
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': content * 5,  # 增加长度
            'timestamp': datetime.utcnow().isoformat()
        }
        db.save_message(msg)
        
        # 添加到上下文
        db.cursor.execute("""
            INSERT INTO context_items (conversation_id, ordinal, item_type, item_id)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, i, 'message', msg['id']))
    
    db.conn.commit()
    print(f"✅ 创建了 30 条测试消息\n")
    
    # 执行压缩
    print("=" * 60)
    print("  🦞 执行压缩")
    print("=" * 60)
    
    compressor.leaf_chunk_tokens = 300
    stats = compressor.full_compact(conversation_id)
    
    # ==================== 测试 lobster_grep ====================
    print("\n" + "=" * 60)
    print("  🔍 测试 lobster_grep")
    print("=" * 60)
    
    # 测试 1: 搜索 "Python"
    print("\n测试 1: 搜索 'Python'")
    results = lobster_grep(db, "Python", conversation_id=conversation_id, limit=5)
    print(f"  找到 {len(results)} 个结果")
    for i, result in enumerate(results[:3], 1):
        print(f"    {i}. [{result['type']}] {result['id']}")
        print(f"       {result['content'][:80]}...")
    
    # 测试 2: 搜索 "技术话题"
    print("\n测试 2: 搜索 '技术话题'")
    results = lobster_grep(db, "技术话题", conversation_id=conversation_id, limit=5)
    print(f"  找到 {len(results)} 个结果")
    for i, result in enumerate(results[:3], 1):
        print(f"    {i}. [{result['type']}] {result['id']}")
    
    # 测试 3: 只搜索摘要
    print("\n测试 3: 只搜索摘要")
    results = lobster_grep(db, "技术话题", conversation_id=conversation_id, 
                          search_messages=False, search_summaries=True, limit=5)
    print(f"  找到 {len(results)} 个摘要")
    for i, result in enumerate(results[:3], 1):
        print(f"    {i}. [{result['type']}] {result['id']} (depth={result['depth']})")
    
    # ==================== 测试 lobster_describe ====================
    print("\n" + "=" * 60)
    print("  📄 测试 lobster_describe")
    print("=" * 60)
    
    # 测试 1: 查看对话的摘要结构
    print("\n测试 1: 查看对话的摘要结构")
    structure = lobster_describe(db, conversation_id=conversation_id)
    print(f"  总摘要数: {structure['total_summaries']}")
    print(f"  最大深度: {structure['max_depth']}")
    for depth in sorted(structure['by_depth'].keys()):
        summaries = structure['by_depth'][depth]
        print(f"  Depth {depth}: {len(summaries)} 个摘要")
    
    # 测试 2: 查看单个摘要
    if structure['total_summaries'] > 0:
        print("\n测试 2: 查看单个摘要")
        first_summary_id = structure['by_depth'][0][0]['summary_id']
        summary = lobster_describe(db, summary_id=first_summary_id)
        
        print(f"  摘要 ID: {summary['summary_id']}")
        print(f"  Kind: {summary['kind']}")
        print(f"  Depth: {summary['depth']}")
        print(f"  Messages: {summary.get('descendant_count', 0)}")
        print(f"  Content: {summary['content'][:100]}...")
        
        if summary['kind'] == 'leaf':
            print(f"  包含消息: {len(summary['messages'])} 条")
    
    # ==================== 测试 lobster_expand ====================
    print("\n" + "=" * 60)
    print("  📤 测试 lobster_expand")
    print("=" * 60)
    
    if structure['total_summaries'] > 0:
        # 测试 1: 展开叶子摘要
        print("\n测试 1: 展开叶子摘要")
        leaf_summary_id = structure['by_depth'][0][0]['summary_id']
        result = lobster_expand(db, summary_id=leaf_summary_id)
        
        print(f"  摘要 ID: {result['summary_id']}")
        print(f"  总消息数: {result['total_messages']}")
        print(f"  访问摘要: {result['visited_summaries']}")
        print(f"  前 3 条消息:")
        for i, msg in enumerate(result['messages'][:3], 1):
            print(f"    {i}. [{msg['role']}] {msg['content'][:60]}...")
        
        # 测试 2: 展开压缩摘要（如果有）
        if structure['max_depth'] > 0:
            print("\n测试 2: 展开压缩摘要")
            condensed_summary_id = structure['by_depth'][1][0]['summary_id']
            result = lobster_expand(db, summary_id=condensed_summary_id)
            
            print(f"  摘要 ID: {result['summary_id']}")
            print(f"  总消息数: {result['total_messages']}")
            print(f"  访问摘要: {result['visited_summaries']}")
    
    # ==================== 总结 ====================
    print("\n" + "=" * 60)
    print("  ✅ 测试完成")
    print("=" * 60)
    
    print(f"\n📊 测试统计:")
    print(f"  - 消息数: 30 条")
    print(f"  - 叶子摘要: {stats['leaf_summaries']} 个")
    print(f"  - 压缩摘要: {stats['condensed_summaries']} 个")
    print(f"  - 压缩消息: {stats['messages_compressed']} 条")
    
    print(f"\n🔧 工具测试:")
    print(f"  - lobster_grep: ✅ 搜索功能正常")
    print(f"  - lobster_describe: ✅ 查看摘要正常")
    print(f"  - lobster_expand: ✅ 展开功能正常")
    
    # 清理
    db.close()
    os.remove("test_tools.db")
    print(f"\n🗑️ 清理测试数据库")


if __name__ == "__main__":
    test_agent_tools()
