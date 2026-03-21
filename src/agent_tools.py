#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress Agent Tools - Agent 工具集
借鉴 lossless-claw 的 LCM Agent Tools

Author: LobsterPress Team
Version: v4.0.16
"""

import sys
import json
import argparse
from typing import List, Dict, Optional
from pathlib import Path

# 添加 database 模块
sys.path.insert(0, str(Path(__file__).parent))
from database import LobsterDatabase
from pipeline.tfidf_scorer import TFIDFScorer


# ==================== lobster_grep ====================

def lobster_grep(db: LobsterDatabase, 
                 query: str,
                 conversation_id: str = None,
                 search_messages: bool = True,
                 search_summaries: bool = True,
                 limit: int = 10,
                 use_tfidf_rerank: bool = True) -> List[Dict]:
    """搜索消息和摘要
    
    v2.5.0 更新：
    - 添加 TF-IDF 重排序
    - 结合 FTS5 rank 和 tfidf_score
    
    Args:
        db: LobsterDatabase 实例
        query: 搜索查询（支持正则）
        conversation_id: 对话 ID（None = 所有对话）
        search_messages: 是否搜索消息
        search_summaries: 是否搜索摘要
        limit: 最大结果数
        use_tfidf_rerank: 是否使用 TF-IDF 重排序
    
    Returns:
        搜索结果列表（按相关性排序）
    """
    results = []
    
    # v2.5.0: 初始化 TF-IDF 评分器
    scorer = TFIDFScorer() if use_tfidf_rerank else None

    # 缺陷 2 修复：计算查询的 TF 向量
    query_tokens = scorer.tokenize(query) if scorer else []

    # 搜索消息
    if search_messages:
        # v3.5.0: 直接在 SQL 中过滤 conversation_id（更高效）
        messages = db.search_messages(query, conversation_id=conversation_id, limit=limit * 2)

        for rank_pos, msg in enumerate(messages[:limit], 1):
            # 缺陷 2 修复：实际计算查询与结果的余弦相似度
            query_relevance = 0.0
            if scorer and query_tokens:
                content_tokens = scorer.tokenize(msg['content'])
                if content_tokens:
                    query_relevance = scorer._cosine_similarity(query_tokens, content_tokens)
            
            # v2.5.0: 结合 FTS5 rank、存储的 tfidf_score 和查询相关性
            # combined_score = 0.6 * tfidf_score + 0.4 * (1.0 / rank_position)
            # 缺陷 2 修复：增加查询相关性的权重
            stored_tfidf = msg.get('tfidf_score', 0.0)
            rank_score = 1.0 / rank_pos  # 审查修复：使用 rank_pos 而非 rank_position
            
            if use_tfidf_rerank:
                relevance = 0.4 * (stored_tfidf / 100.0) + 0.3 * rank_score + 0.3 * query_relevance
            else:
                relevance = rank_score
            
            results.append({
                'type': 'message',
                'id': msg['message_id'],
                'conversation_id': msg['conversation_id'],
                'role': msg.get('role', 'unknown'),
                'content': msg['content'][:200] + ('...' if len(msg['content']) > 200 else ''),
                'timestamp': msg.get('created_at', ''),
                'relevance': round(relevance, 3),
                'tfidf_score': round(stored_tfidf, 2),
                'query_relevance': round(query_relevance, 3),
                'msg_type': msg.get('msg_type', 'unknown')
            })
    
    # 搜索摘要
    if search_summaries:
        # v3.5.0: 直接在 SQL 中过滤 conversation_id（更高效）
        summaries = db.search_summaries(query, conversation_id=conversation_id, limit=limit * 2)

        for rank_pos, summary in enumerate(summaries[:limit], 1):
            # 缺陷 2 修复：计算查询与摘要的余弦相似度
            query_relevance = 0.0
            if scorer and query_tokens:
                content_tokens = scorer.tokenize(summary['content'])
                if content_tokens:
                    query_relevance = scorer._cosine_similarity(query_tokens, content_tokens)
            
            rank_score = 1.0 / rank_pos
            relevance = (0.7 * rank_score + 0.3 * query_relevance) if use_tfidf_rerank else rank_score
            
            results.append({
                'type': 'summary',
                'id': summary['summary_id'],
                'conversation_id': summary['conversation_id'],
                'kind': summary['kind'],
                'depth': summary['depth'],
                'content': summary['content'][:200] + ('...' if len(summary['content']) > 200 else ''),
                'descendant_count': summary.get('descendant_count', 0),
                'relevance': round(relevance, 3),
                'tfidf_score': 0.0,
                'query_relevance': round(query_relevance, 3),
                'msg_type': 'summary'
            })
    
    # v2.5.0: 按 TF-IDF 重排序
    if use_tfidf_rerank:
        results.sort(key=lambda x: x['relevance'], reverse=True)
    
    # v2.6.0: 触发记忆巩固（命中的消息重置衰减计数器）
    if results:
        for r in results:
            if r['type'] == 'message':
                db.touch_message(r['id'])
    
    # 限制总结果数
    return results[:limit]


# ==================== lobster_describe ====================

def lobster_describe(db: LobsterDatabase,
                     summary_id: str = None,
                     conversation_id: str = None,
                     depth: int = None) -> Optional[Dict]:
    """查看摘要详情
    
    借鉴 lossless-claw 的 lcm_describe：
    - 可以查看单个摘要的详情
    - 可以查看对话的摘要结构
    - 可以按深度过滤
    
    Args:
        db: LobsterDatabase 实例
        summary_id: 摘要 ID（查看单个摘要）
        conversation_id: 对话 ID（查看对话的摘要）
        depth: 深度过滤（None = 所有深度）
    
    Returns:
        摘要详情或摘要结构
    """
    if summary_id:
        # 查看单个摘要
        db.cursor.execute("""
            SELECT * FROM summaries WHERE summary_id = ?
        """, (summary_id,))
        
        row = db.cursor.fetchone()
        if not row:
            return None
        
        summary = db._row_to_dict(row, 'summaries')
        
        # 获取子节点信息
        if summary['kind'] == 'leaf':
            # 获取包含的消息
            db.cursor.execute("""
                SELECT m.* FROM messages m
                JOIN summary_messages sm ON m.message_id = sm.message_id
                WHERE sm.summary_id = ?
                ORDER BY m.seq ASC
            """, (summary_id,))
            
            messages = [db._row_to_dict(row, 'messages') for row in db.cursor.fetchall()]
            summary['messages'] = [
                {
                    'message_id': msg['message_id'],
                    'role': msg['role'],
                    'content': msg['content'][:100] + '...',
                    'timestamp': msg.get('created_at', '')
                }
                for msg in messages
            ]
        else:
            # 获取父摘要
            db.cursor.execute("""
                SELECT s.* FROM summaries s
                JOIN summary_parents sp ON s.summary_id = sp.parent_summary_id
                WHERE sp.summary_id = ?
                ORDER BY s.created_at ASC
            """, (summary_id,))
            
            parents = [db._row_to_dict(row, 'summaries') for row in db.cursor.fetchall()]
            summary['parent_summaries'] = [
                {
                    'summary_id': parent['summary_id'],
                    'kind': parent['kind'],
                    'depth': parent['depth'],
                    'descendant_count': parent.get('descendant_count', 0)
                }
                for parent in parents
            ]
        
        return summary
    
    elif conversation_id:
        # 查看对话的摘要结构
        summaries = db.get_summaries(conversation_id, depth)
        
        # 按 depth 分组
        by_depth = {}
        for summary in summaries:
            d = summary['depth']
            if d not in by_depth:
                by_depth[d] = []
            
            by_depth[d].append({
                'summary_id': summary['summary_id'],
                'kind': summary['kind'],
                'descendant_count': summary.get('descendant_count', 0),
                'earliest_at': summary.get('earliest_at', ''),
                'latest_at': summary.get('latest_at', '')
            })
        
        return {
            'conversation_id': conversation_id,
            'total_summaries': len(summaries),
            'max_depth': max(by_depth.keys()) if by_depth else 0,
            'by_depth': by_depth
        }
    
    return None


# ==================== lobster_expand ====================

def lobster_expand(db: LobsterDatabase,
                   summary_id: str,
                   max_depth: int = -1) -> Dict:
    """展开摘要到原始消息
    
    借鉴 lossless-claw 的 lcm_expand_query：
    - 递归展开摘要 DAG
    - 返回所有原始消息
    - 可以限制展开深度
    
    Args:
        db: LobsterDatabase 实例
        summary_id: 摘要 ID
        max_depth: 最大展开深度（-1 = 无限）
    
    Returns:
        展开结果（包含消息和统计）
    """
    messages = []
    visited = set()
    
    def expand_recursive(sid: str, current_depth: int):
        """递归展开摘要"""
        if sid in visited:
            return
        
        if max_depth != -1 and current_depth > max_depth:
            return
        
        visited.add(sid)
        
        # 获取摘要信息
        db.cursor.execute("""
            SELECT kind, depth FROM summaries WHERE summary_id = ?
        """, (sid,))
        
        row = db.cursor.fetchone()
        if not row:
            return
        
        kind, depth = row
        
        if kind == 'leaf':
            # 叶子摘要：获取消息
            db.cursor.execute("""
                SELECT m.* FROM messages m
                JOIN summary_messages sm ON m.message_id = sm.message_id
                WHERE sm.summary_id = ?
                ORDER BY m.seq ASC
            """, (sid,))
            
            for msg_row in db.cursor.fetchall():
                msg = db._row_to_dict(msg_row, 'messages')
                messages.append({
                    'message_id': msg['message_id'],
                    'role': msg['role'],
                    'content': msg['content'],
                    'timestamp': msg.get('created_at', ''),
                    'seq': msg.get('seq', 0)
                })
        else:
            # 压缩摘要：递归展开父摘要
            db.cursor.execute("""
                SELECT parent_summary_id FROM summary_parents
                WHERE summary_id = ?
                ORDER BY parent_summary_id ASC
            """, (sid,))
            
            for parent_row in db.cursor.fetchall():
                parent_id = parent_row[0]
                expand_recursive(parent_id, current_depth + 1)
    
    # 开始展开
    expand_recursive(summary_id, 0)
    
    # 按序号排序
    messages.sort(key=lambda m: m.get('seq', 0))
    
    return {
        'summary_id': summary_id,
        'total_messages': len(messages),
        'visited_summaries': len(visited),
        'messages': messages
    }


# ==================== CLI 接口 ====================

def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='LobsterPress Agent Tools')
    parser.add_argument('--db', default='lobster.db', help='数据库路径')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # lobster_grep
    grep_parser = subparsers.add_parser('grep', help='搜索消息和摘要')
    grep_parser.add_argument('query', help='搜索查询')
    grep_parser.add_argument('--conversation', help='对话 ID')
    grep_parser.add_argument('--no-messages', action='store_true', help='不搜索消息')
    grep_parser.add_argument('--no-summaries', action='store_true', help='不搜索摘要')
    grep_parser.add_argument('--limit', type=int, default=10, help='最大结果数')
    grep_parser.add_argument('--json', action='store_true', help='JSON 输出')
    
    # lobster_describe
    describe_parser = subparsers.add_parser('describe', help='查看摘要详情')
    describe_parser.add_argument('--summary', help='摘要 ID')
    describe_parser.add_argument('--conversation', help='对话 ID')
    describe_parser.add_argument('--depth', type=int, help='深度过滤')
    describe_parser.add_argument('--json', action='store_true', help='JSON 输出')
    
    # lobster_expand
    expand_parser = subparsers.add_parser('expand', help='展开摘要')
    expand_parser.add_argument('summary', help='摘要 ID')
    expand_parser.add_argument('--max-depth', type=int, default=-1, help='最大展开深度')
    expand_parser.add_argument('--json', action='store_true', help='JSON 输出')
    expand_parser.add_argument('--brief', action='store_true', help='简要输出')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 连接数据库
    db = LobsterDatabase(args.db)
    
    try:
        if args.command == 'grep':
            results = lobster_grep(
                db, args.query,
                conversation_id=args.conversation,
                search_messages=not args.no_messages,
                search_summaries=not args.no_summaries,
                limit=args.limit
            )
            
            if args.json:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                print(f"\n🔍 搜索结果: {len(results)} 项\n")
                for i, result in enumerate(results, 1):
                    print(f"{i}. [{result['type']}] {result['id']}")
                    if result['type'] == 'message':
                        print(f"   Role: {result['role']}")
                    else:
                        print(f"   Kind: {result['kind']} (depth={result['depth']})")
                    print(f"   {result['content']}")
                    print()
        
        elif args.command == 'describe':
            result = lobster_describe(
                db,
                summary_id=args.summary,
                conversation_id=args.conversation,
                depth=args.depth
            )
            
            if not result:
                print("❌ 未找到摘要")
                return
            
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                if args.summary:
                    # 单个摘要详情
                    print(f"\n📄 摘要: {result['summary_id']}\n")
                    print(f"  Kind: {result['kind']}")
                    print(f"  Depth: {result['depth']}")
                    print(f"  Messages: {result.get('descendant_count', 0)}")
                    print(f"  Content:\n{result['content']}\n")
                    
                    if result['kind'] == 'leaf':
                        print(f"  包含消息 ({len(result['messages'])} 条):")
                        for msg in result['messages'][:5]:
                            print(f"    - [{msg['role']}] {msg['content']}")
                        if len(result['messages']) > 5:
                            print(f"    ... 还有 {len(result['messages']) - 5} 条")
                    else:
                        print(f"  父摘要 ({len(result['parent_summaries'])} 个):")
                        for parent in result['parent_summaries']:
                            print(f"    - {parent['summary_id']}: {parent['kind']} (depth={parent['depth']})")
                else:
                    # 对话的摘要结构
                    print(f"\n📊 对话: {result['conversation_id']}\n")
                    print(f"  总摘要数: {result['total_summaries']}")
                    print(f"  最大深度: {result['max_depth']}\n")
                    
                    for depth in sorted(result['by_depth'].keys()):
                        summaries = result['by_depth'][depth]
                        print(f"  Depth {depth}: {len(summaries)} 个摘要")
                        for summary in summaries[:3]:
                            print(f"    - {summary['summary_id']}: {summary['kind']} ({summary['descendant_count']} msgs)")
                        if len(summaries) > 3:
                            print(f"    ... 还有 {len(summaries) - 3} 个")
                        print()
        
        elif args.command == 'expand':
            result = lobster_expand(
                db,
                summary_id=args.summary,
                max_depth=args.max_depth
            )
            
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            elif args.brief:
                print(f"\n✅ 展开摘要: {result['summary_id']}")
                print(f"  总消息数: {result['total_messages']}")
                print(f"  访问摘要: {result['visited_summaries']}\n")
            else:
                print(f"\n📤 展开摘要: {result['summary_id']}\n")
                print(f"  总消息数: {result['total_messages']}")
                print(f"  访问摘要: {result['visited_summaries']}\n")
                print("  消息:")
                for i, msg in enumerate(result['messages'][:10], 1):
                    content = msg['content'][:80] + ('...' if len(msg['content']) > 80 else '')
                    print(f"    {i}. [{msg['role']}] {content}")
                if len(result['messages']) > 10:
                    print(f"    ... 还有 {len(result['messages']) - 10} 条消息")
                print()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
