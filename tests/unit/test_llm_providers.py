#!/usr/bin/env python3
"""v3.2.0 多 LLM 提供商测试"""

import sys
import os

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(_project_root, "src"))

from src.llm_client import create_llm_client, get_llm_client, MockLLMClient
from src.llm_providers import get_provider_client


def test_mock_client():
    """测试 Mock 客户端"""
    print("\n🧪 测试 Mock 客户端...")

    # 创建 Mock 客户端
    client = create_llm_client(provider="mock")

    # 测试生成
    result = client.generate("测试提示词")

    assert result is not None
    assert len(result) > 0
    assert client.is_available()

    print(f"✅ Mock 客户端测试通过")
    return True


def test_openai_client():
    """测试 OpenAI 客户端（不实际调用 API）"""
    print("\n🧪 测试 OpenAI 客户端初始化...")

    # 创建客户端（无 API key，仅测试初始化）
    client = create_llm_client(
        provider="openai", api_key="test-key", model="gpt-4o-mini"
    )

    # 验证客户端创建成功
    assert client is not None
    assert client.api_key == "test-key"
    assert client.model == "gpt-4o-mini"
    assert client.is_available()

    print(f"✅ OpenAI 客户端初始化成功")
    return True


def test_deepseek_client():
    """测试 DeepSeek 客户端（不实际调用 API）"""
    print("\n🧪 测试 DeepSeek 客户端初始化...")

    # 创建客户端
    client = create_llm_client(
        provider="deepseek", api_key="test-key", model="deepseek-chat"
    )

    # 验证客户端创建成功
    assert client is not None
    assert client.api_key == "test-key"
    assert client.model == "deepseek-chat"
    assert client.is_available()

    print(f"✅ DeepSeek 客户端初始化成功")
    return True


def test_zhipu_client():
    """测试智谱 GLM 客户端（不实际调用 API）"""
    print("\n🧪 测试智谱 GLM 客户端初始化...")

    # 创建客户端
    client = create_llm_client(
        provider="zhipu", api_key="test-key", model="glm-4-flash"
    )

    # 验证客户端创建成功
    assert client is not None
    assert client.api_key == "test-key"
    assert client.model == "glm-4-flash"
    assert client.is_available()

    print(f"✅ 智谱 GLM 客户端初始化成功")
    return True


def test_alibaba_client():
    """测试阿里通义千问客户端（不实际调用 API）"""
    print("\n🧪 测试阿里通义千问客户端初始化...")

    # 创建客户端
    client = create_llm_client(
        provider="alibaba", api_key="test-key", model="qwen-turbo"
    )

    # 验证客户端创建成功
    assert client is not None
    assert client.api_key == "test-key"
    assert client.model == "qwen-turbo"
    assert client.is_available()

    print(f"✅ 阿里通义千问客户端初始化成功")
    return True


def test_anthropic_client():
    """测试 Anthropic Claude 客户端（不实际调用 API）"""
    print("\n🧪 测试 Anthropic Claude 客户端初始化...")

    # 创建客户端
    client = create_llm_client(
        provider="anthropic", api_key="test-key", model="claude-3-5-sonnet-20241022"
    )

    # 验证客户端创建成功
    assert client is not None
    assert client.api_key == "test-key"
    assert client.model == "claude-3-5-sonnet-20241022"
    assert client.is_available()

    print(f"✅ Anthropic Claude 客户端初始化成功")
    return True


def test_gemini_client():
    """测试 Google Gemini 客户端（不实际调用 API）"""
    print("\n🧪 测试 Google Gemini 客户端初始化...")

    # 创建客户端
    client = create_llm_client(
        provider="gemini", api_key="test-key", model="gemini-pro"
    )

    # 验证客户端创建成功
    assert client is not None
    assert client.api_key == "test-key"
    assert client.model == "gemini-pro"
    assert client.is_available()

    print(f"✅ Google Gemini 客户端初始化成功")
    return True


def test_mistral_client():
    """测试 Mistral 客户端（不实际调用 API）"""
    print("\n🧪 测试 Mistral 客户端初始化...")

    # 创建客户端
    client = create_llm_client(
        provider="mistral", api_key="test-key", model="mistral-small-latest"
    )

    # 验证客户端创建成功
    assert client is not None
    assert client.api_key == "test-key"
    assert client.model == "mistral-small-latest"
    assert client.is_available()

    print(f"✅ Mistral 客户端初始化成功")
    return True


def test_baidu_client():
    """测试百度文心客户端（不实际调用 API）"""
    print("\n🧪 测试百度文心客户端初始化...")

    # 创建客户端（百度需要两个密钥）
    client = create_llm_client(
        provider="baidu",
        api_key="test-api-key",
        secret_key="test-secret-key",
        model="ernie-speed-8k",
    )

    # 验证客户端创建成功
    assert client is not None
    assert client.api_key == "test-api-key"
    assert client.secret_key == "test-secret-key"
    assert client.model == "ernie-speed-8k"
    assert client.is_available()

    print(f"✅ 百度文心客户端初始化成功")
    return True


def test_factory_function():
    """测试工厂函数"""
    print("\n🧪 测试工厂函数...")

    # 测试不支持的提供商
    try:
        client = get_provider_client("unsupported_provider")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "不支持的 LLM 提供商" in str(e)

    print(f"✅ 工厂函数测试通过")
    return True


def test_environment_variable():
    """测试环境变量配置"""
    print("\n🧪 测试环境变量配置...")

    import os

    # 设置环境变量
    os.environ["LOBSTER_LLM_PROVIDER"] = "mock"

    # 使用环境变量创建客户端
    client = get_llm_client()

    assert client is not None
    assert isinstance(client, MockLLMClient)

    print(f"✅ 环境变量配置测试通过")
    return True


def test_graceful_fallback():
    """测试优雅降级"""
    print("\n🧪 测试优雅降级...")

    # 测试无效提供商，应该降级为 Mock
    client = create_llm_client(provider="invalid_provider")

    # 应该降级为 Mock 客户端
    assert client is not None
    assert isinstance(client, MockLLMClient)

    print(f"✅ 优雅降级测试通过")
    return True


def main():
    print("=" * 60)
    print("v3.2.0 多 LLM 提供商测试")
    print("=" * 60)

    tests = [
        test_mock_client,
        test_openai_client,
        test_deepseek_client,
        test_zhipu_client,
        test_alibaba_client,
        test_anthropic_client,
        test_gemini_client,
        test_mistral_client,
        test_baidu_client,
        test_factory_function,
        test_environment_variable,
        test_graceful_fallback,
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 60)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 60)

    if all(results):
        print("\n✅ 所有测试通过！多 LLM 提供商支持正常工作")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
