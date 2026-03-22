"""
契约测试：lobster_compress MCP 工具

验证 lobster_compress 工具的响应结构符合 MCP 协议规范。
lobster_compress 是 v3.3.0 引入的增量压缩工具。

响应格式：
- content[0].text 包含 JSON 字符串
- 必需字段：compressed (bool)
- 可选字段：tokens_saved (int), compression_ratio (float)
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server, sample_conversation_id):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 lobster_compress 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_compress",
                "arguments": {
                    "conversation_id": sample_conversation_id,
                    "token_budget": 8000
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
        assert "compressed" in result, "Response must have 'compressed' field"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server, sample_conversation_id):
    """验证字段类型正确"""
    async def run_test():
        # 调用 lobster_compress 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_compress",
                "arguments": {
                    "conversation_id": sample_conversation_id,
                    "token_budget": 8000
                }
            }
        })
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段类型
        assert isinstance(result["compressed"], bool), "'compressed' must be a boolean"
        
        # 验证可选字段类型（如果存在）
        if "tokens_saved" in result:
            assert isinstance(result["tokens_saved"], int), "'tokens_saved' must be an integer"
        
        if "compression_ratio" in result:
            assert isinstance(result["compression_ratio"], (int, float)), "'compression_ratio' must be a number"
    
    asyncio.run(run_test())


def test_edge_case_empty_conversation(mcp_server):
    """验证边界情况：空对话"""
    async def run_test():
        # 使用一个新的、不存在的 conversation_id
        empty_conversation_id = "conv_empty_test_12345"
        
        # 调用 lobster_compress 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_compress",
                "arguments": {
                    "conversation_id": empty_conversation_id,
                    "token_budget": 8000
                }
            }
        })
        
        # 验证响应结构
        assert "content" in response
        assert response["content"][0]["type"] == "text"
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 空对话应该返回 compressed: false
        assert "compressed" in result
        assert isinstance(result["compressed"], bool)
        assert result["compressed"] is False, "Empty conversation should return compressed=false"
    
    asyncio.run(run_test())
