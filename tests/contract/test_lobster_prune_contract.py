"""
契约测试：lobster_prune MCP 工具

验证 lobster_prune 工具的响应结构符合 MCP 协议规范。
lobster_prune 用于删除已标记为 decayed 的消息，释放存储空间（破坏性操作）。

响应格式：
- content[0].text 包含 JSON 字符串
- 必需字段：dry_run, decayed_count (dry_run) 或 deleted_count (实际删除)
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server, sample_conversation_id):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 lobster_prune 工具（dry_run 模式）
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_prune",
                "arguments": {
                    "conversation_id": sample_conversation_id,
                    "dry_run": True
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
        assert "dry_run" in result, "Response must have 'dry_run' field"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server, sample_conversation_id):
    """验证字段类型正确"""
    async def run_test():
        # 调用 lobster_prune 工具（dry_run 模式）
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_prune",
                "arguments": {
                    "conversation_id": sample_conversation_id,
                    "dry_run": True
                }
            }
        })
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段类型
        assert isinstance(result["dry_run"], bool), "'dry_run' must be a boolean"
        
        # 验证 dry_run 模式的字段
        if result["dry_run"]:
            assert "decayed_count" in result, "dry_run mode must have 'decayed_count' field"
            assert isinstance(result["decayed_count"], int), "'decayed_count' must be an integer"
    
    asyncio.run(run_test())


def test_edge_case_missing_conversation_id(mcp_server):
    """验证边界情况：缺少 conversation_id"""
    async def run_test():
        # 不提供 conversation_id（应该失败）
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_prune",
                "arguments": {
                    "dry_run": True
                }
            }
        })
        
        # 验证响应结构（可能是标准 MCP 响应或错误响应）
        if "content" in response:
            assert response["content"][0]["type"] == "text"
            # 解析 JSON 响应
            result = json.loads(response["content"][0]["text"])
            # 应该返回错误信息或字典结构
            assert isinstance(result, dict), "Should return a dictionary"
        else:
            # 错误响应格式：{"error": "..."}
            assert "error" in response, "Should return error when conversation_id is missing"
    
    asyncio.run(run_test())
