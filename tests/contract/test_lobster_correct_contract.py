"""
契约测试：lobster_correct MCP 工具

验证 lobster_correct 工具的响应结构符合 MCP 协议规范。
lobster_correct 用于应用记忆纠错（修改或删除错误记忆）。

响应格式：
- content[0].text 包含 JSON 字符串
- 返回纠错结果或错误信息
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 lobster_correct 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_correct",
                "arguments": {
                    "target_type": "message",
                    "target_id": "msg_test_001",
                    "correction_type": "content",
                    "old_value": "PostgreSQL",
                    "new_value": "MongoDB",
                    "reason": "Database choice updated"
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
        
        # 验证返回的是字典结构
        assert isinstance(result, dict), "Response must be a dictionary"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        # 调用 lobster_correct 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_correct",
                "arguments": {
                    "target_type": "summary",
                    "target_id": "summary_test_001",
                    "correction_type": "metadata"
                }
            }
        })
        
        # 验证响应结构（可能是标准 MCP 响应或错误响应）
        if "content" in response:
            # 解析 JSON 响应
            result = json.loads(response["content"][0]["text"])
            
            # 验证返回的是字典类型
            assert isinstance(result, dict), "Response must be a dictionary"
        else:
            # 错误响应也是有效的
            assert "error" in response
    
    asyncio.run(run_test())


def test_edge_case_nonexistent_target(mcp_server):
    """验证边界情况：不存在的 target_id"""
    async def run_test():
        # 使用一个不存在的 target_id
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "lobster_correct",
                "arguments": {
                    "target_type": "message",
                    "target_id": "msg_nonexistent_xyz_999",
                    "correction_type": "delete"
                }
            }
        })
        
        # 验证响应结构
        assert "content" in response
        assert response["content"][0]["type"] == "text"
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 应该返回字典结构（可能是错误信息或失败状态）
        assert isinstance(result, dict), "Should return a dictionary even for nonexistent target"
    
    asyncio.run(run_test())
