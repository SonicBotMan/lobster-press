"""
契约测试：lobster_assemble MCP 工具

验证 lobster_assemble 工具的响应结构符合 MCP 协议规范。
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_assemble",
                "arguments": {}
            }
        })
        
        assert "content" in response
        assert isinstance(response["content"], list)
        assert len(response["content"]) > 0
        assert response["content"][0]["type"] == "text"
        
        result = json.loads(response["content"][0]["text"])
        assert "assembled" in result
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_assemble",
                "arguments": {}
            }
        })
        
        result = json.loads(response["content"][0]["text"])
        assert isinstance(result["assembled"], bool)
    
    asyncio.run(run_test())


def test_edge_case_empty_data(mcp_server):
    """验证边界情况：空数据"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_assemble",
                "arguments": {}
            }
        })
        
        result = json.loads(response["content"][0]["text"])
        assert "assembled" in result
        assert isinstance(result["assembled"], bool)
    
    asyncio.run(run_test())
