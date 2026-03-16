#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v2.0 Demo - 无损记忆系统演示
基于 lossless-claw 经验优化

Author: LobsterPress Team
Version: v2.0.0-alpha
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import LobsterDatabase


def print_header(title: str):
    """打印标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_section(title: str):
    """打印小节"""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}\n")


def demo_basic_operations():
    """演示基础操作"""
    print_header("🦞 LobsterPress v2.0 - 无损记忆系统演示")
    
    print("📌 核心特性:")
    print("  ✅ 无损存储 - 所有消息永久保存")
    print("  ✅ DAG 结构 - 层次化摘要，可追溯")
    print("  ✅ 全文搜索 - FTS5 搜索引擎")
    print("  ✅ Agent 工具 - 搜索、描述、展开")
    print("  ✅ 增量压缩 - 智能触发，保护新鲜消息")
    
    # 初始化数据库
    db = LobsterDatabase("demo_lobster.db")
    print_section("1️⃣ 初始化数据库")
    print("✅ 数据库初始化成功")
    print(f"   数据库文件: demo_lobster.db")
    
    # 创建测试对话
    conversation_id = "conv_demo_001"
    print_section("2️⃣ 模拟对话")
    
    messages = [
        {
            'id': f'msg_{i:03d}',
            'conversationId': conversation_id,
            'seq': i,
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': [{'type': 'text', 'text': f'这是第 {i} 条消息，讨论了 {"Python 编程" if i < 5 else "机器学习" if i < 10 else "数据库优化"}'}],
            'timestamp': datetime.utcnow().isoformat()
        }
        for i in range(1, 16)
    ]
    
    print(f"📝 创建 {len(messages)} 条测试消息")
    for i, msg in enumerate(messages, 1):
        msg_id = db.save_message(msg)
        print(f"   {i}. {msg_id} - {msg['role']}: {msg['content'][0]['text'][:30]}...")
    
    # 搜索消息
    print_section("3️⃣ 全文搜索（借鉴 lcm_grep）")
    
    query = "Python"
    print(f"🔍 搜索关键词: '{query}'")
    results = db.search_messages(query)
    print(f"   找到 {len(results)} 条匹配消息:")
    for i, result in enumerate(results[:5], 1):
        print(f"   {i}. {result['message_id']}: {result['snippet'][:50]}...")
    
    # 创建叶子摘要
    print_section("4️⃣ 创建叶子摘要（DAG 结构）")
    
    leaf_summary = {
        'summary_id': 'sum_leaf_001',
        'conversation_id': conversation_id,
        'kind': 'leaf',
        'depth': 0,
        'content': '讨论了 Python 编程和机器学习的基础知识',
        'source_messages': [f'msg_{i:03d}' for i in range(1, 11)],
        'earliest_at': messages[0]['timestamp'],
        'latest_at': messages[9]['timestamp'],
        'descendant_count': 10
    }
    
    sum_id = db.save_summary(leaf_summary)
    print(f"✅ 创建叶子摘要: {sum_id}")
    print(f"   深度: 0 (leaf)")
    print(f"   包含消息: 10 条")
    print(f"   内容: {leaf_summary['content']}")
    
    # 创建压缩摘要
    print_section("5️⃣ 创建压缩摘要（DAG 层次）")
    
    condensed_summary = {
        'summary_id': 'sum_condensed_001',
        'conversation_id': conversation_id,
        'kind': 'condensed',
        'depth': 1,
        'content': '技术讨论会话：涵盖编程、AI 和数据库优化',
        'parent_summaries': ['sum_leaf_001'],
        'earliest_at': messages[0]['timestamp'],
        'latest_at': messages[-1]['timestamp'],
        'descendant_count': 15
    }
    
    sum_id = db.save_summary(condensed_summary)
    print(f"✅ 创建压缩摘要: {sum_id}")
    print(f"   深度: 1 (condensed)")
    print(f"   父摘要: 1 个")
    print(f"   内容: {condensed_summary['content']}")
    
    # 描述摘要
    print_section("6️⃣ 查看摘要详情（借鉴 lcm_describe）")
    
    summary = db.describe_summary('sum_condensed_001')
    print(f"📄 摘要 ID: {summary['summary_id']}")
    print(f"   类型: {summary['kind']}")
    print(f"   深度: {summary['depth']}")
    print(f"   内容: {summary['content']}")
    print(f"   子节点数: {summary['children_count']}")
    print(f"   创建时间: {summary['created_at']}")
    
    # 展开摘要
    print_section("7️⃣ 展开摘要（借鉴 lcm_expand）")
    
    print(f"🔄 展开摘要: sum_condensed_001")
    all_messages = db.expand_summary('sum_condensed_001')
    print(f"✅ 展开完成: 恢复了 {len(all_messages)} 条原始消息")
    print(f"   前 3 条消息:")
    for i, msg in enumerate(all_messages[:3], 1):
        print(f"   {i}. {msg['message_id']}: {msg['content'][:40]}...")
    
    # 统计信息
    print_section("8️⃣ 数据库统计")
    
    import sqlite3
    conn = sqlite3.connect("demo_lobster.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    msg_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM summaries")
    sum_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversations")
    conv_count = cursor.fetchone()[0]
    
    print(f"📊 数据库统计:")
    print(f"   对话数: {conv_count}")
    print(f"   消息数: {msg_count}")
    print(f"   摘要数: {sum_count}")
    print(f"   数据库大小: {Path('demo_lobster.db').stat().st_size / 1024:.2f} KB")
    
    conn.close()
    
    # 清理
    print_section("9️⃣ 清理演示")
    db.close()
    print("✅ 数据库连接已关闭")
    
    import os
    os.remove("demo_lobster.db")
    print("✅ 演示数据库已清理")
    
    # 总结
    print_header("🎉 演示完成")
    
    print("✨ 核心改进:")
    print("  1. ✅ 无损存储 - 所有消息永久保存到 SQLite")
    print("  2. ✅ DAG 结构 - 叶子摘要 + 压缩摘要，层次化")
    print("  3. ✅ 全文搜索 - FTS5 搜索，快速查找")
    print("  4. ✅ Agent 工具 - 搜索、描述、展开")
    print("  5. ✅ 可追溯性 - 展开摘要恢复原始消息")
    
    print("\n🚀 下一步:")
    print("  - Phase 1: 完善数据库层（进行中）")
    print("  - Phase 2: 实现 DAG 压缩逻辑")
    print("  - Phase 3: 集成 Agent 工具")
    print("  - Phase 4: 增量压缩和智能触发")
    
    print("\n📚 参考文档:")
    print("  - docs/OPTIMIZATION-PROPOSAL.md - 优化提案")
    print("  - src/database.py - 数据库实现")
    print("  - lossless-claw: https://github.com/Martian-Engineering/lossless-claw")


if __name__ == "__main__":
    try:
        demo_basic_operations()
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
