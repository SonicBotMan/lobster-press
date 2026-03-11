#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量压缩器 v1.3.3
支持并发处理、进度显示、超时控制、智能线程配置

Issue: #54 - 批量压缩性能优化
Issue: #56 - 智能线程配置
Author: LobsterPress Team
Version: v1.3.3
"""

import sys
import json
import os
import time
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

# 导入资源检测器
try:
    from resource_detector import ResourceDetector, SystemResources
    HAS_RESOURCE_DETECTOR = True
except ImportError:
    HAS_RESOURCE_DETECTOR = False
    # 简化版资源检测
    @dataclass
    class SystemResources:
        cpu_count: int
        cpu_percent: float
        memory_total_mb: int
        memory_available_mb: int
        memory_percent: float


@dataclass
class BatchProgress:
    """批量压缩进度"""
    total_sessions: int
    completed_sessions: int
    failed_sessions: int
    in_progress_sessions: int
    current_session: Optional[str]
    start_time: str
    estimated_remaining_seconds: float
    sessions_per_minute: float
    
    @property
    def progress_percent(self) -> float:
        """进度百分比"""
        if self.total_sessions == 0:
            return 0.0
        return (self.completed_sessions / self.total_sessions) * 100


@dataclass
class SessionCompressionResult:
    """会话压缩结果"""
    session_id: str
    success: bool
    original_size: int
    compressed_size: int
    processing_time: float
    error: Optional[str] = None


class BatchCompressor:
    """批量压缩器
    
    支持：
    1. 并发处理多个会话
    2. 实时进度显示
    3. 超时控制
    4. 智能线程配置（根据 CPU/内存自动调整）
    5. 优雅关闭
    """
    
    def __init__(self,
                 max_workers: Union[int, str] = "auto",
                 timeout_per_session: int = 300,
                 progress_callback: Optional[Callable[[BatchProgress], None]] = None,
                 memory_per_thread_mb: int = 100,
                 reserved_cpu: int = 1):
        """初始化批量压缩器
        
        Args:
            max_workers: 最大并发数（"auto" 自动检测，或指定数字，默认 "auto"）
            timeout_per_session: 单个会话超时时间（秒，默认 300）
            progress_callback: 进度回调函数
            memory_per_thread_mb: 每个线程的内存消耗（MB，用于自动检测，默认 100）
            reserved_cpu: 保留的 CPU 核心数（用于自动检测，默认 1）
        """
        # 智能线程数检测
        if max_workers == "auto" or max_workers is None:
            if HAS_RESOURCE_DETECTOR:
                detector = ResourceDetector()
                self.max_workers, resources = detector.recommend_workers(
                    reserved_cpu=reserved_cpu,
                    memory_per_thread_mb=memory_per_thread_mb
                )
                print(f"🔍 自动检测: CPU {resources.cpu_count}核, 可用内存 {resources.memory_available_mb}MB")
                print(f"   推荐线程数: {self.max_workers}")
            else:
                # 无资源检测器，使用 CPU 核心数 - 1
                self.max_workers = max(1, multiprocessing.cpu_count() - 1)
                print(f"⚠️  未找到资源检测器，使用默认线程数: {self.max_workers}")
        else:
            # 用户指定线程数
            self.max_workers = min(int(max_workers), multiprocessing.cpu_count())
        
        self.timeout_per_session = timeout_per_session
        self.progress_callback = progress_callback
        self.start_time = None
        self.results = []
        self._shutdown = False
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n⚠️ 收到信号 {signum}，正在优雅关闭...")
        self._shutdown = True
    
    def compress_batch(self,
                      session_files: List[str],
                      output_dir: str,
                      strategy: str = "medium",
                      limit: Optional[int] = None) -> Tuple[int, int, List[SessionCompressionResult]]:
        """批量压缩会话
        
        Args:
            session_files: 会话文件列表
            output_dir: 输出目录
            strategy: 压缩策略
            limit: 限制处理的会话数量
        
        Returns:
            (成功数, 失败数, 结果列表)
        """
        self.start_time = time.time()
        self.results = []
        
        # 限制数量
        if limit and limit > 0:
            session_files = session_files[:limit]
        
        total_sessions = len(session_files)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 开始批量压缩: {total_sessions} 个会话")
        print(f"   并发数: {self.max_workers}")
        print(f"   超时: {self.timeout_per_session}s/会话")
        print(f"   策略: {strategy}")
        print()
        
        # 进度
        progress = BatchProgress(
            total_sessions=total_sessions,
            completed_sessions=0,
            failed_sessions=0,
            in_progress_sessions=0,
            current_session=None,
            start_time=datetime.now().isoformat(),
            estimated_remaining_seconds=0,
            sessions_per_minute=0
        )
        
        # 使用线程池并发处理
        completed_count = 0
        failed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_session = {}
            for session_file in session_files:
                if self._shutdown:
                    print("⚠️ 检测到关闭信号，停止提交新任务")
                    break
                
                output_file = output_dir / f"{Path(session_file).stem}_compressed.jsonl"
                future = executor.submit(
                    self._compress_single_session,
                    session_file,
                    str(output_file),
                    strategy
                )
                future_to_session[future] = session_file
            
            # 收集结果
            for future in as_completed(future_to_session, timeout=self.timeout_per_session * total_sessions):
                if self._shutdown:
                    print("⚠️ 检测到关闭信号，取消剩余任务")
                    executor.shutdown(wait=False)
                    break
                
                session_file = future_to_session[future]
                session_id = Path(session_file).stem
                
                try:
                    result = future.result(timeout=self.timeout_per_session)
                    self.results.append(result)
                    
                    if result.success:
                        completed_count += 1
                        progress.completed_sessions = completed_count
                    else:
                        failed_count += 1
                        progress.failed_sessions = failed_count
                    
                except Exception as e:
                    failed_count += 1
                    progress.failed_sessions = failed_count
                    self.results.append(SessionCompressionResult(
                        session_id=session_id,
                        success=False,
                        original_size=0,
                        compressed_size=0,
                        processing_time=0,
                        error=str(e)
                    ))
                    print(f"❌ {session_id}: {e}")
                
                # 更新进度
                elapsed_time = time.time() - self.start_time
                remaining_sessions = total_sessions - completed_count - failed_count
                if completed_count + failed_count > 0:
                    progress.sessions_per_minute = (completed_count + failed_count) / (elapsed_time / 60)
                    progress.estimated_remaining_seconds = remaining_sessions / progress.sessions_per_minute * 60
                
                progress.current_session = session_id
                progress.in_progress_sessions = len(future_to_session) - completed_count - failed_count
                
                # 回调进度
                if self.progress_callback:
                    self.progress_callback(progress)
                
                # 打印进度
                print(f"📊 进度: {progress.progress_percent:.1f}% ({completed_count}/{total_sessions}) | "
                      f"速度: {progress.sessions_per_minute:.1f} 会话/分钟 | "
                      f"预计剩余: {progress.estimated_remaining_seconds:.0f}s")
        
        return completed_count, failed_count, self.results
    
    def _compress_single_session(self,
                                 session_file: str,
                                 output_file: str,
                                 strategy: str) -> SessionCompressionResult:
        """压缩单个会话
        
        Args:
            session_file: 会话文件路径
            output_file: 输出文件路径
            strategy: 压缩策略
        
        Returns:
            压缩结果
        """
        session_id = Path(session_file).stem
        start_time = time.time()
        
        try:
            # 读取会话
            messages = []
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))
            
            original_size = len(messages)
            
            # 应用压缩策略
            compressed_messages = self._apply_strategy(messages, strategy)
            compressed_size = len(compressed_messages)
            
            # 写入输出
            with open(output_file, 'w', encoding='utf-8') as f:
                for msg in compressed_messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + '\n')
            
            processing_time = time.time() - start_time
            
            print(f"✅ {session_id}: {original_size} → {compressed_size} ({processing_time:.1f}s)")
            
            return SessionCompressionResult(
                session_id=session_id,
                success=True,
                original_size=original_size,
                compressed_size=compressed_size,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return SessionCompressionResult(
                session_id=session_id,
                success=False,
                original_size=0,
                compressed_size=0,
                processing_time=processing_time,
                error=str(e)
            )
    
    def _apply_strategy(self, messages: List[Dict], strategy: str) -> List[Dict]:
        """应用压缩策略
        
        Args:
            messages: 消息列表
            strategy: 压缩策略
        
        Returns:
            压缩后的消息列表
        """
        if not messages:
            return messages
        
        # 保留比例
        retention_ratios = {
            "light": 0.85,      # 保留 85%
            "medium": 0.70,     # 保留 70%
            "aggressive": 0.55,  # 保留 55%
        }
        
        ratio = retention_ratios.get(strategy, 0.70)
        keep_count = max(1, int(len(messages) * ratio))
        
        # 简化评分：保留前 10% 和后 90%
        if len(messages) <= keep_count:
            return messages
        
        # 保留前 10%（包含重要上下文）
        head_count = max(1, int(keep_count * 0.1))
        tail_count = keep_count - head_count
        
        compressed = messages[:head_count] + messages[-tail_count:]
        
        return compressed
    
    def get_summary(self) -> Dict:
        """获取压缩摘要"""
        if not self.results:
            return {}
        
        total_original = sum(r.original_size for r in self.results)
        total_compressed = sum(r.compressed_size for r in self.results)
        
        return {
            "total_sessions": len(self.results),
            "successful": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success),
            "total_original_size": total_original,
            "total_compressed_size": total_compressed,
            "compression_ratio": f"{(1 - total_compressed / total_original) * 100:.1f}%" if total_original > 0 else "0%",
            "average_time_per_session": sum(r.processing_time for r in self.results) / len(self.results),
            "total_time": time.time() - self.start_time if self.start_time else 0,
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量压缩器 v1.3.3")
    parser.add_argument("input_dir", help="输入目录（包含会话文件）")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--strategy", default="medium", choices=["light", "medium", "aggressive"],
                       help="压缩策略（默认: medium）")
    parser.add_argument("--workers", type=str, default="auto",
                       help="并发数（'auto' 自动检测，或指定数字，默认: auto）")
    parser.add_argument("--timeout", type=int, default=300, help="超时时间（秒，默认: 300）")
    parser.add_argument("--limit", type=int, help="限制处理的会话数量")
    parser.add_argument("--pattern", default="*.jsonl", help="文件模式（默认: *.jsonl）")
    
    args = parser.parse_args()
    
    # 查找会话文件
    input_dir = Path(args.input_dir)
    session_files = list(input_dir.glob(args.pattern))
    
    if not session_files:
        print(f"❌ 未找到匹配的会话文件: {input_dir}/{args.pattern}")
        sys.exit(1)
    
    print(f"找到 {len(session_files)} 个会话文件")
    
    # 创建压缩器
    compressor = BatchCompressor(
        max_workers=args.workers,
        timeout_per_session=args.timeout
    )
    
    # 执行压缩
    completed, failed, results = compressor.compress_batch(
        session_files=[str(f) for f in session_files],
        output_dir=args.output_dir,
        strategy=args.strategy,
        limit=args.limit
    )
    
    # 打印摘要
    print("\n" + "=" * 60)
    summary = compressor.get_summary()
    print("📊 压缩摘要:")
    print(f"   总会话数: {summary['total_sessions']}")
    print(f"   成功: {summary['successful']}")
    print(f"   失败: {summary['failed']}")
    print(f"   压缩率: {summary['compression_ratio']}")
    print(f"   平均时间: {summary['average_time_per_session']:.2f}s/会话")
    print(f"   总耗时: {summary['total_time']:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
