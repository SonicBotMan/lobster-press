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
        # ingested 是整数类型，表示成功入库的消息数量
        assert isinstance(result["ingested"], int), "'ingested' must be an integer"
    
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
        # 空消息列表应该返回 ingested=0
        assert result["ingested"] == 0, "Empty messages should result in ingested=0"
        assert "message" in result, "Should have a message field"
    
    asyncio.run(run_test())
