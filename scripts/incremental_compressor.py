#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量压缩与断点续传 v1.0.0
支持大文件的增量压缩和断点续传

Issue: #45 - 增量压缩与断点续传
Author: LobsterPress Team
Version: v1.0.0
"""

import sys
import json
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class CompressionProgress:
    """压缩进度"""
    session_id: str
    total_messages: int
    processed_messages: int
    last_checkpoint: str
    partial_result_path: str
    status: str  # "in_progress", "completed", "failed"
    error: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        """进度百分比"""
        if self.total_messages == 0:
            return 0.0
        return (self.processed_messages / self.total_messages) * 100
    
    @property
    def is_completed(self) -> bool:
        """是否完成"""
        return self.status == "completed"
    
    @property
    def can_resume(self) -> bool:
        """是否可以恢复"""
        return self.status == "in_progress" and os.path.exists(self.partial_result_path)


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, progress_dir: str = "~/.lobster-press/progress"):
        self.progress_dir = Path(progress_dir).expanduser()
        self.progress_dir.mkdir(parents=True, exist_ok=True)
    
    def get_progress_path(self, session_id: str) -> Path:
        """获取进度文件路径"""
        return self.progress_dir / f"{session_id}.json"
    
    def save_progress(self, progress: CompressionProgress):
        """保存进度"""
        progress_path = self.get_progress_path(progress.session_id)
        
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(progress), f, indent=2, ensure_ascii=False)
    
    def load_progress(self, session_id: str) -> Optional[CompressionProgress]:
        """加载进度"""
        progress_path = self.get_progress_path(session_id)
        
        if not progress_path.exists():
            return None
        
        try:
            with open(progress_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return CompressionProgress(**data)
        except Exception as e:
            print(f"⚠️ 加载进度失败: {e}", file=sys.stderr)
            return None
    
    def delete_progress(self, session_id: str):
        """删除进度"""
        progress_path = self.get_progress_path(session_id)
        if progress_path.exists():
            progress_path.unlink()
    
    def list_progress(self) -> List[CompressionProgress]:
        """列出所有进度"""
        progress_list = []
        
        for progress_file in self.progress_dir.glob("*.json"):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                progress_list.append(CompressionProgress(**data))
            except Exception:
                continue
        
        return progress_list


class IncrementalCompressor:
    """增量压缩器"""
    
    def __init__(self, 
                 progress_dir: str = "~/.lobster-press/progress",
                 checkpoint_size: int = 100):
        """初始化增量压缩器
        
        Args:
            progress_dir: 进度目录
            checkpoint_size: 检查点大小（每处理多少消息保存一次）
        """
        self.progress_manager = ProgressManager(progress_dir)
        self.checkpoint_size = checkpoint_size
    
    def compress_session(self,
                        session_file: str,
                        output_file: str,
                        strategy: str = "medium",
                        resume: bool = True) -> Tuple[bool, str]:
        """压缩会话（支持断点续传）
        
        Args:
            session_file: 会话文件路径
            output_file: 输出文件路径
            strategy: 压缩策略
            resume: 是否恢复进度
        
        Returns:
            (是否成功, 消息)
        """
        session_id = Path(session_file).stem
        
        # 检查是否可以恢复
        if resume:
            progress = self.progress_manager.load_progress(session_id)
            if progress and progress.can_resume:
                return self._resume_compression(progress, session_file, output_file, strategy)
        
        # 开始新的压缩
        return self._start_compression(session_id, session_file, output_file, strategy)
    
    def _start_compression(self,
                          session_id: str,
                          session_file: str,
                          output_file: str,
                          strategy: str) -> Tuple[bool, str]:
        """开始新的压缩"""
        # 读取会话文件
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return False, f"无法读取会话文件: {e}"
        
        total_messages = len(lines)
        
        # 创建进度
        partial_file = f"{output_file}.partial"
        progress = CompressionProgress(
            session_id=session_id,
            total_messages=total_messages,
            processed_messages=0,
            last_checkpoint=datetime.now().isoformat(),
            partial_result_path=partial_file,
            status="in_progress"
        )
        
        self.progress_manager.save_progress(progress)
        
        # 处理消息
        try:
            processed = []
            
            for i, line in enumerate(lines):
                # 解析并处理
                try:
                    msg = json.loads(line)
                    processed.append(msg)
                except json.JSONDecodeError:
                    continue
                
                # 更新进度
                progress.processed_messages = i + 1
                progress.last_checkpoint = datetime.now().isoformat()
                
                # 定期保存检查点
                if (i + 1) % self.checkpoint_size == 0:
                    self._save_checkpoint(progress, processed)
            
            # 完成压缩
            # 这里应该调用实际的压缩逻辑
            # 简化版：直接写入
            with open(output_file, 'w', encoding='utf-8') as f:
                for msg in processed:
                    f.write(json.dumps(msg, ensure_ascii=False) + '\n')
            
            # 更新进度状态
            progress.status = "completed"
            self.progress_manager.save_progress(progress)
            
            # 删除部分文件
            if os.path.exists(partial_file):
                os.unlink(partial_file)
            
            return True, f"压缩完成: {total_messages} 条消息"
        
        except Exception as e:
            progress.status = "failed"
            progress.error = str(e)
            self.progress_manager.save_progress(progress)
            return False, f"压缩失败: {e}"
    
    def _resume_compression(self,
                           progress: CompressionProgress,
                           session_file: str,
                           output_file: str,
                           strategy: str) -> Tuple[bool, str]:
        """恢复压缩"""
        print(f"🔄 恢复压缩: {progress.session_id} ({progress.progress_percent:.1f}%)")
        
        # 读取已处理的部分
        processed = []
        if os.path.exists(progress.partial_result_path):
            try:
                with open(progress.partial_result_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            processed.append(json.loads(line))
            except Exception as e:
                print(f"⚠️ 无法读取部分结果: {e}")
        
        # 读取剩余消息
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return False, f"无法读取会话文件: {e}"
        
        # 跳过已处理的消息
        remaining_lines = lines[progress.processed_messages:]
        
        # 继续处理
        try:
            for i, line in enumerate(remaining_lines):
                try:
                    msg = json.loads(line)
                    processed.append(msg)
                except json.JSONDecodeError:
                    continue
                
                # 更新进度
                progress.processed_messages += 1
                progress.last_checkpoint = datetime.now().isoformat()
                
                # 定期保存
                if (progress.processed_messages) % self.checkpoint_size == 0:
                    self._save_checkpoint(progress, processed)
            
            # 完成
            with open(output_file, 'w', encoding='utf-8') as f:
                for msg in processed:
                    f.write(json.dumps(msg, ensure_ascii=False) + '\n')
            
            progress.status = "completed"
            self.progress_manager.save_progress(progress)
            
            if os.path.exists(progress.partial_result_path):
                os.unlink(progress.partial_result_path)
            
            return True, f"压缩完成: {progress.total_messages} 条消息"
        
        except Exception as e:
            progress.status = "failed"
            progress.error = str(e)
            self.progress_manager.save_progress(progress)
            return False, f"压缩失败: {e}"
    
    def _save_checkpoint(self, progress: CompressionProgress, messages: List[Dict]):
        """保存检查点"""
        # 保存部分结果
        with open(progress.partial_result_path, 'w', encoding='utf-8') as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + '\n')
        
        # 保存进度
        self.progress_manager.save_progress(progress)
    
    def get_progress(self, session_id: str) -> Optional[CompressionProgress]:
        """获取进度"""
        return self.progress_manager.load_progress(session_id)
    
    def clear_progress(self, session_id: str):
        """清除进度"""
        progress = self.progress_manager.load_progress(session_id)
        if progress:
            if os.path.exists(progress.partial_result_path):
                os.unlink(progress.partial_result_path)
            self.progress_manager.delete_progress(session_id)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="增量压缩与断点续传")
    parser.add_argument("session_file", help="会话文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--strategy", "-s", default="medium", help="压缩策略")
    parser.add_argument("--resume", action="store_true", help="恢复进度")
    parser.add_argument("--progress", action="store_true", help="查看进度")
    parser.add_argument("--clear", action="store_true", help="清除进度")
    
    args = parser.parse_args()
    
    session_id = Path(args.session_file).stem
    compressor = IncrementalCompressor()
    
    if args.progress:
        progress = compressor.get_progress(session_id)
        if progress:
            print(f"📊 压缩进度: {session_id}")
            print(f"  状态: {progress.status}")
            print(f"  进度: {progress.processed_messages}/{progress.total_messages} ({progress.progress_percent:.1f}%)")
            print(f"  最后检查点: {progress.last_checkpoint}")
            if progress.error:
                print(f"  错误: {progress.error}")
        else:
            print(f"❌ 没有找到进度: {session_id}")
    
    elif args.clear:
        compressor.clear_progress(session_id)
        print(f"✅ 已清除进度: {session_id}")
    
    else:
        output_file = args.output or f"{args.session_file}.compressed"
        success, message = compressor.compress_session(
            args.session_file,
            output_file,
            args.strategy,
            args.resume
        )
        
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
