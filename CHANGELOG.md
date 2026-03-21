# 更新日志

所有重要的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [4.0.25] - 2026-03-21

### Fixed
- 🟠 **P1**: `assemble()` token_budget 默认值从 8000 改为 128000，与 `afterTurn` 保持一致（Issue #163 P1-4）
  - 之前：assemble 使用 8000，afterTurn 使用 128000，相差 16 倍
  - 现在：统一使用 128000

### Housekeeping
- 📋 **P2**: 版本号同步（Issue #163 P2）
  - src/agent_tools.py: v4.0.16 → v4.0.25
  - mcp_server/lobster_mcp_server.py: v4.0.16 → v4.0.25

### Notes
- P0-1（turn_count 测试覆盖）是误报：`tests/unit/test_v400.py:175` 已有 `test_get_turn_count` 测试
- P0-2（ingest 静默降级）是设计决策，调用方可根据 `ingested: false` 决定是否重试

