#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v2.5.0 BatchImporter

批量导入 v1.5.5 数据到 v2.0.0 数据库

功能：
1. 支持 JSON 格式导入
2. 自动评分和打标签（TF-IDF）
3. 批量导入多个对话
4. 进度反馈
5. 错误处理

Author: LobsterPress Team
Version: v2.5.0
"""

import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Iterator

# 添加 src 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import LobsterDatabase
from pipeline.tfidf_scorer import TFIDFScorer, ScoredMessage


class BatchImporter:
    """批量导入器 - v1.5.5 → v2.0.0"""
    
    def __init__(self, db_path: str):
        """
        初始化批量导入器
        
        Args:
            db_path: 数据库路径
        """
        self.db = LobsterDatabase(db_path)
        self.scorer = TFIDFScorer()
        
        # 统计信息
        self.stats = {
            'total_conversations': 0,
            'total_messages': 0,
            'imported_messages': 0,
            'skipped_messages': 0,
            'errors': []
        }
    
    def import_from_json(
        self,
        json_path: str,
        conversation_id_field: str = 'conversationId',
        messages_field: str = 'messages',
        batch_size: int = 100
    ) -> Dict:
        """
        从 JSON 文件导入数据
        
        Args:
            json_path: JSON 文件路径
            conversation_id_field: 对话 ID 字段名
            messages_field: 消息列表字段名
            batch_size: 批量导入大小
        
        Returns:
            导入统计信息
        """
        print(f"\n📦 开始导入 JSON: {json_path}")
        
        # 读取 JSON 文件
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 处理数据格式
        if isinstance(data, list):
            # 列表格式：多个对话
            conversations = data
        elif isinstance(data, dict):
            # 字典格式：单个对话或嵌套格式
            if messages_field in data:
                conversations = [data]
            elif conversation_id_field in data:
                conversations = [data]
            else:
                # 尝试提取所有对话
                conversations = list(data.values())
        else:
            raise ValueError(f"不支持的 JSON 格式: {type(data)}")
        
        # 导入所有对话
        return self._import_conversations(
            conversations,
            conversation_id_field,
            messages_field,
            batch_size
        )
    
    def import_from_csv(
        self,
        csv_path: str,
        conversation_id_field: str = 'conversation_id',
        content_field: str = 'content',
        role_field: str = 'role',
        timestamp_field: str = 'timestamp',
        batch_size: int = 100
    ) -> Dict:
        """
        从 CSV 文件导入数据
        
        Args:
            csv_path: CSV 文件路径
            conversation_id_field: 对话 ID 字段名
            content_field: 内容字段名
            role_field: 角色字段名
            timestamp_field: 时间戳字段名
            batch_size: 批量导入大小
        
        Returns:
            导入统计信息
        """
        print(f"\n📦 开始导入 CSV: {csv_path}")
        
        # 读取 CSV 文件
        messages = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                messages.append({
                    'conversationId': row.get(conversation_id_field, 'default'),
                    'content': row.get(content_field, ''),
                    'role': row.get(role_field, 'user'),
                    'timestamp': row.get(timestamp_field, datetime.utcnow().isoformat())
                })
        
        # 按 conversation_id 分组
        conversations_dict = {}
        for msg in messages:
            conv_id = msg['conversationId']
            if conv_id not in conversations_dict:
                conversations_dict[conv_id] = []
            conversations_dict[conv_id].append(msg)
        
        # 转换为列表格式
        conversations = [
            {
                'conversationId': conv_id,
                'messages': msgs
            }
            for conv_id, msgs in conversations_dict.items()
        ]
        
        # 导入所有对话
        return self._import_conversations(
            conversations,
            'conversationId',
            'messages',
            batch_size
        )
    
    def _import_conversations(
        self,
        conversations: List[Dict],
        conversation_id_field: str,
        messages_field: str,
        batch_size: int
    ) -> Dict:
        """
        导入对话列表
        
        Args:
            conversations: 对话列表
            conversation_id_field: 对话 ID 字段名
            messages_field: 消息列表字段名
            batch_size: 批量导入大小
        
        Returns:
            导入统计信息
        """
        self.stats['total_conversations'] = len(conversations)
        
        print(f"  发现 {len(conversations)} 个对话")
        
        for i, conv in enumerate(conversations):
            try:
                # 提取对话 ID
                conversation_id = conv.get(conversation_id_field, f'conv_{i}')
                
                # 提取消息列表
                messages = conv.get(messages_field, [])
                
                if not messages:
                    print(f"  ⚠️  对话 {conversation_id} 没有消息，跳过")
                    continue
                
                # 导入消息
                self._import_messages(conversation_id, messages, batch_size)
                
                print(f"  ✅ 对话 {conversation_id}: {len(messages)} 条消息")
                
            except Exception as e:
                error_msg = f"对话 {i} 导入失败: {str(e)}"
                self.stats['errors'].append(error_msg)
                print(f"  ❌ {error_msg}")
        
        # 打印统计信息
        self._print_stats()
        
        return self.stats
    
    def _import_messages(
        self,
        conversation_id: str,
        messages: List[Dict],
        batch_size: int
    ):
        """
        导入消息列表
        
        Args:
            conversation_id: 对话 ID
            messages: 消息列表
            batch_size: 批量导入大小
        """
        self.stats['total_messages'] += len(messages)
        
        # 批量评分
        scored_messages = self.scorer.score_and_tag(messages)
        
        # 批量导入
        for i in range(0, len(scored_messages), batch_size):
            batch = scored_messages[i:i + batch_size]
            
            for scored_msg in batch:
                try:
                    # 转换为数据库格式
                    msg_data = {
                        'id': scored_msg.id,
                        'conversationId': conversation_id,
                        'seq': messages[i].get('seq', i + 1),
                        'role': scored_msg.role,
                        'content': scored_msg.content,
                        'timestamp': scored_msg.timestamp,
                        'msg_type': scored_msg.msg_type,
                        'tfidf_score': scored_msg.tfidf_score,
                        'structural_bonus': scored_msg.structural_bonus,
                        'compression_exempt': scored_msg.compression_exempt
                    }
                    
                    # 保存到数据库
                    self.db.save_message(msg_data)
                    self.stats['imported_messages'] += 1
                    
                except Exception as e:
                    self.stats['skipped_messages'] += 1
                    error_msg = f"消息 {scored_msg.id} 保存失败: {str(e)}"
                    self.stats['errors'].append(error_msg)
    
    def _print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("  📊 导入统计")
        print("=" * 60)
        print(f"  对话总数: {self.stats['total_conversations']}")
        print(f"  消息总数: {self.stats['total_messages']}")
        print(f"  导入成功: {self.stats['imported_messages']}")
        print(f"  跳过消息: {self.stats['skipped_messages']}")
        
        if self.stats['errors']:
            print(f"\n  ❌ 错误 ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # 只显示前5个错误
                print(f"    - {error}")
            if len(self.stats['errors']) > 5:
                print(f"    ... 还有 {len(self.stats['errors']) - 5} 个错误")
        
        print("=" * 60)
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='LobsterPress v2.5.0 BatchImporter'
    )
    parser.add_argument(
        'input_file',
        help='输入文件路径（JSON 或 CSV）'
    )
    parser.add_argument(
        '--db',
        default='lobster_press.db',
        help='数据库路径（默认: lobster_press.db）'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'csv'],
        help='输入文件格式（自动检测）'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='批量导入大小（默认: 100）'
    )
    
    args = parser.parse_args()
    
    # 创建导入器
    importer = BatchImporter(args.db)
    
    try:
        # 检测文件格式
        if args.format:
            file_format = args.format
        else:
            file_format = 'json' if args.input_file.endswith('.json') else 'csv'
        
        # 导入数据
        if file_format == 'json':
            stats = importer.import_from_json(
                args.input_file,
                batch_size=args.batch_size
            )
        else:
            stats = importer.import_from_csv(
                args.input_file,
                batch_size=args.batch_size
            )
        
        # 返回退出码
        sys.exit(0 if not stats['errors'] else 1)
        
    finally:
        importer.close()


if __name__ == '__main__':
    main()
