#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress LLM Providers - 各 LLM 提供商适配器

支持的提供商：
- 国际：OpenAI, Anthropic, Google Gemini, Mistral
- 国内：DeepSeek, 智谱 GLM, 百度文心, 阿里通义千问

Author: LobsterPress Team
Version: v5.0.0
"""

import os
import logging
from typing import Optional, Dict, Any

from src.llm_client import BaseLLMClient

logger = logging.getLogger(__name__)


# ==================== OpenAI-compatible 基类 ====================


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI-compatible API 客户端基类。

    覆盖所有使用 OpenAI SDK chat.completions.create 接口的提供商。
    子类只需定义 base_url / env_key / default_model。
    """

    base_url: Optional[str] = None
    env_key: str = ""  # 环境变量名，如 'DEEPSEEK_API_KEY'
    default_model: str = ""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        self.api_key = api_key or os.getenv(self.env_key)
        self.model = model or self.default_model
        self.base_url = base_url or self.__class__.base_url
        self.kwargs = kwargs
        self._client = None

    def _get_client(self):
        """延迟加载 OpenAI 客户端。"""
        if self._client is None:
            try:
                from openai import OpenAI

                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client

    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()

        params = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.kwargs.get("temperature", 0.7)),
            "max_tokens": kwargs.get("max_tokens", self.kwargs.get("max_tokens", 500)),
        }

        response = client.chat.completions.create(**params)
        return response.choices[0].message.content

    def is_available(self) -> bool:
        return self.api_key is not None


# ==================== 国际提供商 ====================


class OpenAIClient(OpenAICompatibleClient):
    """OpenAI GPT 系列"""

    base_url = None  # 使用 SDK 默认值
    env_key = "OPENAI_API_KEY"
    default_model = "gpt-4o-mini"


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude 系列"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        **kwargs,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.kwargs = kwargs
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 anthropic: pip install anthropic")
        return self._client

    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        params = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.kwargs.get("max_tokens", 500)),
            "messages": [{"role": "user", "content": prompt}],
        }
        response = client.messages.create(**params)
        return response.content[0].text

    def is_available(self) -> bool:
        return self.api_key is not None


class GeminiClient(BaseLLMClient):
    """Google Gemini 系列"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-pro",
        **kwargs,
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = model
        self.kwargs = kwargs
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError("请安装 google-generativeai: pip install google-generativeai")
        return self._client

    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        generation_config = {
            "temperature": kwargs.get("temperature", self.kwargs.get("temperature", 0.7)),
            "max_output_tokens": kwargs.get("max_tokens", self.kwargs.get("max_tokens", 500)),
        }
        response = client.generate_content(prompt, generation_config=generation_config)
        return response.text

    def is_available(self) -> bool:
        return self.api_key is not None


class MistralClient(OpenAICompatibleClient):
    """Mistral AI"""

    base_url = None
    env_key = "MISTRAL_API_KEY"
    default_model = "mistral-small-latest"


# ==================== 国内提供商 ====================


class DeepSeekClient(OpenAICompatibleClient):
    """DeepSeek"""

    base_url = "https://api.deepseek.com"
    env_key = "DEEPSEEK_API_KEY"
    default_model = "deepseek-chat"


class ZhipuClient(OpenAICompatibleClient):
    """智谱 GLM 系列"""

    base_url = "https://open.bigmodel.cn/api/paas/v4"
    env_key = "ZHIPU_API_KEY"
    default_model = "glm-4-flash"


class BaiduClient(BaseLLMClient):
    """百度文心系列"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        model: str = "ernie-speed-8k",
        **kwargs,
    ):
        self.api_key = api_key or os.getenv("BAIDU_API_KEY")
        self.secret_key = secret_key or os.getenv("BAIDU_SECRET_KEY")
        self.model = model
        self.kwargs = kwargs
        self._access_token = None

    def _get_access_token(self):
        if self._access_token is None:
            import urllib.request
            import json as _json

            url = (
                "https://aip.baidubce.com/oauth/2.0/token"
                f"?grant_type=client_credentials&client_id={self.api_key}"
                f"&client_secret={self.secret_key}"
            )
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                result = _json.loads(response.read().decode("utf-8"))
                self._access_token = result["access_token"]
        return self._access_token

    def generate(self, prompt: str, **kwargs) -> str:
        import urllib.request
        import json as _json

        access_token = self._get_access_token()
        url = (
            "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat"
            f"/{self.model}?access_token={access_token}"
        )
        data = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.kwargs.get("temperature", 0.7)),
        }
        req = urllib.request.Request(
            url,
            data=_json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as response:
            result = _json.loads(response.read().decode("utf-8"))
            return result["result"]

    def is_available(self) -> bool:
        return self.api_key is not None and self.secret_key is not None


class AlibabaClient(OpenAICompatibleClient):
    """阿里通义千问系列"""

    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    env_key = "ALIBABA_API_KEY"
    default_model = "qwen-turbo"


# ==================== 工厂函数 ====================


def get_provider_client(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> BaseLLMClient:
    """获取提供商客户端（工厂函数）

    Args:
        provider: 提供商名称
        api_key: API 密钥
        model: 模型名称
        **kwargs: 额外参数

    Returns:
        LLM 客户端实例
    """
    providers = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "gemini": GeminiClient,
        "mistral": MistralClient,
        "deepseek": DeepSeekClient,
        "zhipu": ZhipuClient,
        "baidu": BaiduClient,
        "alibaba": AlibabaClient,
    }

    provider_class = providers.get(provider.lower())
    if provider_class is None:
        raise ValueError(
            f"不支持的 LLM 提供商: {provider}。" f"支持的提供商: {list(providers.keys())}"
        )

    return provider_class(api_key=api_key, model=model, **kwargs)
