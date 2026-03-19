#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress MCP Server
基于 Model Context Protocol (MCP) 的认知记忆压缩服务

Version: v3.5.1
Changelog: https://github.com/SonicBotMan/lobster-press/blob/master/CHANGELOG.md
"""

import sys
import json
import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# 添加 src/ 目录到 Python 模块搜索路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]


class LobsterPressMCPServer:
    """LobsterPress MCP Server"""
    
    def __init__(self, sessions_dir: str = None, db_path: str = None, llm_provider: str = None, llm_model: str = None):
        """初始化 MCP Server
        
        Args:
            sessions_dir: 会话目录
            db_path: LobsterPress 数据库路径
            llm_provider: LLM 提供商
            llm_model: LLM 模型名称
        """
        self.sessions_dir = Path(sessions_dir or os.path.expanduser("~/.openclaw/agents/main/sessions"))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # v3.2.2: OpenClaw 插件支持
        self.db_path = db_path or os.path.expanduser("~/.openclaw/lobster.db")
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self._db = None  # 懒加载数据库连接
        
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
            ),
            # v3.2.2: OpenClaw 插件工具
            MCPTool(
                name="lobster_grep",
                description="在 LobsterPress 记忆库中全文搜索历史对话（FTS5 + TF-IDF 重排序）",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词或短语"},
                        "conversation_id": {"type": "string", "description": "限定搜索范围的会话 ID（可选）"},
                        "limit": {"type": "integer", "description": "最多返回条数，默认 5", "default": 5}
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="lobster_describe",
                description="查看 LobsterPress 的 DAG 摘要层级结构",
                input_schema={
                    "type": "object",
                    "properties": {
                        "conversation_id": {"type": "string", "description": "会话 ID（可选，留空查全局）"}
                    },
                    "required": []
                }
            ),
            MCPTool(
                name="lobster_expand",
                description="将 DAG 摘要节点展开，还原其对应的原始消息（无损检索）",
                input_schema={
                    "type": "object",
                    "properties": {
                        "summary_id": {"type": "string", "description": "要展开的摘要节点 ID"},
                        "max_depth": {"type": "integer", "description": "最大展开层数，默认 2", "default": 2}
                    },
                    "required": ["summary_id"]
                }
            ),
            # v3.3.0: 自动压缩工具（调用真实 DAGCompressor）
            MCPTool(
                name="lobster_compress",
                description="增量压缩：检查上下文使用率，超过阈值时执行真正的 DAG 压缩",
                input_schema={
                    "type": "object",
                    "properties": {
                        "conversation_id": {"type": "string", "description": "对话 ID"},
                        "current_tokens": {"type": "integer", "description": "当前 token 数量"},
                        "token_budget": {"type": "integer", "description": "token 预算"},
                        "force": {"type": "boolean", "description": "是否强制压缩（忽略阈值）", "default": False}
                    },
                    "required": ["conversation_id", "current_tokens", "token_budget"]
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
        
        # v3.2.2: OpenClaw 插件工具
        elif tool_name == "lobster_grep":
            from agent_tools import lobster_grep
            db = self._get_db()
            results = lobster_grep(
                db,
                arguments["query"],
                conversation_id=arguments.get("conversation_id"),
                limit=arguments.get("limit", 5)
            )
            return {"results": results}
        
        elif tool_name == "lobster_describe":
            from agent_tools import lobster_describe
            db = self._get_db()
            return lobster_describe(db, conversation_id=arguments.get("conversation_id"))
        
        elif tool_name == "lobster_expand":
            from agent_tools import lobster_expand
            db = self._get_db()
            return lobster_expand(db, arguments["summary_id"])
        
        # v3.3.0: 自动压缩工具（调用真实 DAGCompressor）
        elif tool_name == "lobster_compress":
            from dag_compressor import DAGCompressor
            db = self._get_db()
            llm = self._get_llm() if self.llm_provider else None
            compressor = DAGCompressor(db, llm_client=llm)

            current_tokens = arguments["current_tokens"]
            token_budget = arguments["token_budget"]
            conversation_id = arguments["conversation_id"]
            force = arguments.get("force", False)
            threshold = token_budget * 0.75  # 默认 75% 阈值

            # v3.4.0: 移除 Python 层的重复阈值判断（修复 Bug #124）
            # TypeScript 层已经做了阈值判断，Python 层直接执行
            # force 参数保留，用于手动调用时使用

            # v3.3.1: 错误处理和重试机制
            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    # 执行压缩（调用真实的 DAGCompressor）
                    did_compress = compressor.incremental_compact(
                        conversation_id,
                        context_threshold=0.0,  # v3.4.0: 始终为 0，由 TS 层控制阈值
                        token_budget=token_budget
                    )

                    # v3.4.0: 返回真实的 tokens_after（修复 Bug #124）
                    messages_after = db.get_messages(conversation_id)
                    tokens_after = sum(m.get('token_count', 0) for m in messages_after)
                    tokens_saved = current_tokens - tokens_after

                    return {
                        "compressed": did_compress,
                        "conversation_id": conversation_id,
                        "tokens_before": current_tokens,
                        "tokens_after": tokens_after,  # 真实值
                        "tokens_saved": tokens_saved,   # 真实值
                        "token_budget": token_budget,
                        "attempt": attempt + 1
                    }
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        # 等待后重试
                        import asyncio
                        await asyncio.sleep(1 * (attempt + 1))
                        continue

            # 所有重试都失败
            return {
                "compressed": False,
                "error": last_error,
                "retries": max_retries,
                "conversation_id": conversation_id
            }
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _get_db(self):
        """获取数据库连接（懒加载）"""
        if self._db is None:
            # 添加 src 目录到 path
            src_dir = Path(__file__).parent.parent / "src"
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))
            
            from database import LobsterDatabase
            self._db = LobsterDatabase(self.db_path)
        return self._db
    
    def _validate_session_id(self, session_id: str) -> str:
        """验证 session_id 防止路径遍历攻击（修复 Issue #12）
        
        Args:
            session_id: 会话 ID
        
        Returns:
            验证后的会话 ID
        
        Raises:
            ValueError: 无效的会话 ID
        """
        if not session_id:
            raise ValueError("Session ID cannot be empty")
        
        # 只允许字母、数字、下划线、连字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise ValueError(f"Invalid session_id: {session_id} (only alphanumeric, underscore, hyphen allowed)")
        
        # 防止路径遍历
        if '..' in session_id or '/' in session_id or '\\' in session_id:
            raise ValueError(f"Invalid session_id: {session_id} (path traversal detected)")
        
        # 长度限制
        if len(session_id) > 255:
            raise ValueError(f"Session ID too long: {len(session_id)} > 255")
        
        return session_id
    
    async def _compress_session(self, session_id: str, strategy: str, dry_run: bool) -> Dict[str, Any]:
        """压缩会话（v3.3.0: 使用真实 DAGCompressor，v3.4.0: 修复 dry_run）"""
        # 验证 session_id（修复 Issue #12）
        session_id = self._validate_session_id(session_id)
        session_file = self.sessions_dir / f"{session_id}.jsonl"

        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        # v3.4.0: 修复 dry_run 被忽略的问题（修复 Bug #124）
        if dry_run:
            db = self._get_db()
            messages = db.get_messages(session_id)
            summaries = db.get_summaries(session_id)
            total_tokens = sum(m.get('token_count', 0) for m in messages)

            return {
                "status": "preview",
                "session_id": session_id,
                "strategy": strategy,
                "message_count": len(messages),
                "summary_count": len(summaries),
                "estimated_tokens": total_tokens,
                "dry_run": True,
                "note": "No compression performed. Call without dry_run=True to compress."
            }

        # v3.3.0: 调用真实 DAGCompressor（不再使用假 DAG）
        from dag_compressor import DAGCompressor
        db = self._get_db()
        llm = self._get_llm() if self.llm_provider else None
        compressor = DAGCompressor(db, llm_client=llm)

        # 根据策略决定阈值
        thresholds = {
            "light": 0.9,      # 只在 90% 时触发
            "medium": 0.75,    # 在 75% 时触发
            "aggressive": 0.5  # 在 50% 时触发
        }
        threshold = thresholds.get(strategy, 0.75)

        # v3.3.1: 错误处理和重试机制
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # 执行真实 DAG 压缩
                did_compress = compressor.incremental_compact(
                    conversation_id=session_id,
                    context_threshold=threshold,
                    token_budget=128000
                )

                # 获取压缩后的统计
                messages = db.get_messages(session_id)
                estimated_tokens = sum(m.get('token_count', 0) for m in messages)

                return {
                    "status": "success" if did_compress else "skipped",
                    "session_id": session_id,
                    "strategy": strategy,
                    "threshold": threshold,
                    "compressed": did_compress,
                    "message_count": len(messages),
                    "estimated_tokens": estimated_tokens,
                    "method": "real_dag_v3.4.0",
                    "attempt": attempt + 1
                }
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    # 等待后重试
                    import asyncio
                    await asyncio.sleep(1 * (attempt + 1))
                    continue

        # 所有重试都失败
        return {
            "status": "error",
            "error": last_error,
            "retries": max_retries,
            "session_id": session_id,
            "strategy": strategy
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


def emit(obj: Dict[str, Any]) -> None:
    """发送 JSON 响应到 stdout"""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


async def main():
    """主入口"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description="LobsterPress MCP Server")
    parser.add_argument("--sessions-dir", help="会话目录")
    parser.add_argument("--db", dest="db_path", help="LobsterPress 数据库路径")
    parser.add_argument("--provider", dest="llm_provider", help="LLM 提供商")
    parser.add_argument("--model", dest="llm_model", help="LLM 模型名称")
    parser.add_argument("--test", action="store_true", help="测试模式")
    
    args = parser.parse_args()
    
    server = LobsterPressMCPServer(
        sessions_dir=args.sessions_dir,
        db_path=args.db_path,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model
    )
    
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
        # Phase 1 (Issue #115): 发送 ready handshake
        emit({"type": "lobster-press/ready", "ts": time.time()})
        
        # MCP 协议模式（读取 stdin）
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            request_id = None
            try:
                req = json.loads(line)
                request_id = req.get("requestId") or req.get("id")
                method = req.get("method")
                
                if method == "tools/call":
                    params = req.get("params", {})
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    result = await server._call_tool(tool_name, arguments)
                    emit({
                        "requestId": request_id,
                        "status": "ok",
                        "result": result,
                    })
                else:
                    # 其他方法使用原有处理逻辑
                    response = await server.handle_request(req)
                    emit({
                        "requestId": request_id,
                        "status": "ok",
                        "result": response,
                    })
            except json.JSONDecodeError as e:
                emit({
                    "requestId": request_id,
                    "status": "error",
                    "error": f"Invalid JSON: {e}",
                })
            except Exception as e:
                emit({
                    "requestId": request_id,
                    "status": "error",
                    "error": str(e),
                })


if __name__ == "__main__":
    asyncio.run(main())
