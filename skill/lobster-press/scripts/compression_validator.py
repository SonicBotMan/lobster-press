#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压缩校验器 + 质量守卫
确保压缩操作真正节省 Token，并保护关键信息

Issue: #25, #30, #32 - Token 成本透明度 + 质量守卫 + 净收益校验
Author: LobsterPress Team
Version: v1.3.0
"""

import sys
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class CompressionResult:
    """压缩结果"""
    original_tokens: int
    compressed_tokens: int
    compression_cost: int  # 压缩操作消耗的 Token
    messages_kept: int
    messages_removed: int
    strategy: str
    
    @property
    def gross_saving(self) -> int:
        """毛节省"""
        return self.original_tokens - self.compressed_tokens
    
    @property
    def net_saving(self) -> int:
        """净节省（扣除压缩成本）"""
        return self.gross_saving - self.compression_cost
    
    @property
    def gross_saving_rate(self) -> float:
        """毛节省率"""
        if self.original_tokens == 0:
            return 0.0
        return self.gross_saving / self.original_tokens * 100
    
    @property
    def net_saving_rate(self) -> float:
        """净节省率"""
        if self.original_tokens == 0:
            return 0.0
        return self.net_saving / self.original_tokens * 100
    
    @property
    def is_worth_compressing(self) -> bool:
        """是否值得压缩"""
        return self.net_saving > 0


class CompressionValidator:
    """压缩净收益校验器"""
    
    # 压缩成本估算（每次压缩操作的 Token 消耗）
    COMPRESSION_COSTS = {
        "light": 800,    # 轻度压缩成本较低
        "medium": 1600,  # 中度压缩
        "heavy": 2400,   # 深度压缩成本最高
    }
    
    # 最小 Token 阈值（低于此值不建议压缩）
    MIN_TOKEN_THRESHOLDS = {
        "light": 8000,   # Light 策略最小 8k
        "medium": 6400,  # Medium 策略最小 6.4k
        "heavy": 4000,   # Heavy 策略最小 4k
    }
    
    # 预期节省率
    EXPECTED_SAVING_RATES = {
        "light": 0.12,   # Light 策略预期节省 12%
        "medium": 0.27,  # Medium 策略预期节省 27%
        "heavy": 0.43,   # Heavy 策略预期节省 43%
    }
    
    def __init__(self, strategy: str = "medium"):
        """初始化校验器
        
        Args:
            strategy: 压缩策略 (light/medium/heavy)
        """
        self.strategy = strategy
        self.compression_cost = self.COMPRESSION_COSTS.get(strategy, 1600)
        self.min_threshold = self.MIN_TOKEN_THRESHOLDS.get(strategy, 6400)
        self.expected_rate = self.EXPECTED_SAVING_RATES.get(strategy, 0.27)
    
    def should_compress(self, original_tokens: int) -> tuple:
        """判断是否应该压缩
        
        Args:
            original_tokens: 原始 Token 数
        
        Returns:
            (should_compress: bool, reason: str)
        """
        # 检查是否低于最小阈值
        if original_tokens < self.min_threshold:
            return False, f"❌ 上下文太小 ({original_tokens} < {self.min_threshold})，压缩成本高于收益"
        
        # 估算净收益
        expected_gross = int(original_tokens * self.expected_rate)
        expected_net = expected_gross - self.compression_cost
        
        if expected_net <= 0:
            return False, f"❌ 预估净收益为负 ({expected_net} tokens)，不值得压缩"
        
        return True, f"✅ 预估净节省 {expected_net} tokens，建议压缩"
    
    def validate_result(self, result: CompressionResult) -> Dict:
        """验证压缩结果
        
        Args:
            result: 压缩结果
        
        Returns:
            验证报告
        """
        report = {
            "strategy": result.strategy,
            "original_tokens": result.original_tokens,
            "compressed_tokens": result.compressed_tokens,
            "compression_cost": result.compression_cost,
            "gross_saving": result.gross_saving,
            "net_saving": result.net_saving,
            "gross_saving_rate": f"{result.gross_saving_rate:.1f}%",
            "net_saving_rate": f"{result.net_saving_rate:.1f}%",
            "is_worth": result.is_worth_compressing,
            "messages_kept": result.messages_kept,
            "messages_removed": result.messages_removed,
            "recommendation": "",
        }
        
        # 生成建议
        if result.net_saving > 0:
            report["recommendation"] = f"✅ 压缩成功，净节省 {result.net_saving} tokens"
        elif result.net_saving == 0:
            report["recommendation"] = "⚠️ 压缩无收益，建议跳过"
        else:
            report["recommendation"] = f"❌ 压缩亏损 {-result.net_saving} tokens，不应执行"
        
        return report
    
    def calculate_break_even(self) -> Dict:
        """计算盈亏平衡点
        
        Returns:
            盈亏平衡分析
        """
        # 净收益 = 原始 × 节省率 - 成本
        # 盈亏平衡：原始 × 节省率 = 成本
        # 原始 = 成本 / 节省率
        
        break_even_tokens = int(self.compression_cost / self.expected_rate)
        
        return {
            "strategy": self.strategy,
            "compression_cost": self.compression_cost,
            "expected_saving_rate": f"{self.expected_rate * 100:.0f}%",
            "break_even_tokens": break_even_tokens,
            "recommendation": f"上下文 >= {break_even_tokens} tokens 时才值得压缩",
        }


@dataclass
class QualityCheckResult:
    """质量检查结果"""
    check_name: str
    passed: bool
    score: int  # 0-100
    details: str


@dataclass
class QualityGuardConfig:
    """质量守卫配置"""
    enabled: bool = True
    min_score: int = 60  # 最低分数阈值
    auto_rollback: bool = True  # 自动回滚
    
    # 检查项权重
    check_weights: Dict[str, int] = field(default_factory=lambda: {
        "decision_preserved": 40,  # 决策保留
        "config_intact": 30,       # 配置完整
        "context_coherent": 30,    # 上下文连贯
    })
    
    # 关键决策关键词
    decision_keywords: List[str] = field(default_factory=lambda: [
        "决定", "采用", "选择", "使用", "方案", "chosed", "will use",
        "decided", "selected", "option", "solution", "final",
    ])
    
    # 配置关键词
    config_keywords: List[str] = field(default_factory=lambda: [
        "配置", "设置", "参数", "环境变量", "config", "setting",
        "parameter", "env", "variable", "API_KEY", "token",
    ])


class QualityGuard:
    """压缩质量守卫
    
    在压缩后验证关键信息是否保留：
    1. decision_preserved - 关键决策是否保留
    2. config_intact - 配置信息是否完整
    3. context_coherent - 上下文是否连贯
    """
    
    def __init__(self, config: Optional[QualityGuardConfig] = None):
        """初始化质量守卫
        
        Args:
            config: 质量守卫配置
        """
        self.config = config or QualityGuardConfig()
    
    def _extract_message_content(self, msg: Dict) -> str:
        """从 OpenClaw JSONL 消息中提取文本内容（Bug 2 修复）
        
        OpenClaw 消息结构：
        {
            "type": "message",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "实际内容"},
                    {"type": "toolCall", ...}
                ]
            }
        }
        
        Args:
            msg: 消息字典
        
        Returns:
            提取的文本内容
        """
        # 方法1：直接 content 字段（旧格式）
        if "content" in msg and isinstance(msg["content"], str):
            return msg["content"]
        
        # 方法2：message.content 列表（OpenClaw 新格式）
        message = msg.get("message", {})
        content_list = message.get("content", [])
        
        if isinstance(content_list, list):
            # 提取所有 type="text" 的 text 字段
            texts = []
            for item in content_list:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            return " ".join(texts)
        
        # 方法3：content 是字符串
        if isinstance(content_list, str):
            return content_list
        
        return ""
    
    def check_decision_preserved(self, 
                                  original_messages: List[Dict],
                                  compressed_messages: List[Dict]) -> QualityCheckResult:
        """检查关键决策是否保留
        
        Args:
            original_messages: 原始消息列表
            compressed_messages: 压缩后消息列表
        
        Returns:
            质量检查结果
        """
        # 提取原始消息中的决策（Bug 2 修复：使用正确的消息结构）
        original_decisions = set()
        for msg in original_messages:
            content = self._extract_message_content(msg)  # 修复：使用正确的提取方法
            for keyword in self.config.decision_keywords:
                if keyword.lower() in content.lower():
                    # 提取包含决策的句子
                    sentences = re.split(r'[。.!?！？]', content)
                    for sentence in sentences:
                        if keyword.lower() in sentence.lower():
                            original_decisions.add(sentence.strip()[:100])  # 截取前100字符
                    break
        
        if not original_decisions:
            return QualityCheckResult(
                check_name="decision_preserved",
                passed=True,
                score=100,
                details="原始消息中无关键决策",
            )
        
        # 检查压缩后是否保留
        compressed_content = " ".join([msg.get("content", "") for msg in compressed_messages])
        preserved_count = 0
        
        for decision in original_decisions:
            # 模糊匹配：检查关键词是否出现
            keywords = decision.split()[:5]  # 取前5个词
            if any(kw.lower() in compressed_content.lower() for kw in keywords if len(kw) > 2):
                preserved_count += 1
        
        score = int(preserved_count / len(original_decisions) * 100) if original_decisions else 100
        passed = score >= 60
        
        return QualityCheckResult(
            check_name="decision_preserved",
            passed=passed,
            score=score,
            details=f"决策保留率: {preserved_count}/{len(original_decisions)} ({score}%)",
        )
    
    def check_config_intact(self,
                           original_messages: List[Dict],
                           compressed_messages: List[Dict]) -> QualityCheckResult:
        """检查配置信息是否完整（Bug 2 修复）
        
        Args:
            original_messages: 原始消息列表
            compressed_messages: 压缩后消息列表
        
        Returns:
            质量检查结果
        """
        # 提取配置项（Bug 2 修复：使用正确的消息结构）
        original_configs = set()
        for msg in original_messages:
            content = self._extract_message_content(msg)  # 修复：使用正确的提取方法
            # 匹配 key=value 模式
            config_patterns = re.findall(r'[\w_]+=\S+', content)
            original_configs.update(config_patterns)
            
            # 匹配配置关键词
            for keyword in self.config.config_keywords:
                if keyword.lower() in content.lower():
                    original_configs.add(keyword)
        
        if not original_configs:
            return QualityCheckResult(
                check_name="config_intact",
                passed=True,
                score=100,
                details="原始消息中无配置信息",
            )
        
        # 检查压缩后是否保留
        compressed_content = " ".join([msg.get("content", "") for msg in compressed_messages])
        preserved_count = sum(1 for cfg in original_configs if cfg.lower() in compressed_content.lower())
        
        score = int(preserved_count / len(original_configs) * 100) if original_configs else 100
        passed = score >= 70  # 配置保留阈值更高
        
        return QualityCheckResult(
            check_name="config_intact",
            passed=passed,
            score=score,
            details=f"配置保留率: {preserved_count}/{len(original_configs)} ({score}%)",
        )
    
    def check_context_coherent(self,
                               compressed_messages: List[Dict]) -> QualityCheckResult:
        """检查上下文是否连贯
        
        Args:
            compressed_messages: 压缩后消息列表
        
        Returns:
            质量检查结果
        """
        if not compressed_messages:
            return QualityCheckResult(
                check_name="context_coherent",
                passed=False,
                score=0,
                details="压缩后消息为空",
            )
        
        # 检查角色分布
        roles = [msg.get("role", "") for msg in compressed_messages]
        role_set = set(roles)
        
        # 应该至少有 user 和 assistant
        has_user = "user" in role_set
        has_assistant = "assistant" in role_set
        
        # 检查是否有突兀的跳跃（连续多条相同角色）
        max_consecutive = 1
        current_consecutive = 1
        for i in range(1, len(roles)):
            if roles[i] == roles[i-1]:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
        
        # 评分
        score = 100
        details = []
        
        if not has_user:
            score -= 30
            details.append("缺少 user 角色")
        if not has_assistant:
            score -= 30
            details.append("缺少 assistant 角色")
        if max_consecutive > 5:
            score -= 20
            details.append(f"连续 {max_consecutive} 条相同角色")
        
        passed = score >= 60
        details_str = " | ".join(details) if details else "上下文连贯"
        
        return QualityCheckResult(
            check_name="context_coherent",
            passed=passed,
            score=max(0, score),
            details=details_str,
        )
    
    def run_quality_checks(self,
                          original_messages: List[Dict],
                          compressed_messages: List[Dict]) -> Tuple[bool, Dict]:
        """运行所有质量检查
        
        Args:
            original_messages: 原始消息列表
            compressed_messages: 压缩后消息列表
        
        Returns:
            (passed: bool, report: Dict)
        """
        if not self.config.enabled:
            return True, {"enabled": False, "message": "质量守卫已禁用"}
        
        checks = [
            self.check_decision_preserved(original_messages, compressed_messages),
            self.check_config_intact(original_messages, compressed_messages),
            self.check_context_coherent(compressed_messages),
        ]
        
        # 计算加权总分
        total_score = 0
        total_weight = 0
        all_passed = True
        
        check_results = []
        for check in checks:
            weight = self.config.check_weights.get(check.check_name, 20)
            total_score += check.score * weight
            total_weight += weight
            
            if not check.passed:
                all_passed = False
            
            check_results.append({
                "check": check.check_name,
                "passed": check.passed,
                "score": check.score,
                "details": check.details,
                "weight": weight,
            })
        
        final_score = total_score // total_weight if total_weight > 0 else 0
        passed = final_score >= self.config.min_score and all_passed
        
        report = {
            "enabled": True,
            "passed": passed,
            "final_score": final_score,
            "min_score": self.config.min_score,
            "auto_rollback": self.config.auto_rollback,
            "checks": check_results,
            "recommendation": "",
        }
        
        if passed:
            report["recommendation"] = f"✅ 质量检查通过 ({final_score}分)"
        else:
            report["recommendation"] = f"❌ 质量检查失败 ({final_score}分 < {self.config.min_score}分)"
            if self.config.auto_rollback:
                report["recommendation"] += "，建议回滚"
        
        return passed, report


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="压缩校验器 + 质量守卫")
    parser.add_argument("original_tokens", type=int, nargs="?", help="原始 Token 数")
    parser.add_argument("--strategy", default="medium", choices=["light", "medium", "heavy"],
                       help="压缩策略")
    parser.add_argument("--validate", help="验证压缩结果（JSON 格式）")
    parser.add_argument("--break-even", action="store_true", help="计算盈亏平衡点")
    parser.add_argument("--quality-check", help="质量检查（JSON 格式：{original, compressed}）")
    parser.add_argument("--quality-config", help="质量守卫配置（JSON 格式）")
    
    args = parser.parse_args()
    
    # 质量检查模式
    if args.quality_check:
        try:
            data = json.loads(args.quality_check)
            original = data.get("original", [])
            compressed = data.get("compressed", [])
            
            # 加载配置
            config = QualityGuardConfig()
            if args.quality_config:
                config_data = json.loads(args.quality_config)
                for key, value in config_data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            
            guard = QualityGuard(config)
            passed, report = guard.run_quality_checks(original, compressed)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            
            if not passed:
                sys.exit(1)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    validator = CompressionValidator(args.strategy)
    
    if args.break_even:
        # 计算盈亏平衡点
        result = validator.calculate_break_even()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.validate:
        # 验证压缩结果
        try:
            data = json.loads(args.validate)
            result = CompressionResult(**data)
            report = validator.validate_result(result)
            print(json.dumps(report, indent=2, ensure_ascii=False))
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.original_tokens:
        # 判断是否应该压缩
        should, reason = validator.should_compress(args.original_tokens)
        print(json.dumps({
            "should_compress": should,
            "reason": reason,
            "strategy": args.strategy,
            "min_threshold": validator.min_threshold,
        }, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
