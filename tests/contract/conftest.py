"""
契约测试共享 fixtures
验证 MCP 工具响应结构的一致性
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import tempfile
import os

from src.database import LobsterDatabase
from src.llm_client import MockLLMClient
from src.dag_compressor import DAGCompressor
from mcp_server.lobster_mcp_server import LobsterPressMCPServer


@pytest.fixture
def temp_db():
    """创建临时数据库用于测试"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = LobsterDatabase(db_path)
    yield db
    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_llm():
    """创建 Mock LLM 客户端用于测试"""
    return MockLLMClient()


@pytest.fixture
def compressor(temp_db, mock_llm):
    """创建 DAGCompressor 实例"""
    return DAGCompressor(
        db=temp_db,
        fresh_tail_count=32,
        leaf_chunk_tokens=20000,
        condensed_min_fanout=4,
        llm_client=mock_llm
    )


@pytest.fixture
def mcp_server(temp_db, mock_llm):
    """创建 LobsterPressMCPServer 实例"""
    server = LobsterPressMCPServer(
        db_path=temp_db.db_path
    )
    # Manually inject the mock LLM client
    server._llm_client = mock_llm
    return server


@pytest.fixture
def sample_conversation_id():
    """示例对话 ID"""
    return "conv_test_001"


@pytest.fixture
def sample_messages():
    """示例消息列表"""
    return [
        {
            "id": "msg_001",
            "role": "user",
            "content": "我们决定使用 PostgreSQL 作为主数据库",
            "timestamp": "2026-03-17T10:00:00Z"
        },
        {
            "id": "msg_002",
            "role": "assistant",
            "content": "好的，我会记住这个决定。PostgreSQL 是一个可靠的选择，特别是对于需要 ACID 事务的场景。",
            "timestamp": "2026-03-17T10:01:00Z"
        },
        {
            "id": "msg_003",
            "role": "user",
            "content": "另外，我们采用 React 18 作为前端框架",
            "timestamp": "2026-03-17T10:02:00Z"
        },
        {
            "id": "msg_004",
            "role": "assistant",
            "content": "明白了。React 18 带来了很多新特性，比如并发渲染和自动批处理。",
            "timestamp": "2026-03-17T10:03:00Z"
        },
        {
            "id": "msg_005",
            "role": "user",
            "content": "改用 MongoDB，因为需要文档灵活性",
            "timestamp": "2026-03-17T10:05:00Z"
        }
    ]
