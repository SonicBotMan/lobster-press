#!/usr/bin/env python3
"""v4.0.x FallbackLLMClient 测试"""

import sys

sys.path.insert(0, "/Users/a523034406/Documents/OpenCode/lobster-press")

from src.llm_client import (
    FallbackLLMClient,
    MockLLMClient,
    create_llm_client,
)


class MockClient:
    """测试用模拟客户端"""

    def __init__(
        self,
        name: str,
        response: str = "mock response",
        available: bool = True,
        fail_on_prompt: str = None,
    ):
        self.name = name
        self.response = response
        self.available_flag = available
        self.fail_on_prompt = fail_on_prompt
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        if self.fail_on_prompt and self.fail_on_prompt in prompt:
            raise Exception(f"{self.name} failed")
        if not self.response:
            return ""
        return f"{self.name}:{self.response}"

    def is_available(self) -> bool:
        return self.available_flag


def test_fallback_chain_order():
    """测试降级链顺序：skill → summary → native → mock"""
    skill = MockClient("skill", "skill_response")
    summary = MockClient("summary", "summary_response")
    native = MockClient("native", "native_response")

    client = FallbackLLMClient(
        skill_client=skill, summary_client=summary, native_client=native
    )

    result = client.generate("test prompt")
    assert result == "skill:skill_response"
    assert skill.call_count == 1
    assert summary.call_count == 0
    assert native.call_count == 0


def test_fallback_skill_fails():
    """测试 skill 失败时降级到 summary"""
    skill = MockClient("skill", "skill_response", fail_on_prompt="SKILL_FAIL")
    summary = MockClient("summary", "summary_response")
    native = MockClient("native", "native_response")

    client = FallbackLLMClient(
        skill_client=skill, summary_client=summary, native_client=native
    )

    result = client.generate("SKILL_FAIL")
    assert result == "summary:summary_response"
    assert skill.call_count == 1
    assert summary.call_count == 1
    assert native.call_count == 0


def test_fallback_skill_summary_fail():
    """测试 skill 和 summary 都失败时降级到 native"""
    skill = MockClient("skill", "skill_response", fail_on_prompt="SKILL_FAIL")
    summary = MockClient("summary", "summary_response", fail_on_prompt="SUMMARY_FAIL")
    native = MockClient("native", "native_response")

    client = FallbackLLMClient(
        skill_client=skill, summary_client=summary, native_client=native
    )

    result = client.generate("SKILL_FAIL_SUMMARY_FAIL")
    assert result == "native:native_response"
    assert skill.call_count == 1
    assert summary.call_count == 1
    assert native.call_count == 1


def test_fallback_all_fail():
    """测试所有级别都失败时返回 mock"""
    skill = MockClient("skill", "skill_response", available=False)
    summary = MockClient("summary", "summary_response", available=False)
    native = MockClient("native", "native_response", available=False)

    client = FallbackLLMClient(
        skill_client=skill, summary_client=summary, native_client=native
    )

    result = client.generate("test")
    assert result != ""
    assert skill.call_count == 0
    assert summary.call_count == 0
    assert native.call_count == 0


def test_fallback_generate_returns_first_non_empty():
    """测试 generate 返回第一个非空结果"""
    skill = MockClient("skill", "")
    summary = MockClient("summary", "summary_response")
    native = MockClient("native", "native_response")

    client = FallbackLLMClient(
        skill_client=skill, summary_client=summary, native_client=native
    )

    result = client.generate("test")
    assert result == "summary:summary_response"
    assert skill.call_count == 1
    assert summary.call_count == 1


def test_fallback_generate_catches_exceptions():
    """测试 generate 捕获异常并继续"""
    skill = MockClient("skill", "skill_response", fail_on_prompt="SKILL_FAIL")
    summary = MockClient("summary", "summary_response", fail_on_prompt="SUMMARY_FAIL")
    native = MockClient("native", "native_response", fail_on_prompt="NATIVE_FAIL")

    client = FallbackLLMClient(
        skill_client=skill, summary_client=summary, native_client=native
    )

    result = client.generate("SKILL_FAIL_SUMMARY_FAIL_NATIVE_FAIL")
    assert result != ""
    assert skill.call_count == 1
    assert summary.call_count == 1
    assert native.call_count == 1


def test_fallback_is_available():
    """测试 is_available 当链非空时返回 True"""
    skill = MockClient("skill", "skill_response")
    summary = MockClient("summary", "summary_response")

    client = FallbackLLMClient(
        skill_client=skill, summary_client=summary, native_client=None
    )

    assert client.is_available() is True


def test_fallback_empty_chain():
    """测试空链时 is_available 仍返回 True（mock 兜底）"""
    client = FallbackLLMClient(
        skill_client=None, summary_client=None, native_client=None
    )

    assert client.is_available() is True
    assert len(client.chain) == 1


def test_create_llm_client_fallback_true():
    """测试 create_llm_client(fallback=True) 返回 FallbackLLMClient"""
    client = create_llm_client(fallback=True)
    assert isinstance(client, FallbackLLMClient)
    assert client.is_available() is True


def test_create_llm_client_fallback_false():
    """测试 create_llm_client(fallback=False) 向后兼容"""
    client = create_llm_client(fallback=False)
    assert isinstance(client, MockLLMClient)


def test_create_llm_client_fallback_uses_env_vars(monkeypatch):
    """测试 fallback=True 使用环境变量配置"""
    monkeypatch.setenv("LOBSTER_LLM_SKILL_PROVIDER", "mock")
    monkeypatch.setenv("LOBSTER_LLM_SUMMARY_PROVIDER", "mock")
    monkeypatch.setenv("LOBSTER_LLM_PROVIDER", "mock")

    client = create_llm_client(fallback=True)
    assert isinstance(client, FallbackLLMClient)
