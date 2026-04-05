#!/usr/bin/env python3
"""v3.1.0 LLM 摘要功能测试"""

import sys
import os

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(_project_root, "src"))

from src.database import LobsterDatabase
from src.dag_compressor import DAGCompressor


class MockLLMClient:
    """模拟 LLM 客户端"""

    def generate(self, prompt: str) -> str:
        """模拟 LLM 生成摘要"""
        if "对话摘要" in prompt:
            return "用户询问了关于 Python 异步编程的问题。助手解释了 asyncio/await 的基本用法，并提供了代码示例。用户表示理解了，将开始实践。"
        elif "压缩摘要" in prompt:
            return "讨论了 Python 异步编程的核心概念，包括事件循环、协程和任务调度。"
        else:
            # 返回包含关键字的摘要
            return "LLM 生成的摘要：这是一个关于 Python 异步编程的测试摘要。"


def test_llm_leaf_summary():
    """测试 LLM 叶子摘要生成"""
    print("\n🧪 测试 LLM 叶子摘要生成...")

    # 创建数据库
    db = LobsterDatabase(":memory:")

    # 插入测试消息
    messages = [
        {
            "id": "msg_1",
            "conversationId": "test_conv",
            "seq": 1,
            "role": "user",
            "content": "请问 Python 的 asyncio 和 await 有什么区别？",
        },
        {
            "id": "msg_2",
            "conversationId": "test_conv",
            "seq": 2,
            "role": "assistant",
            "content": "asyncio 是 Python 3.4+ 引入的异步编程库，await 是关键字。主要区别： asyncio 提供了高级 API，而 await 是语法糖。",
        },
        {
            "id": "msg_3",
            "conversationId": "test_conv",
            "seq": 3,
            "role": "user",
            "content": "能举个例子吗?",
        },
        {
            "id": "msg_4",
            "conversationId": "test_conv",
            "seq": 4,
            "role": "assistant",
            "content": '当然。使用 async def 定义协程，用 await 等待异步操作完成。例如:\nimport asyncio\n\nasync def fetch_data():\n    await asyncio.sleep(1)\n    return "Data fetched"',
        },
    ]

    for msg in messages:
        db.save_message(msg)

    # 创建 DAGCompressor（有 LLM）
    compressor_with_llm = DAGCompressor(db, llm_client=MockLLMClient())

    # 生成摘要
    summary = compressor_with_llm._generate_leaf_summary(messages)

    # 验证摘要质量
    assert "对话摘要" in summary
    assert "LLM 生成的摘要" in summary or "Python" in summary or "异步" in summary
    assert len(summary) > 0

    print(f"✅ LLM 叶子摘要生成成功 (长度: {len(summary)})")
    print(f"摘要内容:\n{summary[:200]}...")
    return True


def test_extractive_leaf_summary():
    """测试提取式叶子摘要（降级方案）"""
    print("\n🧪 测试提取式叶子摘要...")

    # 创建数据库
    db = LobsterDatabase(":memory:")

    # 插入测试消息
    messages = [
        {
            "id": "msg_1",
            "conversationId": "test_conv",
            "seq": 1,
            "role": "user",
            "content": "测试消息 1",
        },
        {
            "id": "msg_2",
            "conversationId": "test_conv",
            "seq": 2,
            "role": "assistant",
            "content": "测试消息 2",
        },
    ]

    for msg in messages:
        db.save_message(msg)

    # 创建 DAGCompressor（无 LLM）
    compressor_no_llm = DAGCompressor(db)

    # 生成摘要
    summary = compressor_no_llm._generate_leaf_summary(messages)

    # 验证降级方案
    assert "对话摘要" in summary
    assert len(summary) > 0

    print(f"✅ 提取式叶子摘要生成成功 (长度: {len(summary)})")
    return True


def test_llm_condensed_summary():
    """测试 LLM 压缩摘要生成"""
    print("\n🧪 测试 LLM 压缩摘要生成...")

    # 创建数据库
    db = LobsterDatabase(":memory:")

    # 创建 DAGCompressor（有 LLM）
    compressor_with_llm = DAGCompressor(db, llm_client=MockLLMClient())

    # 模拟合并内容
    combined_content = "这是第一段内容。" * 100

    # 生成压缩摘要
    summary = compressor_with_llm._generate_condensed_summary(combined_content, depth=0)

    # 验证摘要质量
    assert "压缩摘要" in summary
    assert "Depth 1" in summary
    assert len(summary) > 0

    print(f"✅ LLM 压缩摘要生成成功 (长度: {len(summary)})")
    return True


def test_llm_client_integration():
    """测试 LLM 客户端集成"""
    print("\n🧪 测试 LLM 客户端集成...")

    # 创建数据库
    db = LobsterDatabase(":memory:")

    # 创建 Mock LLM 客户端
    llm_client = MockLLMClient()

    # 创建 DAGCompressor
    compressor = DAGCompressor(db, llm_client=llm_client)

    # 验证 LLM 客户端被正确传递
    assert compressor.llm_client is llm_client

    print("✅ LLM 客户端集成成功")
    return True


def main():
    print("=" * 60)
    print("v3.1.0 LLM 摘要功能测试")
    print("=" * 60)

    tests = [
        test_llm_leaf_summary,
        test_extractive_leaf_summary,
        test_llm_condensed_summary,
        test_llm_client_integration,
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 60)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 60)

    if all(results):
        print("\n✅ 所有测试通过！LLM 摘要功能正常工作")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
