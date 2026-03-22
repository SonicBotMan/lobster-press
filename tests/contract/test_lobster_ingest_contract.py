"""
契约测试：lobster_ingest MCP 工具
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_ingest",
                "arguments": {
                    "conversation_id": "test_conv",
                    "messages": []
                }
            }
        })
        
        assert "content" in response
        assert isinstance(response["content"], list)
        assert response["content"][0]["type"] == "text"
        
        result = json.loads(response["content"][0]["text"])
        assert "ingested" in result
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_ingest",
                "arguments": {
                    "conversation_id": "test_conv",
                    "messages": []
                }
            }
        })
        
        result = json.loads(response["content"][0]["text"])
        assert isinstance(result["ingested"], bool)
    
    asyncio.run(run_test())


def test_edge_case_empty_messages(mcp_server):
    """验证边界情况：空消息列表"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_ingest",
                "arguments": {
                    "conversation_id": "empty_conv",
                    "messages": []
                }
            }
        })
        
        result = json.loads(response["content"][0]["text"])
        assert result["ingested"] is True
    
    asyncio.run(run_test())
