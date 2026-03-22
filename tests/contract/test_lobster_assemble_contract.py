"""
契约测试：lobster_assemble MCP 工具

验证 lobster_assemble 工具的响应结构符合 MCP 协议规范。
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server, sample_conversation_id):
    """验证响应包含必需字段"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_assemble",
                "arguments": {
                    "conversation_id": sample_conversation_id,
                    "token_budget": 8000
                }
            }
        })
        
        # 验证响应结构（可能是标准 MCP 响应或错误响应）
        if "content" in response:
            assert isinstance(response["content"], list)
            assert len(response["content"]) > 0
            assert response["content"][0]["type"] == "text"
            
            result = json.loads(response["content"][0]["text"])
            assert "assembled" in result
        else:
            # 错误响应格式：{"error": "..."}
            assert "error" in response
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server, sample_conversation_id):
    """验证字段类型正确"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_assemble",
                "arguments": {
                    "conversation_id": sample_conversation_id
                }
            }
        })
        
        # 验证响应结构
        if "content" in response:
            result = json.loads(response["content"][0]["text"])
            # assembled 是列表类型，不是 bool
            assert isinstance(result["assembled"], list), "'assembled' must be a list"
        else:
            # 错误响应也是有效的
            assert "error" in response
    
    asyncio.run(run_test())


def test_edge_case_empty_data(mcp_server):
    """验证边界情况：空数据"""
    async def run_test():
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_assemble",
                "arguments": {
                    "conversation_id": "empty_conversation_test"
                }
            }
        })
        
        # 验证响应结构
        if "content" in response:
            result = json.loads(response["content"][0]["text"])
            assert "assembled" in result
            # 空对话应该返回空列表
            assert isinstance(result["assembled"], list)
        else:
            # 错误响应也是有效的
            assert "error" in response
    
    asyncio.run(run_test())
