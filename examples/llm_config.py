#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress LLM 配置示例

展示如何配置各种 LLM 提供商

Author: LobsterPress Team
Version: v3.2.0
"""

# ==================== 方式1: 使用环境变量（推荐）====================

"""
配置环境变量（在 ~/.bashrc 或 .env 文件中）：

# OpenAI
export LOBSTER_LLM_PROVIDER=openai
export LOBSTER_LLM_API_KEY=sk-xxx
export LOBSTER_LLM_MODEL=gpt-4o-mini

# DeepSeek（国内推荐）
export LOBSTER_LLM_PROVIDER=deepseek
export LOBSTER_LLM_API_KEY=sk-xxx
export LOBSTER_LLM_MODEL=deepseek-chat

# 智谱 GLM（国内推荐）
export LOBSTER_LLM_PROVIDER=zhipu
export LOBSTER_LLM_API_KEY=xxx.xxx
export LOBSTER_LLM_MODEL=glm-4-flash

# 阿里通义千问
export LOBSTER_LLM_PROVIDER=alibaba
export LOBSTER_LLM_API_KEY=sk-xxx
export LOBSTER_LLM_MODEL=qwen-turbo

# Anthropic Claude
export LOBSTER_LLM_PROVIDER=anthropic
export LOBSTER_LLM_API_KEY=sk-ant-xxx
export LOBSTER_LLM_MODEL=claude-3-5-sonnet-20241022

# Google Gemini
export LOBSTER_LLM_PROVIDER=gemini
export LOBSTER_LLM_API_KEY=xxx
export LOBSTER_LLM_MODEL=gemini-pro

# Mistral
export LOBSTER_LLM_PROVIDER=mistral
export LOBSTER_LLM_API_KEY=xxx
export LOBSTER_LLM_MODEL=mistral-small-latest

# 百度文心（需要两个密钥）
export LOBSTER_LLM_PROVIDER=baidu
export BAIDU_API_KEY=xxx
export BAIDU_SECRET_KEY=xxx
export LOBSTER_LLM_MODEL=ernie-speed-8k
"""

# 使用环境变量（最简单）
from src.llm_client import get_llm_client

client = get_llm_client()
summary = client.generate("总结这段文本...")


# ==================== 方式2: 显式配置 ====================

from src.llm_client import create_llm_client

# OpenAI
openai_client = create_llm_client(
    provider='openai',
    api_key='sk-xxx',
    model='gpt-4o-mini'
)

# DeepSeek（国内推荐，性价比高）
deepseek_client = create_llm_client(
    provider='deepseek',
    api_key='sk-xxx',
    model='deepseek-chat'
)

# 智谱 GLM（国内推荐，免费额度大）
zhipu_client = create_llm_client(
    provider='zhipu',
    api_key='xxx.xxx',
    model='glm-4-flash'
)

# 阿里通义千问
alibaba_client = create_llm_client(
    provider='alibaba',
    api_key='sk-xxx',
    model='qwen-turbo'
)

# Anthropic Claude
claude_client = create_llm_client(
    provider='anthropic',
    api_key='sk-ant-xxx',
    model='claude-3-5-sonnet-20241022'
)

# Google Gemini
gemini_client = create_llm_client(
    provider='gemini',
    api_key='xxx',
    model='gemini-pro'
)

# Mistral
mistral_client = create_llm_client(
    provider='mistral',
    api_key='xxx',
    model='mistral-small-latest'
)

# 百度文心（需要两个密钥）
baidu_client = create_llm_client(
    provider='baidu',
    api_key='xxx',
    secret_key='xxx',  # 注意：百度需要 secret_key
    model='ernie-speed-8k'
)


# ==================== 方式3: 在 DAGCompressor 中使用 ====================

from src.database import LobsterDatabase
from src.dag_compressor import DAGCompressor

# 创建数据库
db = LobsterDatabase('lobster.db')

# 创建 LLM 客户端（使用环境变量）
llm_client = get_llm_client()

# 创建 DAGCompressor
compressor = DAGCompressor(
    db,
    llm_client=llm_client  # 传入 LLM 客户端
)

# 执行压缩（自动使用 LLM 生成高质量摘要）
compressor.leaf_compact(conversation_id='conv_123')
compressor.condensed_compact(conversation_id='conv_123')


# ==================== 方式4: 自定义客户端 ====================

from src.llm_client import BaseLLMClient

class MyCustomLLMClient(BaseLLMClient):
    """自定义 LLM 客户端"""
    
    def __init__(self, my_api_key: str):
        self.my_api_key = my_api_key
    
    def generate(self, prompt: str, **kwargs) -> str:
        # 实现你的逻辑
        # ...
        return "生成的摘要"
    
    def is_available(self) -> bool:
        return self.my_api_key is not None

# 使用自定义客户端
custom_client = MyCustomLLMClient(my_api_key='xxx')
compressor = DAGCompressor(db, llm_client=custom_client)


# ==================== 推荐配置（按场景）====================

"""
1. 国内用户，追求性价比：
   - DeepSeek（便宜，质量高）
   - 智谱 GLM（免费额度大，适合测试）

2. 国内用户，追求质量：
   - DeepSeek（质量接近 GPT-4）
   - 阿里通义千问（中文能力强）

3. 国际用户：
   - OpenAI GPT-4o-mini（性价比高）
   - Anthropic Claude 3.5 Sonnet（质量最高）
   - Google Gemini Pro（免费额度大）

4. 测试/开发：
   - Mock 客户端（无需 API，快速测试）
   - 智谱 GLM（免费额度大）
"""


# ==================== 故障排除 ====================

"""
Q: 提示 "请安装 xxx"？
A: 运行 pip install xxx 安装对应 SDK

Q: 提示 API key 无效？
A: 检查环境变量是否正确设置：
   echo $LOBSTER_LLM_API_KEY

Q: 国内访问 OpenAI 慢？
A: 使用 DeepSeek 或智谱 GLM，国内访问快

Q: 如何查看支持哪些提供商？
A: 运行：
   from src.llm_providers import get_provider_client
   print(list(providers.keys()))

Q: 百度文心为什么需要两个密钥？
A: 百度使用 OAuth2.0，需要 API Key 和 Secret Key

Q: 如何降级到提取式摘要？
A: 不配置 LLM 客户端（llm_client=None），自动降级
"""
