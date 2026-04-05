#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dual Decay Parameters Test - Phase 1.4
测试双半衰期参数系统：12h 压缩 vs 14d 检索

Author: LobsterPress Team
Date: 2026-04-05
"""

import sys
import math
import pytest
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database import LobsterDatabase


class TestDualDecayConstants:
    """测试双半衰期常量定义"""

    def test_compression_half_life_hours(self):
        """验证压缩半衰期常量 = 12h"""
        assert LobsterDatabase.COMPRESSION_HALF_LIFE_HOURS == 12

    def test_retrieval_half_life_days(self):
        """验证检索半衰期常量 = 14d"""
        assert LobsterDatabase.RETRIEVAL_HALF_LIFE_DAYS == 14.0

    def test_retrieval_half_life_hours(self):
        """验证检索半衰期常量 = 336h（14d * 24h）"""
        assert LobsterDatabase.RETRIEVAL_HALF_LIFE_HOURS == 336.0


class TestDefaultCompressionBehavior:
    """测试默认压缩行为（half_life_override=None）"""

    def setup_method(self):
        self.db = LobsterDatabase(":memory:")

    def test_chlr_adaptive_algorithm_unchanged(self):
        """C-HLR+ 自适应算法应保持不变"""
        msg = {
            "content": "test message",
            "tfidf_score": 1.0,
            "structural_bonus": 0.0,
            "msg_type": "unknown",
            "created_at": datetime.utcnow().isoformat(),
        }
        current = datetime.utcnow()
        retention1 = self.db._compute_retention(msg, current, half_life_override=None)
        retention2 = self.db._compute_retention(msg, current)
        assert retention1 == retention2

    def test_message_type_affects_base_half_life(self):
        """消息类型应影响基础半衰期"""
        now = datetime.utcnow()
        created = now - timedelta(days=1)

        chitchat_msg = {
            "content": "hi there",
            "tfidf_score": 1.0,
            "msg_type": "chitchat",
            "created_at": created.isoformat(),
        }
        decision_msg = {
            "content": "we decided to use python",
            "tfidf_score": 1.0,
            "msg_type": "decision",
            "created_at": created.isoformat(),
        }

        chitchat_retention = self.db._compute_retention(chitchat_msg, now)
        decision_retention = self.db._compute_retention(decision_msg, now)

        assert chitchat_retention < decision_retention

    def test_12h_window_shows_differential_retention(self):
        """12h 窗口应显示差异保留率"""
        now = datetime.utcnow()

        recent_msg = {
            "content": "recent message",
            "tfidf_score": 1.0,
            "msg_type": "unknown",
            "created_at": now.isoformat(),
        }
        old_msg = {
            "content": "old message",
            "tfidf_score": 1.0,
            "msg_type": "unknown",
            "created_at": (now - timedelta(hours=12)).isoformat(),
        }

        recent_retention = self.db._compute_retention(recent_msg, now)
        old_retention = self.db._compute_retention(old_msg, now)

        assert recent_retention > old_retention


class TestRetrievalOverride:
    """测试检索覆盖模式（half_life_override=336.0）"""

    def setup_method(self):
        self.db = LobsterDatabase(":memory:")

    def test_retrieval_decay_returns_decay_factor(self):
        """检索衰减应返回衰减因子"""
        msg = {
            "content": "test message",
            "tfidf_score": 1.0,
            "created_at": datetime.utcnow().isoformat(),
        }
        current = datetime.utcnow()
        retention = self.db._compute_retention(msg, current, half_life_override=336.0)
        assert 0.0 < retention <= 1.0

    def test_at_14_days_factor_approx_065(self):
        """current_time = created_at + 14d 时，factor ≈ 0.65"""
        created = datetime(2026, 1, 1, 12, 0, 0)
        at_14d = created + timedelta(days=14)

        msg = {
            "content": "test",
            "tfidf_score": 1.0,
            "created_at": created.isoformat(),
        }

        retention = self.db._compute_retention(msg, at_14d, half_life_override=336.0)
        expected = 0.3 + 0.7 * 0.5
        assert abs(retention - expected) < 0.01

    def test_at_creation_time_factor_approx_1(self):
        """current_time = created_at 时，factor ≈ 1.0"""
        created = datetime(2026, 1, 1, 12, 0, 0)

        msg = {
            "content": "test",
            "tfidf_score": 1.0,
            "created_at": created.isoformat(),
        }

        retention = self.db._compute_retention(msg, created, half_life_override=336.0)
        assert abs(retention - 1.0) < 0.001


class Test12hVs14dDifference:
    """测试 12h vs 14d 差异"""

    def setup_method(self):
        self.db = LobsterDatabase(":memory:")

    def test_12h_half_life_decays_faster(self):
        """12h 半衰期比 14d 半衰期衰减更快"""
        created = datetime(2026, 1, 1, 12, 0, 0)
        at_1d = created + timedelta(days=1)

        msg = {
            "content": "test message",
            "tfidf_score": 1.0,
            "created_at": created.isoformat(),
        }

        retention_12h = self.db._compute_retention(msg, at_1d, half_life_override=12.0)
        retention_14d = self.db._compute_retention(msg, at_1d, half_life_override=336.0)

        assert retention_12h < retention_14d

    def test_1_day_old_12h_factor_approx_03(self):
        """1 天旧的 12h 半衰期消息：factor ≈ 0.3"""
        created = datetime(2026, 1, 1, 12, 0, 0)
        at_1d = created + timedelta(days=1)

        msg = {
            "content": "test",
            "tfidf_score": 1.0,
            "created_at": created.isoformat(),
        }

        retention = self.db._compute_retention(msg, at_1d, half_life_override=12.0)
        expected = 0.3 + 0.7 * math.pow(0.5, 24.0 / 12.0)
        assert abs(retention - expected) < 0.01

    def test_1_day_old_14d_factor_approx_097(self):
        """1 天旧的 14d 半衰期消息：factor ≈ 0.97"""
        created = datetime(2026, 1, 1, 12, 0, 0)
        at_1d = created + timedelta(days=1)

        msg = {
            "content": "test",
            "tfidf_score": 1.0,
            "created_at": created.isoformat(),
        }

        retention = self.db._compute_retention(msg, at_1d, half_life_override=336.0)
        expected = 0.3 + 0.7 * math.pow(0.5, 1.0 / 14.0)
        assert abs(retention - expected) < 0.01


class TestFloorValue:
    """测试地板值（floor value）"""

    def setup_method(self):
        self.db = LobsterDatabase(":memory:")

    def test_old_message_retains_30_percent(self):
        """极老消息仍保留至少 30% 分数"""
        created = datetime(2026, 1, 1, 12, 0, 0)
        at_100d = created + timedelta(days=100)

        msg = {
            "content": "old message",
            "tfidf_score": 1.0,
            "created_at": created.isoformat(),
        }

        retention = self.db._compute_retention(msg, at_100d, half_life_override=336.0)
        assert retention >= 0.3

    def test_floor_value_prevents_zero(self):
        """地板值防止分数归零"""
        created = datetime(2026, 1, 1, 12, 0, 0)
        at_very_old = created + timedelta(days=1000)

        msg = {
            "content": "very old",
            "tfidf_score": 1.0,
            "created_at": created.isoformat(),
        }

        retention = self.db._compute_retention(
            msg, at_very_old, half_life_override=336.0
        )
        assert retention > 0.0
        assert retention >= 0.3
