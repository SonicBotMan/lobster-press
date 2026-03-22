"""
契约测试：list_sessions MCP 工具

验证 list_sessions 工具的响应结构符合 MCP 协议规范。
list_sessions 用于列出所有可压缩的会话。

响应格式：
- content[0].text 包含 JSON 字符串
- 必需字段：sessions (array), total (int)
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 list_sessions 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "list_sessions",
                "arguments": {
                    "min_tokens": 10000
                }
            }
        })
        
        # 验证 MCP 响应结构
        assert "content" in response, "Response must have 'content' field"
        assert isinstance(response["content"], list), "'content' must be a list"
        assert len(response["content"]) > 0, "'content' list must not be empty"
        assert response["content"][0]["type"] == "text", "First content item must have type 'text'"
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段存在
        assert "sessions" in result, "Response must have 'sessions' field"
        assert "total" in result, "Response must have 'total' field"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        # 调用 list_sessions 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "list_sessions",
                "arguments": {
                    "min_tokens": 5000
                }
            }
        })
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段类型
        assert isinstance(result["sessions"], list), "'sessions' must be a list"
        assert isinstance(result["total"], int), "'total' must be an integer"
        
        # 验证 total 和 sessions 长度一致
        assert result["total"] == len(result["sessions"]), "'total' should match sessions list length"
    
    asyncio.run(run_test())


def test_edge_case_no_sessions(mcp_server):
    """验证边界情况：无符合条件的会话"""
    async def run_test():
        # 使用一个非常高的 min_tokens 阈值
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "list_sessions",
                "arguments": {
                    "min_tokens": 999999999
                }
            }
        })
        
        # 验证响应结构
        assert "content" in response
        assert response["content"][0]["type"] == "text"
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 应该返回空会话列表
        assert "sessions" in result
        assert "total" in result
        assert isinstance(result["sessions"], list)
        assert result["total"] == 0, "Should return 0 sessions with very high threshold"
        assert len(result["sessions"]) == 0, "Sessions list should be empty"
    
    asyncio.run(run_test())
