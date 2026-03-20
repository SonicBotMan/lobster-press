#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress LLM Providers - 各 LLM 提供商适配器

支持的提供商：
- 国际：OpenAI, Anthropic, Google Gemini, Mistral
- 国内：DeepSeek, 智谱 GLM, 百度文心, 阿里通义千问

Author: LobsterPress Team
Version: v4.0.12
"""

import os
from typing import Optional, Dict, Any
from src.llm_client import BaseLLMClient


# ==================== 国际提供商 ====================

class OpenAIClient(BaseLLMClient):
    """OpenAI GPT 系列"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        **kwargs
    ):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.base_url = base_url or os.getenv('OPENAI_BASE_URL')
        self.kwargs = kwargs
        self._client = None
    
    def _get_client(self):
        """延迟加载 OpenAI 客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        
        # 合并参数
        params = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.kwargs.get('temperature', 0.7)),
            'max_tokens': kwargs.get('max_tokens', self.kwargs.get('max_tokens', 500))
        }
        
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    def is_available(self) -> bool:
        return self.api_key is not None


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude 系列"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        **kwargs
    ):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        self.kwargs = kwargs
        self._client = None
    
    def _get_client(self):
        """延迟加载 Anthropic 客户端"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 anthropic: pip install anthropic")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        
        # 合并参数
        params = {
            'model': self.model,
            'max_tokens': kwargs.get('max_tokens', self.kwargs.get('max_tokens', 500)),
            'messages': [{'role': 'user', 'content': prompt}]
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
        **kwargs
    ):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.model = model
        self.kwargs = kwargs
        self._client = None
    
    def _get_client(self):
        """延迟加载 Gemini 客户端"""
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
        
        # 合并参数
        generation_config = {
            'temperature': kwargs.get('temperature', self.kwargs.get('temperature', 0.7)),
            'max_output_tokens': kwargs.get('max_tokens', self.kwargs.get('max_tokens', 500))
        }
        
        response = client.generate_content(prompt, generation_config=generation_config)
        return response.text
    
    def is_available(self) -> bool:
        return self.api_key is not None


class MistralClient(BaseLLMClient):
    """Mistral AI"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistral-small-latest",
        **kwargs
    ):
        self.api_key = api_key or os.getenv('MISTRAL_API_KEY')
        self.model = model
        self.kwargs = kwargs
        self._client = None
    
    def _get_client(self):
        """延迟加载 Mistral 客户端"""
        if self._client is None:
            try:
                from mistralai import Mistral
                self._client = Mistral(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 mistralai: pip install mistralai")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        
        # 合并参数
        params = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.kwargs.get('temperature', 0.7)),
            'max_tokens': kwargs.get('max_tokens', self.kwargs.get('max_tokens', 500))
        }
        
        response = client.chat.complete(**params)
        return response.choices[0].message.content
    
    def is_available(self) -> bool:
        return self.api_key is not None


# ==================== 国内提供商 ====================

class DeepSeekClient(BaseLLMClient):
    """DeepSeek"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        **kwargs
    ):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.model = model
        self.kwargs = kwargs
        self._client = None
    
    def _get_client(self):
        """延迟加载 DeepSeek 客户端（使用 OpenAI 兼容接口）"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com"
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        
        # 合并参数
        params = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.kwargs.get('temperature', 0.7)),
            'max_tokens': kwargs.get('max_tokens', self.kwargs.get('max_tokens', 500))
        }
        
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    def is_available(self) -> bool:
        return self.api_key is not None


class ZhipuClient(BaseLLMClient):
    """智谱 GLM 系列"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "glm-4-flash",
        **kwargs
    ):
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY')
        self.model = model
        self.kwargs = kwargs
        self._client = None
    
    def _get_client(self):
        """延迟加载智谱客户端"""
        if self._client is None:
            try:
                from zhipuai import ZhipuAI
                self._client = ZhipuAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 zhipuai: pip install zhipuai")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        
        # 合并参数
        params = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.kwargs.get('temperature', 0.7)),
            'max_tokens': kwargs.get('max_tokens', self.kwargs.get('max_tokens', 500))
        }
        
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    def is_available(self) -> bool:
        return self.api_key is not None


class BaiduClient(BaseLLMClient):
    """百度文心系列"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        model: str = "ernie-speed-8k",
        **kwargs
    ):
        self.api_key = api_key or os.getenv('BAIDU_API_KEY')
        self.secret_key = secret_key or os.getenv('BAIDU_SECRET_KEY')
        self.model = model
        self.kwargs = kwargs
        self._access_token = None
    
    def _get_access_token(self):
        """获取百度 access_token"""
        if self._access_token is None:
            import urllib.request
            import urllib.parse
            import json
            
            url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
            
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                self._access_token = result['access_token']
        
        return self._access_token
    
    def generate(self, prompt: str, **kwargs) -> str:
        import urllib.request
        import json
        
        access_token = self._get_access_token()
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{self.model}?access_token={access_token}"
        
        # 合并参数
        data = {
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.kwargs.get('temperature', 0.7))
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['result']
    
    def is_available(self) -> bool:
        return self.api_key is not None and self.secret_key is not None


class AlibabaClient(BaseLLMClient):
    """阿里通义千问系列"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-turbo",
        **kwargs
    ):
        self.api_key = api_key or os.getenv('ALIBABA_API_KEY')
        self.model = model
        self.kwargs = kwargs
        self._client = None
    
    def _get_client(self):
        """延迟加载通义千问客户端（使用 OpenAI 兼容接口）"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        
        # 合并参数
        params = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', self.kwargs.get('temperature', 0.7)),
            'max_tokens': kwargs.get('max_tokens', self.kwargs.get('max_tokens', 500))
        }
        
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    def is_available(self) -> bool:
        return self.api_key is not None


# ==================== 工厂函数 ====================

def get_provider_client(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
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
    # 提供商映射
    providers = {
        'openai': OpenAIClient,
        'anthropic': AnthropicClient,
        'gemini': GeminiClient,
        'mistral': MistralClient,
        'deepseek': DeepSeekClient,
        'zhipu': ZhipuClient,
        'baidu': BaiduClient,
        'alibaba': AlibabaClient
    }
    
    # 获取提供商类
    provider_class = providers.get(provider.lower())
    if provider_class is None:
        raise ValueError(f"不支持的 LLM 提供商: {provider}。支持的提供商: {list(providers.keys())}")
    
    # 创建客户端
    return provider_class(api_key=api_key, model=model, **kwargs)
