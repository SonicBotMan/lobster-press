#!/usr/bin/env python3
"""实际 LLM API 调用测试"""

import sys
import os
import pytest

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(_project_root, "src"))

from src.llm_client import create_llm_client

# API Keys（由用户提供）
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY_HERE"
# Test API key - set ZHIPU_API_KEY env var
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")

if not os.environ.get("ZHIPU_API_KEY"):
    pytest.skip("ZHIPU_API_KEY not set", allow_module_level=True)

# 测试提示词（模拟摘要生成场景）
TEST_PROMPT = """请总结以下对话内容，保留关键决策和技术要点：

用户: 我们决定使用 PostgreSQL 作为主数据库
助手: 好的，PostgreSQL 适合 ACID 事务场景
用户: 连接池设置为 20 个连接
助手: 已记录，连接池配置为 20

请生成简洁摘要（100字以内）："""


def test_deepseek():
    """测试 DeepSeek API"""
    print("\n" + "=" * 60)
    print("🧪 测试 DeepSeek API")
    print("=" * 60)

    try:
        # 创建客户端
        client = create_llm_client(
            provider="deepseek", api_key=DEEPSEEK_API_KEY, model="deepseek-chat"
        )

        print(f"✅ 客户端创建成功")
        print(f"   Provider: DeepSeek")
        print(f"   Model: deepseek-chat")
        # v4.0.9: 移除 API Key 打印（CodeQL 安全警告）

        # 调用 API
        print(f"\n📤 发送请求...")
        result = client.generate(TEST_PROMPT, temperature=0.7, max_tokens=200)

        print(f"\n✅ API 调用成功！")
        print(f"\n📝 生成结果：")
        print("-" * 60)
        print(result)
        print("-" * 60)
        print(f"\n📊 统计：")
        print(f"   响应长度: {len(result)} 字符")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_zhipu():
    """测试智谱 GLM API"""
    print("\n" + "=" * 60)
    print("🧪 测试智谱 GLM API")
    print("=" * 60)

    try:
        # 创建客户端
        client = create_llm_client(
            provider="zhipu", api_key=ZHIPU_API_KEY, model="glm-4-flash"
        )

        print(f"✅ 客户端创建成功")
        print(f"   Provider: 智谱 GLM")
        print(f"   Model: glm-4-flash")
        # v4.0.9: 移除 API Key 打印（CodeQL 安全警告）

        # 调用 API
        print(f"\n📤 发送请求...")
        result = client.generate(TEST_PROMPT, temperature=0.7, max_tokens=200)

        print(f"\n✅ API 调用成功！")
        print(f"\n📝 生成结果：")
        print("-" * 60)
        print(result)
        print("-" * 60)
        print(f"\n📊 统计：")
        print(f"   响应长度: {len(result)} 字符")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("LobsterPress v3.2.0 - 实际 LLM API 调用测试")
    print("=" * 60)

    results = []

    # 测试 DeepSeek
    results.append(("DeepSeek", test_deepseek()))

    # 测试智谱 GLM
    results.append(("智谱 GLM", test_zhipu()))

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    for provider, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{provider:15s} {status}")

    success_count = sum(1 for _, s in results if s)
    print(f"\n总计: {success_count}/{len(results)} 通过")

    if success_count == len(results):
        print("\n🎉 所有测试通过！LLM 客户端正常工作")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查 API key 或网络连接")
        return 1


if __name__ == "__main__":
    sys.exit(main())
