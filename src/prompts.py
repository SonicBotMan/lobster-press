#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress Prompt Templates - Prompt 模板库

集中管理所有 LLM prompt，便于优化和维护。

Author: LobsterPress Team
Version: v4.0.12
"""

from typing import List, Dict


# ==================== 叶子摘要 Prompt ====================

LEAF_SUMMARY_PROMPT = """你是一个专业的对话摘要助手。请总结以下对话片段的核心内容。

## 要求
1. **提取关键决策**：技术选型、架构决策、重要结论
2. **保留技术细节**：配置参数、API 端点、版本号、命令
3. **识别行动项**：待办事项、后续任务
4. **简洁明了**：不超过 300 字，使用要点列表

## 输出格式
```markdown
## 对话摘要

### 关键决策
- [决策1]
- [决策2]

### 技术细节
- [细节1]
- [细节2]

### 行动项
- [ ] [任务1]
- [ ] [任务2]
```

## 对话内容
{conversation_text}

## 摘要
"""

# ==================== 压缩摘要 Prompt ====================

CONDENSED_SUMMARY_PROMPT = """你是一个专业的对话压缩助手。请将以下多个摘要合并为一个更高层次的摘要。

## 要求
1. **去重**：合并重复信息
2. **提炼**：提取跨摘要的共同主题
3. **压缩**：保留最重要的信息
4. **结构化**：使用清晰的层次结构

## 输出格式
```markdown
## 压缩摘要（Level {depth}）

### 核心主题
- [主题1]
- [主题2]

### 关键决策
- [决策1]
- [决策2]

### 重要细节
- [细节1]
- [细节2]
```

## 输入摘要
{combined_content}

## 压缩摘要
"""

# ==================== Note 提取 Prompt ====================

NOTE_EXTRACTION_PROMPT = """你是一个知识提取助手。请从以下对话片段中提取「稳定的语义知识」。

## 要求
1. **只提取明确陈述的事实**：不要推断或假设
2. **去重**：避免提取已存在的知识
3. **具体化**：使用具体的值而非模糊描述
4. **稳定性**：提取长期有效的知识，而非临时状态

## 类别说明
- **preference**：用户/项目偏好（如"用户偏好 PostgreSQL"）
- **decision**：技术选型、架构决策（如"项目采用 React 18"）
- **constraint**：硬性约束、限制条件（如"部署环境必须为 AWS"）
- **fact**：客观事实（如"API 版本为 v2.1.0"）

## 输出格式（JSON 数组）
```json
[
  {{"category": "preference", "content": "用户偏好使用 PostgreSQL 作为主数据库"}},
  {{"category": "decision", "content": "项目采用 React 18 + TypeScript 技术栈"}},
  {{"category": "constraint", "content": "部署环境限制为 AWS，不能使用 GCP"}},
  {{"category": "fact", "content": "PostgreSQL 版本为 15.2"}}
]
```

**注意**：
- 如果没有稳定知识，返回空数组 `[]`
- 每个类别可以有多个条目
- content 应该是完整的句子，包含必要的上下文

## 对话片段
{context}

## 提取结果（JSON）
"""

# ==================== 矛盾检测 Prompt（可选） ====================

CONFLICT_DETECTION_PROMPT = """你是一个矛盾检测助手。请判断以下两个陈述是否存在矛盾。

## 陈述1
{statement1}

## 陈述2
{statement2}

## 要求
1. **语义理解**：理解两个陈述的实际含义
2. **矛盾判定**：判断是否存在逻辑矛盾
3. **置信度**：给出 0-1 之间的置信度分数

## 输出格式（JSON）
```json
{{
  "has_conflict": true,
  "confidence": 0.95,
  "reason": "陈述1说使用 PostgreSQL，陈述2说使用 MySQL，存在直接矛盾"
}}
```

## 判定结果（JSON）
"""

# ==================== Prompt 构建函数 ====================

def build_leaf_summary_prompt(messages: List[Dict]) -> str:
    """构建叶子摘要 prompt
    
    Args:
        messages: 消息列表
    
    Returns:
        格式化后的 prompt
    """
    conversation_text = '\n\n'.join([
        f"**[{m.get('role', 'unknown').upper()}]**: {m.get('content', '')}"
        for m in messages
    ])
    
    return LEAF_SUMMARY_PROMPT.format(conversation_text=conversation_text)


def build_condensed_summary_prompt(combined_content: str, depth: int) -> str:
    """构建压缩摘要 prompt
    
    Args:
        combined_content: 合并后的内容
        depth: 压缩深度
    
    Returns:
        格式化后的 prompt
    """
    return CONDENSED_SUMMARY_PROMPT.format(
        combined_content=combined_content,
        depth=depth
    )


def build_note_extraction_prompt(messages: List[Dict]) -> str:
    """构建 note 提取 prompt
    
    Args:
        messages: 消息列表
    
    Returns:
        格式化后的 prompt
    """
    context = '\n\n'.join([
        f"[{m.get('role', 'unknown')}]: {m.get('content', '')}"
        for m in messages
    ])
    
    return NOTE_EXTRACTION_PROMPT.format(context=context)


def build_conflict_detection_prompt(statement1: str, statement2: str) -> str:
    """构建矛盾检测 prompt
    
    Args:
        statement1: 陈述1
        statement2: 陈述2
    
    Returns:
        格式化后的 prompt
    """
    return CONFLICT_DETECTION_PROMPT.format(
        statement1=statement1,
        statement2=statement2
    )


# ==================== Prompt 优化工具 ====================

def estimate_tokens(text: str) -> int:
    """估算文本的 token 数（粗略估计：1 token ≈ 4 字符）
    
    Args:
        text: 文本
    
    Returns:
        估算的 token 数
    """
    return len(text) // 4


def truncate_messages(messages: List[Dict], max_tokens: int = 20000) -> List[Dict]:
    """截断消息列表以适应 token 限制
    
    Args:
        messages: 消息列表
        max_tokens: 最大 token 数
    
    Returns:
        截断后的消息列表
    """
    result = []
    total_tokens = 0
    
    for msg in reversed(messages):  # 从最新的消息开始
        content = msg.get('content', '')
        msg_tokens = estimate_tokens(content)
        
        if total_tokens + msg_tokens <= max_tokens:
            result.insert(0, msg)
            total_tokens += msg_tokens
        else:
            break
    
    return result


# ==================== 示例和测试 ====================

if __name__ == '__main__':
    # 测试 prompt 构建
    test_messages = [
        {'role': 'user', 'content': '我们决定使用 PostgreSQL'},
        {'role': 'assistant', 'content': '好的，PostgreSQL 是个好选择'},
        {'role': 'user', 'content': '版本是 15.2'},
        {'role': 'assistant', 'content': '已记录，PostgreSQL 15.2'},
    ]
    
    print("=" * 60)
    print("叶子摘要 Prompt:")
    print("=" * 60)
    print(build_leaf_summary_prompt(test_messages))
    
    print("\n" + "=" * 60)
    print("Note 提取 Prompt:")
    print("=" * 60)
    print(build_note_extraction_prompt(test_messages))
