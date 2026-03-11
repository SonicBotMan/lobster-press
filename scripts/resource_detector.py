#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统资源检测器
自动检测 CPU 和内存配置，智能推荐线程数

Author: LobsterPress Team
Version: v1.3.3
"""

import os
import sys
import multiprocessing
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SystemResources:
    """系统资源信息"""
    cpu_count: int                    # CPU 核心数
    cpu_percent: float                # CPU 使用率（%）
    memory_total_mb: int              # 总内存（MB）
    memory_available_mb: int          # 可用内存（MB）
    memory_percent: float             # 内存使用率（%）
    
    @property
    def memory_total_gb(self) -> float:
        """总内存（GB）"""
        return self.memory_total_mb / 1024
    
    @property
    def memory_available_gb(self) -> float:
        """可用内存（GB）"""
        return self.memory_available_mb / 1024


class ResourceDetector:
    """系统资源检测器"""
    
    # 每个线程预估内存消耗（MB）
    # 根据实际测试调整：处理 1000 条消息约需 50MB
    MEMORY_PER_THREAD_MB = 100
    
    # CPU 保留核心数（不全部用完）
    CPU_RESERVED = 1
    
    # 最小线程数
    MIN_WORKERS = 1
    
    # 最大线程数（安全上限）
    MAX_WORKERS = 32
    
    def detect_resources(self) -> SystemResources:
        """检测系统资源
        
        Returns:
            系统资源信息
        """
        # CPU 信息
        cpu_count = self._get_cpu_count()
        cpu_percent = self._get_cpu_usage()
        
        # 内存信息
        memory_total_mb, memory_available_mb = self._get_memory_info()
        memory_percent = ((memory_total_mb - memory_available_mb) / memory_total_mb * 100) if memory_total_mb > 0 else 0
        
        return SystemResources(
            cpu_count=cpu_count,
            cpu_percent=cpu_percent,
            memory_total_mb=memory_total_mb,
            memory_available_mb=memory_available_mb,
            memory_percent=memory_percent
        )
    
    def _get_cpu_count(self) -> int:
        """获取 CPU 核心数"""
        try:
            return multiprocessing.cpu_count()
        except:
            return 1
    
    def _get_cpu_usage(self) -> float:
        """获取 CPU 使用率（简化版）"""
        try:
            # 读取 /proc/stat
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                if line.startswith('cpu'):
                    parts = line.split()[1:8]
                    values = [int(p) for p in parts]
                    total = sum(values)
                    idle = values[3]
                    return ((total - idle) / total * 100) if total > 0 else 0
        except:
            pass
        return 0.0
    
    def _get_memory_info(self) -> Tuple[int, int]:
        """获取内存信息
        
        Returns:
            (总内存 MB, 可用内存 MB)
        """
        try:
            # Linux: 读取 /proc/meminfo
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(':')
                        value = int(parts[1])
                        meminfo[key] = value
                
                # MemTotal 和 MemAvailable（KB → MB）
                total_kb = meminfo.get('MemTotal', 0)
                available_kb = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
                
                return (total_kb // 1024, available_kb // 1024)
                
        except:
            pass
        
        # Fallback: 使用 psutil（如果可用）
        try:
            import psutil
            mem = psutil.virtual_memory()
            return (mem.total // (1024 * 1024), mem.available // (1024 * 1024))
        except:
            pass
        
        # 默认值
        return (4096, 2048)  # 假设 4GB 总内存，2GB 可用
    
    def recommend_workers(self,
                         reserved_cpu: int = None,
                         memory_per_thread_mb: int = None,
                         min_workers: int = None,
                         max_workers: int = None) -> Tuple[int, SystemResources]:
        """智能推荐线程数
        
        基于 CPU 核心数和可用内存计算最佳线程数
        
        Args:
            reserved_cpu: 保留的 CPU 核心数（默认 1）
            memory_per_thread_mb: 每个线程的内存消耗（MB，默认 100）
            min_workers: 最小线程数（默认 1）
            max_workers: 最大线程数（默认 32）
        
        Returns:
            (推荐线程数, 系统资源信息)
        """
        # 使用默认值
        reserved_cpu = reserved_cpu if reserved_cpu is not None else self.CPU_RESERVED
        memory_per_thread_mb = memory_per_thread_mb if memory_per_thread_mb is not None else self.MEMORY_PER_THREAD_MB
        min_workers = min_workers if min_workers is not None else self.MIN_WORKERS
        max_workers = max_workers if max_workers is not None else self.MAX_WORKERS
        
        # 检测系统资源
        resources = self.detect_resources()
        
        # 基于 CPU 的推荐值
        cpu_based = max(1, resources.cpu_count - reserved_cpu)
        
        # 基于内存的推荐值
        # 保留 30% 的内存给系统和其他进程
        usable_memory_mb = resources.memory_available_mb * 0.7
        memory_based = max(1, int(usable_memory_mb / memory_per_thread_mb))
        
        # 取两者最小值
        recommended = min(cpu_based, memory_based)
        
        # 限制在 [min_workers, max_workers] 范围内
        recommended = max(min_workers, min(recommended, max_workers))
        
        return recommended, resources
    
    def get_recommendation_report(self) -> str:
        """生成推荐报告"""
        recommended, resources = self.recommend_workers()
        
        report = []
        report.append("=" * 60)
        report.append("系统资源检测报告")
        report.append("=" * 60)
        report.append("")
        report.append("硬件配置:")
        report.append(f"  CPU 核心数: {resources.cpu_count}")
        report.append(f"  CPU 使用率: {resources.cpu_percent:.1f}%")
        report.append(f"  总内存: {resources.memory_total_gb:.1f} GB ({resources.memory_total_mb} MB)")
        report.append(f"  可用内存: {resources.memory_available_gb:.1f} GB ({resources.memory_available_mb} MB)")
        report.append(f"  内存使用率: {resources.memory_percent:.1f}%")
        report.append("")
        report.append("推荐配置:")
        report.append(f"  推荐线程数: {recommended}")
        report.append(f"  CPU 限制: {resources.cpu_count - self.CPU_RESERVED} (保留 {self.CPU_RESERVED} 核)")
        report.append(f"  内存限制: {int(resources.memory_available_mb * 0.7 / self.MEMORY_PER_THREAD_MB)} (每线程 {self.MEMORY_PER_THREAD_MB}MB)")
        report.append(f"  实际选择: min(CPU, 内存) = {recommended}")
        report.append("")
        report.append("使用建议:")
        if recommended <= 2:
            report.append("  ⚠️  资源紧张，建议使用较少并发")
            report.append("  - 单线程处理: --workers 1")
            report.append("  - 分批处理: --limit 50")
        elif recommended <= 4:
            report.append("  ✅ 资源适中，推荐使用 2-4 线程")
            report.append("  - 推荐配置: --workers 2")
        else:
            report.append("  ✅ 资源充足，可使用高并发")
            report.append(f"  - 推荐配置: --workers {recommended}")
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    """命令行入口"""
    detector = ResourceDetector()
    
    # 显示推荐报告
    print(detector.get_recommendation_report())
    
    # 显示使用示例
    recommended, _ = detector.recommend_workers()
    print("\n使用示例:")
    print(f"  python scripts/batch_compressor.py sessions/ compressed/ --workers {recommended}")
    print("\n或使用自动检测:")
    print("  python scripts/batch_compressor.py sessions/ compressed/ --workers auto")


if __name__ == "__main__":
    main()
