#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LobsterPress MCP Server
基于 Model Context Protocol (MCP) 的认知记忆压缩服务

Version: v4.0.11
Changelog: https://github.com/SonicBotMan/lobster-press/blob/master/CHANGELOG.md

# lobster-press v4.0.11 MCP 工具集

## Write 层（写入记忆）
- lobster_compact   — 触发 DAG 压缩，将工作记忆写入情节记忆
- lobster_correct   — 纠错已压缩的记忆（v3.6 引入）

## Manage 层（管理记忆）
- lobster_sweep     — 主动衰减扫描，标记低分消息（v3.6 引入）
- lobster_assemble  — 按三层优先级拼装最优上下文（v3.6 引入）
- lobster_prune     — 删除 decay_candidate 消息，释放存储（v4.0 新增）

## Read 层（读取记忆）
- lobster_grep      — 全文搜索（FTS5)
- lobster_describe  — 查看 DAG 节点详情
- lobster_expand    — 可逆展开（v4.0 支持 R³Mem 三层）
- lobster_status    — 系统级健康报告（v4.0 新增）
"""

