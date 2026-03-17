#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3.0.0 验收测试 - Feature 3 & Feature 4
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import LobsterDatabase
from semantic_memory import SemanticMemory


class MockLLMClient:
    """模拟 LLM 客户端"""
    
    def complete(self, prompt: str, max_tokens: int = 500) -> str:
        if 'PostgreSQL' in prompt or '数据库' in prompt:
            return '[{"category": "decision", "content": "项目采用 PostgreSQL"}]'
        return '[]'


def test_notes_extraction():
    """测试 1: notes 提取"""
    print("\n测试 1: notes 提取...")
    
    db_path = '/tmp/test_v300_1.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = LobsterDatabase(db_path)
    sem_mem = SemanticMemory(db)
    
    messages = [
        {'id': 'm1', 'role': 'user', 'content': '我们决定用 PostgreSQL'},
        {'id': 'm2', 'role': 'assistant', 'content': '好的'}
    ]
    
    note_ids = sem_mem.extract_and_store(
        conversation_id='test_conv',
        messages=messages,
        llm_client=MockLLMClient(),
        source_msg_ids=['m1', 'm2']
    )
    
    notes = sem_mem.get_active_notes('test_conv')
    assert len(notes) > 0, "应该提取到 notes"
    
    os.remove(db_path)
    print("✅ 测试 1 通过")


def test_notes_injection():
    """测试 2: notes 注入上下文"""
    print("\n测试 2: notes 注入...")
    
    db_path = '/tmp/test_v300_2.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = LobsterDatabase(db_path)
    sem_mem = SemanticMemory(db)
    
    sem_mem._save_note(
        conversation_id='test_conv',
        category='decision',
        content='项目采用 React 18'
    )
    
    notes = sem_mem.get_active_notes('test_conv')
    text = sem_mem.format_for_context(notes)
    
    assert '[背景知识]' in text, "应该包含背景知识标签"
    assert 'React 18' in text, "应该包含 React 18"
    
    os.remove(db_path)
    print("✅ 测试 2 通过")


def test_conflict_api():
    """测试 3: 矛盾检测 API 可用性"""
    print("\n测试 3: 矛盾检测 API...")
    
    from pipeline.conflict_detector import ConflictDetector
    
    detector = ConflictDetector(use_nli=False)
    
    # 验证 API 可用
    assert hasattr(detector, 'detect'), "应该有 detect 方法"
    assert hasattr(detector, 'reconcile'), "应该有 reconcile 方法"
    
    # 简单功能测试
    new_msg = {'id': 'm1', 'content': '测试消息', 'role': 'user'}
    conflicts = detector.detect(new_msg, [])
    
    assert conflicts == [], "空 notes 应该返回空冲突列表"
    
    print("✅ 测试 3 通过")


def test_notes_dedup():
    """测试 4: note 去重"""
    print("\n测试 4: note 去重...")
    
    db_path = '/tmp/test_v300_4.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = LobsterDatabase(db_path)
    sem_mem = SemanticMemory(db)
    
    # 第一次插入
    id1 = sem_mem._save_note(
        conversation_id='test_conv',
        category='decision',
        content='项目采用 Python 3.11'
    )
    
    assert id1 is not None, "第一次应该成功"
    
    # 第二次插入相同内容
    id2 = sem_mem._save_note(
        conversation_id='test_conv',
        category='decision',
        content='项目采用 Python 3.11'
    )
    
    assert id2 is None, "第二次应该被去重"
    
    notes = sem_mem.get_active_notes('test_conv')
    assert len(notes) == 1, "应该只有一条 note"
    
    os.remove(db_path)
    print("✅ 测试 4 通过")


if __name__ == '__main__':
    print("=" * 60)
    print("  v3.0.0 验收测试")
    print("=" * 60)
    
    try:
        test_notes_extraction()
        test_notes_injection()
        test_conflict_api()
        test_notes_dedup()
        
        print("\n" + "=" * 60)
        print("  ✅ 所有测试通过！")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
