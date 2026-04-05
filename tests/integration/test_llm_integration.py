#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress v3.2.1 - LLM 集成测试

测试 LLM 客户端集成和 prompt 优化效果。

Author: LobsterPress Team
Version: v3.2.1
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src")
)

from src.prompts import (
    build_leaf_summary_prompt,
    build_condensed_summary_prompt,
    build_note_extraction_prompt,
    estimate_tokens,
    truncate_messages,
)
from src.llm_client import create_llm_client


# 测试数据
TEST_MESSAGES = [
    {"role": "user", "content": "我们决定使用 PostgreSQL 作为主数据库"},
    {
        "role": "assistant",
        "content": "好的，PostgreSQL 适合 ACID 事务场景，是个不错的选择",
    },
    {"role": "user", "content": "版本是 15.2，连接池设置为 20"},
    {"role": "assistant", "content": "已记录：PostgreSQL 15.2，连接池 20"},
    {"role": "user", "content": "部署环境是 AWS，不能使用 GCP"},
    {"role": "assistant", "content": "了解，部署限制为 AWS"},
]

TEST_COMBINED_CONTENT = """
## 对话摘要 (4 条消息)
- 用户消息: 2 条
- 助手消息: 2 条

### 核心内容:
决定使用 PostgreSQL 15.2 作为主数据库，连接池 20，部署在 AWS。
"""


def test_prompt_building():
    """测试 prompt 构建"""
    print("\n" + "=" * 60)
    print("🧪 测试 Prompt 构建")
    print("=" * 60)

    # 1. 叶子摘要 prompt
    leaf_prompt = build_leaf_summary_prompt(TEST_MESSAGES)
    print(f"\n✅ 叶子摘要 Prompt 构建成功")
    print(f"   长度: {len(leaf_prompt)} 字符")
    print(f"   预估 tokens: {estimate_tokens(leaf_prompt)}")
    assert "对话摘要" in leaf_prompt
    assert "PostgreSQL" in leaf_prompt

    # 2. 压缩摘要 prompt
    condensed_prompt = build_condensed_summary_prompt(TEST_COMBINED_CONTENT, depth=1)
    print(f"\n✅ 压缩摘要 Prompt 构建成功")
    print(f"   长度: {len(condensed_prompt)} 字符")
    print(f"   预估 tokens: {estimate_tokens(condensed_prompt)}")
    assert "Level 1" in condensed_prompt

    # 3. Note 提取 prompt
    note_prompt = build_note_extraction_prompt(TEST_MESSAGES)
    print(f"\n✅ Note 提取 Prompt 构建成功")
    print(f"   长度: {len(note_prompt)} 字符")
    print(f"   预估 tokens: {estimate_tokens(note_prompt)}")
    assert "稳定的语义知识" in note_prompt
    assert "JSON" in note_prompt

    return True


def test_token_estimation():
    """测试 token 估算"""
    print("\n" + "=" * 60)
    print("🧪 测试 Token 估算")
    print("=" * 60)

    text = "这是一段测试文本，用于估算 token 数量。"
    tokens = estimate_tokens(text)
    print(f"文本: {text}")
    print(f"字符数: {len(text)}")
    print(f"预估 tokens: {tokens}")
    assert tokens > 0

    # 测试消息截断
    long_messages = [{"role": "user", "content": "x" * 10000} for _ in range(10)]
    truncated = truncate_messages(long_messages, max_tokens=5000)
    print(f"\n原始消息数: {len(long_messages)}")
    print(f"截断后消息数: {len(truncated)}")
    assert len(truncated) < len(long_messages)

    return True


def test_llm_integration_with_deepseek():
    """测试 DeepSeek LLM 集成"""
    print("\n" + "=" * 60)
    print("🧪 测试 DeepSeek LLM 集成")
    print("=" * 60)

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️ DEEPSEEK_API_KEY 未设置，跳过实际 API 测试")
        return True

    try:
        # 创建客户端
        client = create_llm_client(
            provider="deepseek", api_key=api_key, model="deepseek-chat"
        )
        print(f"✅ DeepSeek 客户端创建成功")

        # 测试叶子摘要生成
        prompt = build_leaf_summary_prompt(TEST_MESSAGES[:2])
        result = client.generate(prompt, temperature=0.7, max_tokens=300)
        print(f"\n✅ 叶子摘要生成成功")
        print(f"   响应长度: {len(result)} 字符")
        print(f"   预览: {result[:100]}...")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_llm_integration_with_zhipu():
    """测试智谱 GLM LLM 集成"""
    print("\n" + "=" * 60)
    print("🧪 测试智谱 GLM LLM 集成")
    print("=" * 60)

    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print("⚠️ ZHIPU_API_KEY 未设置，跳过实际 API 测试")
        return True

    try:
        # 创建客户端
        client = create_llm_client(
            provider="zhipu", api_key=api_key, model="glm-4-flash"
        )
        print(f"✅ 智谱 GLM 客户端创建成功")

        # 测试 Note 提取
        prompt = build_note_extraction_prompt(TEST_MESSAGES[:2])
        result = client.generate(prompt, temperature=0.5, max_tokens=500)
        print(f"\n✅ Note 提取成功")
        print(f"   响应长度: {len(result)} 字符")
        print(f"   预览: {result[:150]}...")

        # 尝试解析 JSON
        import json

        # 清理可能的代码块标记
        cleaned_result = result.strip()
        if cleaned_result.startswith("```"):
            # 移除 ```json 和 ```
            lines = cleaned_result.split("\n")
            cleaned_result = "\n".join(lines[1:-1])

        notes = json.loads(cleaned_result.strip())
        print(f"   提取的 notes 数量: {len(notes)}")
        print(f"   内容: {notes}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("LobsterPress v3.2.1 - LLM 集成测试")
    print("=" * 60)

    results = []

    # 1. Prompt 构建测试
    results.append(("Prompt 构建", test_prompt_building()))

    # 2. Token 估算测试
    results.append(("Token 估算", test_token_estimation()))

    # 3. DeepSeek 集成测试（需要 API key）
    results.append(("DeepSeek 集成", test_llm_integration_with_deepseek()))

    # 4. 智谱 GLM 集成测试（需要 API key）
    results.append(("智谱 GLM 集成", test_llm_integration_with_zhipu()))

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:20s} {status}")

    success_count = sum(1 for _, s in results if s)
    print(f"\n总计: {success_count}/{len(results)} 通过")

    if success_count == len(results):
        print("\n🎉 所有测试通过！LLM 集成正常工作")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查配置")
        return 1


if __name__ == "__main__":
    sys.exit(main())
