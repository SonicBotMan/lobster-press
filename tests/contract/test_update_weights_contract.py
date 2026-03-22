"""
契约测试：update_weights MCP 工具

验证 update_weights 工具的响应结构符合 MCP 协议规范。
update_weights 用于更新消息类型权重配置。

响应格式：
- content[0].text 包含 JSON 字符串
- 必需字段：status, updated_weights
"""
import json
import asyncio


def test_response_has_required_fields(mcp_server):
    """验证响应包含必需字段"""
    async def run_test():
        # 调用 update_weights 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "update_weights",
                "arguments": {
                    "weights": {
                        "decision": 0.3,
                        "error": 0.25
                    }
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
        assert "status" in result, "Response must have 'status' field"
        assert "updated_weights" in result, "Response must have 'updated_weights' field"
    
    asyncio.run(run_test())


def test_response_field_types(mcp_server):
    """验证字段类型正确"""
    async def run_test():
        # 调用 update_weights 工具
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "update_weights",
                "arguments": {
                    "weights": {
                        "config": 0.2,
                        "preference": 0.15
                    }
                }
            }
        })
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 验证必需字段类型
        assert isinstance(result["status"], str), "'status' must be a string"
        assert isinstance(result["updated_weights"], dict), "'updated_weights' must be a dictionary"
        
        # 验证权重值类型
        for key, value in result["updated_weights"].items():
            assert isinstance(value, (int, float)), f"Weight '{key}' must be a number"
    
    asyncio.run(run_test())


def test_edge_case_partial_weights(mcp_server):
    """验证边界情况：部分权重更新"""
    async def run_test():
        # 只更新部分权重
        response = await mcp_server.handle_request({
            "method": "tools/call",
            "params": {
                "name": "update_weights",
                "arguments": {
                    "weights": {
                        "context": 0.05
                    }
                }
            }
        })
        
        # 验证响应结构
        assert "content" in response
        assert response["content"][0]["type"] == "text"
        
        # 解析 JSON 响应
        result = json.loads(response["content"][0]["text"])
        
        # 应该返回成功状态和更新后的权重
        assert "status" in result
        assert "updated_weights" in result
        assert result["status"] == "success", "Should return success status"
        assert "context" in result["updated_weights"], "Should include updated weight"
    
    asyncio.run(run_test())
