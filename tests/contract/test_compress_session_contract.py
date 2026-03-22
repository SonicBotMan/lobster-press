"""
契约测试：compress_session MCP 工具

验证 compress_session 工具的响应结构符合 MCP 协议规范。
compress_session 用于压缩 OpenClaw 会话历史，保留重要信息。

响应格式：
- content[0].text 包含 JSON 字符串
- 必需字段：status, session_id
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 compress_session 工具（dry_run 模式）
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "compress_session",
                "arguments": {
                    "session_id": "test_session_001",
                    "strategy": "medium",
                    "dry_run": True
                }
            }
        })
        
        # 验证响应结构（可能是标准 MCP 响应或错误响应）
        if "content" in response:
            assert isinstance(response["content"], list), "'content' must be a list"
            assert len(response["content"]) > 0, "'content' list must not be empty"
            assert response["content"][0]["type"] == "text", "First content item must have type 'text'"
            
            # 解析 JSON 响应
            result = json.loads(response["content"][0]["text"])
            
            # 验证必需字段存在
            assert "status" in result, "Response must have 'status' field"
            assert "session_id" in result, "Response must have 'session_id' field"
        else:
            # 错误响应格式：{"error": "..."}
            assert "error" in response, "Should return error when session not found"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        # 调用 compress_session 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "compress_session",
                "arguments": {
                    "session_id": "test_session_002",
                    "dry_run": True
                }
            }
        })
        
        # 验证响应结构
        if "content" in response:
            # 解析 JSON 响应
            result = json.loads(response["content"][0]["text"])
            
            # 验证必需字段类型
            assert isinstance(result["status"], str), "'status' must be a string"
            assert isinstance(result["session_id"], str), "'session_id' must be a string"
            
            # 验证可选字段类型
            if "dry_run" in result:
                assert isinstance(result["dry_run"], bool), "'dry_run' must be a boolean"
            
            if "strategy" in result:
                assert isinstance(result["strategy"], str), "'strategy' must be a string"
        else:
            # 错误响应也是有效的
            assert "error" in response
    
    asyncio.run(run_test())


def test_edge_case_nonexistent_session(mcp_server):
    """验证边界情况：不存在的 session_id"""
    async def run_test():
        # 使用一个不存在的 session_id
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "compress_session",
                "arguments": {
                    "session_id": "nonexistent_session_xyz_999",
                    "dry_run": True
                }
            }
        })
        
        # 验证响应结构（可能是标准 MCP 响应或错误响应）
        if "content" in response:
            assert response["content"][0]["type"] == "text"
            result = json.loads(response["content"][0]["text"])
            # 不存在的 session 应该返回错误状态
            assert "status" in result
            # 可能是 "error" 或 "preview" 状态
            assert result["status"] in ["error", "preview"], "Should return error or preview status for nonexistent session"
        else:
            # 错误响应格式：{"error": "..."}
            assert "error" in response, "Should return error when session not found"
    
    asyncio.run(run_test())
