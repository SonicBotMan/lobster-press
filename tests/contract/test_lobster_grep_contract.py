"""
契约测试：lobster_grep MCP 工具

验证 lobster_grep 工具的响应结构符合 MCP 协议规范。
lobster_grep 是 FTS5 全文搜索工具，支持 TF-IDF 重排序。

响应格式：
- content[0].text 包含 JSON 字符串
- 必需字段：results (array)
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 lobster_grep 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_grep",
                "arguments": {
                    "query": "PostgreSQL",
                    "limit": 5
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
        assert "results" in result, "Response must have 'results' field"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        # 调用 lobster_grep 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_grep",
                "arguments": {
                    "query": "database",
                    "limit": 3
                }
            }
        })
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段类型
        assert isinstance(result["results"], list), "'results' must be a list"
    
    asyncio.run(run_test())


def test_edge_case_no_results(mcp_server):
    """验证边界情况：无搜索结果"""
    async def run_test():
        # 使用一个不太可能匹配的关键词
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_grep",
                "arguments": {
                    "query": "xyznonexistent123",
                    "limit": 5
                }
            }
        })
        
        # 验证响应结构
        assert "content" in response
        assert response["content"][0]["type"] == "text"
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 应该返回空结果列表
        assert "results" in result
        assert isinstance(result["results"], list)
        assert len(result["results"]) == 0, "Should return empty results for non-matching query"
    
    asyncio.run(run_test())
