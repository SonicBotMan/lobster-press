"""
契约测试：lobster_status MCP 工具

验证 lobster_status 工具的响应结构符合 MCP 协议规范。
lobster_status 返回系统健康报告，包含记忆分布、压缩统计等信息。

响应格式：
- content[0].text 包含 JSON 字符串
- 必需字段：version, tier_distribution
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 lobster_status 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_status",
                "arguments": {}
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
        assert "version" in result, "Response must have 'version' field"
        assert "tier_distribution" in result, "Response must have 'tier_distribution' field"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        # 调用 lobster_status 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_status",
                "arguments": {}
            }
        })
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段类型
        assert isinstance(result["version"], str), "'version' must be a string"
        assert isinstance(result["tier_distribution"], dict), "'tier_distribution' must be a dictionary"
        
        # 验证可选字段类型
        if "entity_count" in result:
            assert isinstance(result["entity_count"], int), "'entity_count' must be an integer"
        
        if "correction_count" in result:
            assert isinstance(result["correction_count"], int), "'correction_count' must be an integer"
    
    asyncio.run(run_test())


def test_edge_case_with_conversation_id(mcp_server):
    """验证边界情况：指定 conversation_id"""
    async def run_test():
        # 使用指定的 conversation_id
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_status",
                "arguments": {
                    "conversation_id": "conv_test_001"
                }
            }
        })
        
        # 验证响应结构
        assert "content" in response
        assert response["content"][0]["type"] == "text"
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段存在
        assert "version" in result
        assert "tier_distribution" in result
        assert isinstance(result["tier_distribution"], dict)
    
    asyncio.run(run_test())
