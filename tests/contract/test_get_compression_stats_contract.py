"""
契约测试：get_compression_stats MCP 工具

验证 get_compression_stats 工具的响应结构符合 MCP 协议规范。
get_compression_stats 用于获取压缩统计数据。

响应格式：
- content[0].text 包含 JSON 字符串
- 必需字段：stats, config
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 get_compression_stats 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "get_compression_stats",
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
        assert "stats" in result, "Response must have 'stats' field"
        assert "config" in result, "Response must have 'config' field"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        # 调用 get_compression_stats 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "get_compression_stats",
                "arguments": {}
            }
        })
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段类型
        assert isinstance(result["stats"], dict), "'stats' must be a dictionary"
        assert isinstance(result["config"], dict), "'config' must be a dictionary"
        
        # 验证 stats 子字段
        if "total_compressions" in result["stats"]:
            assert isinstance(result["stats"]["total_compressions"], int), "'total_compressions' must be an integer"
        
        if "total_messages_processed" in result["stats"]:
            assert isinstance(result["stats"]["total_messages_processed"], int), "'total_messages_processed' must be an integer"
    
    asyncio.run(run_test())


def test_edge_case_no_arguments(mcp_server):
    """验证边界情况：无参数调用"""
    async def run_test():
        # 不传递任何参数
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "get_compression_stats",
                "arguments": {}
            }
        })
        
        # 验证响应结构
        assert "content" in response
        assert response["content"][0]["type"] == "text"
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 应该返回统计数据
        assert "stats" in result
        assert "config" in result
        assert isinstance(result["stats"], dict)
        assert isinstance(result["config"], dict)
    
    asyncio.run(run_test())
