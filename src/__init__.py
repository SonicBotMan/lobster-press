# -*- coding: utf-8 -*-
"""
LobsterPress - Cognitive Memory System for AI Agents

单一版本号来源（Single Source of Truth）
所有其他文件应从此处导入版本号。
"""


__version__ = "4.0.90"
__author__ = "SonicBotMan"
__email__ = "sonicbotman@example.com"

# 版本历史（最近5个）
VERSION_HISTORY = [
    ("4.0.41", "2026-03-22", "Issue #185 - Fix __init__.py syntax error"),
    ("4.0.40", "2026-03-22", "Issue #184 - MCP cwd path fix + lifecycle hooks"),
    ("4.0.37", "2026-03-22", "Issue #181 - E2E test bug fixes"),
    ("4.0.36", "2026-03-22", "Issue #174 - Expert feedback optimization"),
    ("4.0.35", "2026-03-22", "Issue #174 - P0/P1/P2 fixes"),
    ("4.0.34", "2026-03-21", "Issue #173 - TF-IDF optimization"),
]

def get_version():
    """获取当前版本号"""
    return __version__

def get_version_info():
    """获取版本详细信息"""
    return {
        "version": __version__,
        "author": __author__,
        "email": __email__,
    }
