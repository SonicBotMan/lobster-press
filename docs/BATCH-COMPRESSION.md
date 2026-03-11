# 批量压缩器使用指南

## 概述

批量压缩器（Batch Compressor）用于批量处理多个会话的压缩任务，支持并发处理、实时进度显示、超时控制等特性。

## 特性

- ✅ **并发处理** - 支持多线程并发处理多个会话
- ✅ **实时进度** - 显示进度百分比、速度、预计剩余时间
- ✅ **超时控制** - 单个会话超时控制，避免卡死
- ✅ **优雅关闭** - 支持 SIGINT/SIGTERM 优雅关闭
- ✅ **限制数量** - 支持限制处理的会话数量
- ✅ **压缩策略** - 支持轻/中/重度压缩

## 使用方法

### 命令行使用

```bash
# 基础用法
python scripts/batch_compressor.py sessions/ compressed/

# 自定义参数
python scripts/batch_compressor.py sessions/ compressed/ \
  --strategy aggressive \
  --workers 8 \
  --timeout 600 \
  --limit 100
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input_dir` | 输入目录（包含会话文件） | 必填 |
| `output_dir` | 输出目录 | 必填 |
| `--strategy` | 压缩策略（light/medium/aggressive） | medium |
| `--workers` | 并发数 | 4 |
| `--timeout` | 单个会话超时（秒） | 300 |
| `--limit` | 限制处理的会话数量 | 无限制 |
| `--pattern` | 文件模式 | *.jsonl |

### Python API 使用

```python
from scripts.batch_compressor import BatchCompressor

def progress_callback(progress):
    print(f"进度: {progress.progress_percent:.1f}%")
    print(f"速度: {progress.sessions_per_minute:.1f} 会话/分钟")

compressor = BatchCompressor(
    max_workers=4,
    timeout_per_session=300,
    progress_callback=progress_callback
)

completed, failed, results = compressor.compress_batch(
    session_files=["session1.jsonl", "session2.jsonl"],
    output_dir="compressed/",
    strategy="medium",
    limit=10
)

# 获取摘要
summary = compressor.get_summary()
print(f"压缩率: {summary['compression_ratio']}")
```

## 压缩策略

### light（轻度）
- 保留 85% 的消息
- 适用于重要会话
- 压缩率约 15%

### medium（中度）
- 保留 70% 的消息
- 平衡压缩率和保留率
- 压缩率约 30%

### aggressive（重度）
- 保留 55% 的消息
- 最大化压缩率
- 压缩率约 45%

## 性能优化建议

### 1. 并发数设置

```bash
# CPU 密集型任务：并发数 = CPU 核心数
--workers $(nproc)

# I/O 密集型任务：并发数 = CPU 核心数 * 2
--workers $(( $(nproc) * 2 ))
```

### 2. 超时设置

```bash
# 小会话（<1000 消息）：60s
--timeout 60

# 中等会话（1000-10000 消息）：300s
--timeout 300

# 大会话（>10000 消息）：600s
--timeout 600
```

### 3. 批量处理

```bash
# 分批处理大量会话
for i in {1..10}; do
    python scripts/batch_compressor.py sessions/ compressed/batch_$i/ \
      --limit 100 \
      --workers 4
done
```

## 监控和日志

### 实时进度

```
🚀 开始批量压缩: 100 个会话
   并发数: 4
   超时: 300s/会话
   策略: medium

✅ session_001: 1000 → 700 (2.1s)
📊 进度: 10.0% (10/100) | 速度: 12.3 会话/分钟 | 预计剩余: 450s
✅ session_002: 1500 → 1050 (2.8s)
...
```

### 压缩摘要

```
📊 压缩摘要:
   总会话数: 100
   成功: 98
   失败: 2
   压缩率: 28.5%
   平均时间: 2.3s/会话
   总耗时: 245.6s
```

## 错误处理

### 常见错误

1. **超时错误**
   ```
   ⏱️ session_large: 超时（>300s）
   ```
   解决：增加超时时间 `--timeout 600`

2. **文件读取错误**
   ```
   ❌ session_invalid: Expecting value: line 1 column 1 (char 0)
   ```
   解决：检查文件格式是否为有效 JSONL

3. **内存不足**
   ```
   ❌ session_huge: [Errno 12] Cannot allocate memory
   ```
   解决：减少并发数或分批处理

## 最佳实践

1. **首次运行**：使用小批量测试
   ```bash
   python scripts/batch_compressor.py sessions/ test/ --limit 10
   ```

2. **生产环境**：设置合理超时和并发
   ```bash
   python scripts/batch_compressor.py sessions/ compressed/ \
     --workers 4 \
     --timeout 300 \
     --strategy medium
   ```

3. **监控进度**：使用进度回调
   ```python
   def progress_callback(progress):
       if progress.progress_percent % 10 == 0:
           send_alert(f"进度: {progress.progress_percent:.0f}%")
   ```

4. **优雅关闭**：Ctrl+C 会等待当前任务完成

---

**Version:** v1.3.1  
**Issue:** #54  
**Author:** LobsterPress Team
