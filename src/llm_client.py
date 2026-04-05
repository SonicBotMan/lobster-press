#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress LLM Client - 统一 LLM 客户端接口

支持的提供商：
- 国际：OpenAI, Anthropic, Google Gemini, Mistral
- 国内：DeepSeek, 智谱 GLM, 百度文心, 阿里通义千问

Author: LobsterPress Team
Version: v4.0.41
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本

        Args:
            prompt: 输入提示词
            **kwargs: 额外参数（temperature, max_tokens等）

        Returns:
            生成的文本
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        pass


class MockLLMClient(BaseLLMClient):
    """模拟 LLM 客户端（用于测试）

    v3.2.1: 智能响应，根据 prompt 类型返回合适的格式
    """

    def __init__(self, response: str = None):
        self.default_response = response or "这是一个模拟摘要。"

    def generate(self, prompt: str, **kwargs) -> str:
        """智能生成响应

        根据 prompt 内容返回合适的格式：
        - JSON 请求 → 返回 JSON 格式
        - 摘要请求 → 返回摘要格式
        - 其他 → 返回默认响应
        """
        # 检测是否需要 JSON 响应
        if "JSON" in prompt or "稳定的语义知识" in prompt or "提取结果" in prompt:
            # Note 提取场景：返回 JSON 数组
            return "[]"  # 空数组，避免测试失败

        # 检测是否需要摘要
        if "摘要" in prompt or "总结" in prompt:
            return self.default_response

        # 默认响应
        return self.default_response

    def is_available(self) -> bool:
        return True


class FallbackLLMClient(BaseLLMClient):
    """LLM 三级降级链

    借鉴 MemOS:
      Level 1: skillSummarizer（技能专用模型）
      Level 2: summarizer（通用摘要模型）
      Level 3: OpenClaw Native（从环境变量读取）
      Level 4: Mock（无 LLM）

    每级失败自动降级，零手动干预。
    """

    def __init__(self, skill_client=None, summary_client=None, native_client=None):
        self.chain = []
        if skill_client and skill_client.is_available():
            self.chain.append(("skill", skill_client))
        if summary_client and summary_client.is_available():
            self.chain.append(("summary", summary_client))
        if native_client and native_client.is_available():
            self.chain.append(("native", native_client))
        # 兜底
        self.chain.append(("mock", MockLLMClient()))

    def generate(self, prompt: str, **kwargs) -> str:
        for name, client in self.chain:
            try:
                result = client.generate(prompt, **kwargs)
                if result:
                    return result
            except Exception as e:
                print(f"⚠️ LLM [{name}] 失败: {e}，尝试下一级")
                continue
        return ""

    def is_available(self) -> bool:
        return len(self.chain) > 0


def _create_single_client(
    provider: str, api_key: Optional[str], model: Optional[str]
) -> BaseLLMClient:
    """创建单一 LLM 客户端（用于 FallbackLLMClient 内部）"""
    if provider == "mock":
        return MockLLMClient()
    try:
        from llm_providers import get_provider_client

        return get_provider_client(provider, api_key, model)
    except Exception:
        return MockLLMClient()


def create_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    fallback: bool = False,
    **kwargs,
) -> BaseLLMClient:
    """创建 LLM 客户端（工厂函数）

    Args:
        provider: 提供商名称（不指定时从环境变量 LOBSTER_LLM_PROVIDER 读取）
        api_key: API 密钥（不指定时从环境变量读取）
        model: 模型名称（不指定时使用默认模型）
        **kwargs: 额外配置参数

    Returns:
        LLM 客户端实例

    环境变量：
        LOBSTER_LLM_PROVIDER: 提供商名称
        LOBSTER_LLM_API_KEY: API 密钥
        LOBSTER_LLM_MODEL: 模型名称

    支持的提供商：
        - openai: OpenAI GPT 系列
        - anthropic: Anthropic Claude 系列
        - gemini: Google Gemini 系列
        - mistral: Mistral AI
        - deepseek: DeepSeek
        - zhipu: 智谱 GLM 系列
        - baidu: 百度文心系列
        - alibaba: 阿里通义千问系列
        - mock: 模拟客户端（用于测试）

    Examples:
        # 使用环境变量配置
        client = create_llm_client()

        # 指定提供商
        client = create_llm_client(provider='openai', api_key='sk-xxx')

        # 使用 DeepSeek
        client = create_llm_client(
            provider='deepseek',
            api_key='sk-xxx',
            model='deepseek-chat'
        )
    """
    # 从环境变量读取配置
    provider = provider or os.getenv("LOBSTER_LLM_PROVIDER", "mock")

    if fallback:
        skill_provider = os.getenv("LOBSTER_LLM_SKILL_PROVIDER")
        summary_provider = os.getenv("LOBSTER_LLM_SUMMARY_PROVIDER")

        skill_client = None
        summary_client = None
        native_client = None

        if skill_provider:
            try:
                skill_client = _create_single_client(
                    skill_provider,
                    os.getenv("LOBSTER_LLM_SKILL_API_KEY"),
                    os.getenv("LOBSTER_LLM_SKILL_MODEL"),
                )
            except Exception:
                pass

        if summary_provider:
            try:
                summary_client = _create_single_client(
                    summary_provider,
                    os.getenv("LOBSTER_LLM_SUMMARY_API_KEY"),
                    os.getenv("LOBSTER_LLM_SUMMARY_MODEL"),
                )
            except Exception:
                pass

        try:
            native_client = _create_single_client(provider, api_key, model)
        except Exception:
            pass

        return FallbackLLMClient(
            skill_client=skill_client,
            summary_client=summary_client,
            native_client=native_client,
        )

    # 根据提供商创建客户端
    if provider == "mock":
        return MockLLMClient()

    # 尝试导入提供商适配器
    try:
        from llm_providers import get_provider_client

        return get_provider_client(provider, api_key, model, **kwargs)
    except ImportError as e:
        print(f"⚠️ 无法加载 LLM 提供商 {provider}: {e}")
        print(f"   降级为 Mock 客户端")
        return MockLLMClient()
    except Exception as e:
        print(f"⚠️ 创建 LLM 客户端失败: {e}")
        print(f"   降级为 Mock 客户端")
        return MockLLMClient()


# 便捷函数
def get_llm_client() -> BaseLLMClient:
    """获取 LLM 客户端（使用环境变量配置）

    这是最简单的使用方式，只需配置环境变量：
        export LOBSTER_LLM_PROVIDER=openai
        export LOBSTER_LLM_API_KEY=sk-xxx
        export LOBSTER_LLM_MODEL=gpt-4

    然后在代码中：
        client = get_llm_client()
        summary = client.generate("总结这段文本...")
    """
    return create_llm_client()
