#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress MCP Server v1.0.0
基于 Model Context Protocol (MCP) 的压缩服务

Issue: #42 - v2.0 架构演进：向 MCP Server 演进
Author: LobsterPress Team
Version: v1.0.0
"""

import sys
import json
import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]


class LobsterPressMCPServer:
    """LobsterPress MCP Server"""
    
    def __init__(self, sessions_dir: str = None):
        """初始化 MCP Server
        
        Args:
            sessions_dir: 会话目录
        """
        self.sessions_dir = Path(sessions_dir or os.path.expanduser("~/.openclaw/agents/main/sessions"))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # 统计数据
        self.stats = {
            "total_compressions": 0,
            "total_messages_processed": 0,
            "total_tokens_saved": 0,
            "last_compression": None
        }
        
        # 配置
        self.config = {
            "weights": {
                "decision": 0.3,
                "error": 0.25,
                "config": 0.2,
                "preference": 0.15,
                "context": 0.05,
                "chitchat": 0.02,
                "other": 0.03
            },
            "strategy": "medium",
            "max_tokens": 800000
        }
        
        # 注册工具
        self.tools = self._register_tools()
    
    def _register_tools(self) -> List[MCPTool]:
        """注册 MCP 工具"""
        return [
            MCPTool(
                name="compress_session",
                description="压缩 OpenClaw 会话历史，保留重要信息",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话 ID（文件名，不含扩展名）"
                        },
                        "strategy": {
                            "type": "string",
                            "enum": ["light", "medium", "aggressive"],
                            "description": "压缩策略：light（轻度）、medium（中度）、aggressive（激进）",
                            "default": "medium"
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "是否仅预览，不实际压缩",
                            "default": False
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            MCPTool(
                name="preview_compression",
                description="预览压缩效果，显示将要保留和删除的消息",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话 ID"
                        },
                        "strategy": {
                            "type": "string",
                            "enum": ["light", "medium", "aggressive"],
                            "default": "medium"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            MCPTool(
                name="get_compression_stats",
                description="获取压缩统计数据",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            MCPTool(
                name="update_weights",
                description="更新消息类型权重配置",
                input_schema={
                    "type": "object",
                    "properties": {
                        "weights": {
                            "type": "object",
                            "description": "消息类型权重",
                            "properties": {
                                "decision": {"type": "number"},
                                "error": {"type": "number"},
                                "config": {"type": "number"},
                                "preference": {"type": "number"},
                                "context": {"type": "number"},
                                "chitchat": {"type": "number"}
                            }
                        }
                    },
                    "required": ["weights"]
                }
            ),
            MCPTool(
                name="list_sessions",
                description="列出所有可压缩的会话",
                input_schema={
                    "type": "object",
                    "properties": {
                        "min_tokens": {
                            "type": "integer",
                            "description": "最小 Token 数阈值",
                            "default": 10000
                        }
                    },
                    "required": []
                }
            )
        ]
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 MCP 请求
        
        Args:
            request: MCP 请求
        
        Returns:
            MCP 响应
        """
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "tools/list":
                return {
                    "tools": [asdict(tool) for tool in self.tools]
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                result = await self._call_tool(tool_name, arguments)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            
            elif method == "resources/list":
                return await self._list_resources()
            
            elif method == "resources/read":
                return await self._read_resource(params.get("uri"))
            
            else:
                return {"error": f"Unknown method: {method}"}
        
        except Exception as e:
            return {"error": str(e)}
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if tool_name == "compress_session":
            return await self._compress_session(
                arguments.get("session_id"),
                arguments.get("strategy", "medium"),
                arguments.get("dry_run", False)
            )
        
        elif tool_name == "preview_compression":
            return await self._preview_compression(
                arguments.get("session_id"),
                arguments.get("strategy", "medium")
            )
        
        elif tool_name == "get_compression_stats":
            return self._get_stats()
        
        elif tool_name == "update_weights":
            return self._update_weights(arguments.get("weights", {}))
        
        elif tool_name == "list_sessions":
            return await self._list_sessions(arguments.get("min_tokens", 10000))
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _compress_session(self, session_id: str, strategy: str, dry_run: bool) -> Dict[str, Any]:
        """压缩会话"""
        session_file = self.sessions_dir / f"{session_id}.jsonl"
        
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        
        # 读取会话
        messages = []
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        
        total_messages = len(messages)
        
        # 估算 Token 数
        estimated_tokens = self._estimate_tokens(messages)
        
        # 根据策略决定保留比例
        retention_ratios = {
            "light": 0.7,
            "medium": 0.5,
            "aggressive": 0.3
        }
        retention_ratio = retention_ratios.get(strategy, 0.5)
        
        # 计算要保留的消息数
        keep_count = int(total_messages * retention_ratio)
        
        # 评分并排序（简化版）
        scored_messages = []
        for i, msg in enumerate(messages):
            score = self._score_message(msg)
            scored_messages.append((i, score, msg))
        
        # 按分数排序，保留高分消息
        scored_messages.sort(key=lambda x: x[1], reverse=True)
        keep_indices = set(x[0] for x in scored_messages[:keep_count])
        
        # 按原始顺序保留
        compressed_messages = [msg for i, msg in enumerate(messages) if i in keep_indices]
        
        # 计算压缩后的 Token 数
        compressed_tokens = self._estimate_tokens(compressed_messages)
        tokens_saved = estimated_tokens - compressed_tokens
        
        if dry_run:
            return {
                "status": "preview",
                "session_id": session_id,
                "original_messages": total_messages,
                "compressed_messages": len(compressed_messages),
                "original_tokens": estimated_tokens,
                "compressed_tokens": compressed_tokens,
                "tokens_saved": tokens_saved,
                "compression_ratio": f"{(tokens_saved / estimated_tokens * 100):.1f}%" if estimated_tokens > 0 else "0%",
                "strategy": strategy
            }
        
        # 实际写入（备份原文件）
        backup_file = self.sessions_dir / f"{session_id}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        session_file.rename(backup_file)
        
        with open(session_file, 'w', encoding='utf-8') as f:
            for msg in compressed_messages:
                f.write(json.dumps(msg, ensure_ascii=False) + '\n')
        
        # 更新统计
        self.stats["total_compressions"] += 1
        self.stats["total_messages_processed"] += total_messages
        self.stats["total_tokens_saved"] += tokens_saved
        self.stats["last_compression"] = datetime.now().isoformat()
        
        return {
            "status": "success",
            "session_id": session_id,
            "original_messages": total_messages,
            "compressed_messages": len(compressed_messages),
            "original_tokens": estimated_tokens,
            "compressed_tokens": compressed_tokens,
            "tokens_saved": tokens_saved,
            "compression_ratio": f"{(tokens_saved / estimated_tokens * 100):.1f}%" if estimated_tokens > 0 else "0%",
            "strategy": strategy,
            "backup_file": str(backup_file)
        }
    
    async def _preview_compression(self, session_id: str, strategy: str) -> Dict[str, Any]:
        """预览压缩效果"""
        return await self._compress_session(session_id, strategy, dry_run=True)
    
    def _get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        return {
            "stats": self.stats,
            "config": self.config
        }
    
    def _update_weights(self, weights: Dict[str, float]) -> Dict[str, Any]:
        """更新权重配置"""
        # 验证权重
        for key, value in weights.items():
            if key in self.config["weights"]:
                self.config["weights"][key] = value
        
        return {
            "status": "success",
            "updated_weights": self.config["weights"]
        }
    
    async def _list_sessions(self, min_tokens: int) -> Dict[str, Any]:
        """列出会话"""
        sessions = []
        
        for session_file in self.sessions_dir.glob("*.jsonl"):
            if session_file.name.endswith((".backup.", ".reset.", ".deleted.")):
                continue
            
            # 估算 Token 数
            messages = []
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))
            
            estimated_tokens = self._estimate_tokens(messages)
            
            if estimated_tokens >= min_tokens:
                sessions.append({
                    "session_id": session_file.stem,
                    "messages": len(messages),
                    "estimated_tokens": estimated_tokens,
                    "file_size": session_file.stat().st_size,
                    "modified": datetime.fromtimestamp(session_file.stat().st_mtime).isoformat()
                })
        
        # 按 Token 数排序
        sessions.sort(key=lambda x: x["estimated_tokens"], reverse=True)
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
    
    async def _list_resources(self) -> Dict[str, Any]:
        """列出资源"""
        resources = []
        
        for session_file in self.sessions_dir.glob("*.jsonl"):
            if not session_file.name.endswith((".backup.", ".reset.", ".deleted.")):
                resources.append({
                    "uri": f"lobster://sessions/{session_file.stem}",
                    "name": session_file.stem,
                    "mimeType": "application/jsonl"
                })
        
        return {"resources": resources}
    
    async def _read_resource(self, uri: str) -> Dict[str, Any]:
        """读取资源"""
        if not uri.startswith("lobster://sessions/"):
            raise ValueError(f"Invalid resource URI: {uri}")
        
        session_id = uri.replace("lobster://sessions/", "")
        session_file = self.sessions_dir / f"{session_id}.jsonl"
        
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        
        with open(session_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/jsonl",
                    "text": content
                }
            ]
        }
    
    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """估算 Token 数"""
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total_chars += len(part["text"])
        
        # 简单估算：3 字符 = 1 token
        return total_chars // 3
    
    def _score_message(self, msg: Dict) -> float:
        """评分消息重要性"""
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        
        content_lower = content.lower()
        score = 0.0
        
        # 关键词评分
        patterns = {
            "decision": ["决定", "方案", "选择", "决定采用", "decide", "choose"],
            "error": ["错误", "失败", "异常", "error", "fail", "exception"],
            "config": ["配置", "设置", "更新", "config", "setting", "update"],
            "preference": ["偏好", "喜欢", "希望", "prefer", "like", "want"],
        }
        
        for category, keywords in patterns.items():
            for keyword in keywords:
                if keyword in content_lower:
                    score += self.config["weights"].get(category, 0.1)
        
        return score


async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LobsterPress MCP Server")
    parser.add_argument("--sessions-dir", help="会话目录")
    parser.add_argument("--test", action="store_true", help="测试模式")
    
    args = parser.parse_args()
    
    server = LobsterPressMCPServer(args.sessions_dir)
    
    if args.test:
        # 测试模式
        print("=== LobsterPress MCP Server 测试 ===")
        print("\n可用工具:")
        for tool in server.tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # 测试 list_sessions
        result = await server._call_tool("list_sessions", {"min_tokens": 1000})
        print(f"\n找到 {result['total']} 个可压缩会话")
        for session in result["sessions"][:3]:
            print(f"  - {session['session_id']}: {session['estimated_tokens']} tokens")
        
        print("\n✅ MCP Server 正常工作")
    else:
        # MCP 协议模式（读取 stdin）
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = await server.handle_request(request)
                print(json.dumps(response))
            except json.JSONDecodeError as e:
                print(json.dumps({"error": f"Invalid JSON: {e}"}))


if __name__ == "__main__":
    asyncio.run(main())
