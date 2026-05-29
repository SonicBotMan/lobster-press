# Phase 1 执行计划：集成现有压缩模块到 lobster_assemble

## 目标

让 `lobster_assemble` 调用已有的压缩模块，解决小文反馈的问题：
- ❌ 重复 JSON 没有去重 → 使用 `semantic_dedup.py`
- ❌ 有价值内容没有提取 → 使用 `event_segmenter.py`
- ❌ 工具输出占用大量 token → 使用 `three_pass_trimmer.py`

---

## Todo 列表

### 1. 准备阶段

- [ ] 1.1 阅读现有模块源码，理解接口
  - [x] 1.1.1 阅读 `three_pass_trimmer.py` - CMV 三遍压缩 ✅
  - [x] 1.1.2 阅读 `event_segmenter.py` - EM-LLM 事件分割 ✅
  - [x] 1.1.3 阅读 `semantic_dedup.py` - 语义去重 ✅
  - [x] 1.1.4 阅读 `database.py` 的 `get_context_by_tier()` 方法 ✅

- [x] 1.2 确认模块可用性
  - [x] 1.2.1 检查 `three_pass_trimmer.py` 的导入和接口 ✅
  - [x] 1.2.2 检查 `event_segmenter.py` 的导入和接口 ✅
  - [x] 1.2.3 检查 `semantic_dedup.py` 的导入和接口 → 暂不使用（需要 ScoredMessage 输入，增加复杂性）
  - [ ] 1.1.4 阅读 `database.py` 的 `get_context_by_tier()` 方法

- [ ] 1.2 确认模块可用性
  - [ ] 1.2.1 检查 `three_pass_trimmer.py` 的导入和接口
  - [ ] 1.2.2 检查 `event_segmenter.py` 的导入和接口
  - [ ] 1.2.3 检查 `semantic_dedup.py` 的导入和接口

### 2. 设计阶段

- [x] 2.1 设计新的 `lobster_assemble` 流程 ✅
  - [x] 2.1.1 确定压缩流程顺序（先去重？先分割？先压缩？） → 先分割，再压缩
  - [x] 2.1.2 确定 token 预算分配策略 → 保持现有 30%:30%:40%
  - [x] 2.1.3 设计错误处理机制（模块失败时降级） → try-except 降级

- [ ] 2.2 编写伪代码
  - [ ] 2.2.1 编写 `lobster_assemble` 的新实现伪代码
  - [ ] 2.2.2 确认与现有接口的兼容性

---

## 设计决策

### 压缩流程顺序

```
1. 获取三层记忆（working/episodic/semantic）
2. 对 working 层：
   a. EventSegmenter.segment() → 分割为情节
   b. ThreePassTrimmer.trim() → 压缩每个情节
3. 按 30%:30%:40% 预算分配返回
```

### 错误处理

```python
try:
    # 尝试压缩
    compressed = trimmer.trim(messages)
except Exception as e:
    # 降级：返回原始内容
    logger.warning(f"ThreePassTrimmer 失败: {e}")
    compressed = messages
```

### 伪代码

```python
def lobster_assemble(conversation_id, token_budget=8000, tiers=["semantic", "episodic", "working"]):
    # 1. 获取三层记忆
    context = db.get_context_by_tier(conversation_id, tiers)
    
    # 2. 对 working 层进行压缩处理
    if 'working' in context and context['working']:
        try:
            # 2a. 事件分割
            from pipeline.event_segmenter import EventSegmenter
            segmenter = EventSegmenter()
            episodes = segmenter.segment(context['working'])
            
            # 2b. 对每个情节进行三遍压缩
            from three_pass_trimmer import ThreePassTrimmer
            trimmer = ThreePassTrimmer()
            compressed_episodes = []
            for episode in episodes:
                trimmed, stats = trimmer.trim(episode)
                compressed_episodes.append(trimmed)
            
            # 2c. 合并压缩后的情节
            context['working'] = []
            for episode in compressed_episodes:
                context['working'].extend(episode)
                
        except Exception as e:
            # 降级：返回原始内容
            logger.warning(f"压缩失败: {e}，使用原始内容")
    
    # 3. 按预算分配返回
    assembled = []
    tier_ratios = {"semantic": 0.30, "episodic": 0.30, "working": 0.40}
    tier_budgets = {t: int(token_budget * tier_ratios.get(t, 0.33)) for t in tiers}
    
    used_tokens = 0
    for tier in tiers:
        tier_used = 0
        tier_budget = tier_budgets[tier]
        for item in context.get(tier, []):
            item_tokens = item.get('token_count', 0)
            if tier_used + item_tokens > tier_budget:
                break
            assembled.append({"tier": tier, **item})
            tier_used += item_tokens
        used_tokens += tier_used
    
    return {
        "assembled": assembled,
        "total_tokens": used_tokens,
        "token_budget": token_budget,
        "tier_breakdown": {t: len([x for x in assembled if x['tier'] == t]) for t in tiers}
    }
```

### 3. 实施阶段

- [x] 3.1 修改 `lobster_mcp_server.py` ✅
  - [x] 3.1.1 添加模块导入 ✅
  - [x] 3.1.2 修改 `lobster_assemble` 实现 ✅
  - [x] 3.1.3 添加调试日志 ✅（使用 print 语句）

- [x] 3.2 本地测试 ✅
  - [x] 3.2.1 测试 `three_pass_trimmer` 功能 ✅
  - [x] 3.2.2 测试 `event_segmenter` 功能 ✅
  - [x] 3.2.3 测试 `semantic_dedup` 功能 → 跳过（暂不使用）
  - [x] 3.2.4 测试完整的 `lobster_assemble` 流程 ✅

### 4. 验证阶段

- [x] 4.1 构建和打包 ✅
  - [x] 4.1.1 运行 `npm run build` ✅
  - [x] 4.1.2 运行 `npm pack` ✅
  - [x] 4.1.3 验证打包文件完整性 ✅

- [x] 4.2 在小文机器上测试 ✅
  - [x] 4.2.1 上传新版本到小文机器 ✅
  - [x] 4.2.2 重启 OpenClaw Gateway ✅
  - [x] 4.2.3 测试记忆召回效果 ✅
  - [x] 4.2.4 验证重复内容是否被去重 ✅

**测试结果**: 20 条消息，压缩率 **85.5%**（5315 → 769 tokens）

### 5. 发布阶段

- [ ] 5.1 版本更新
  - [ ] 5.1.1 更新 `package.json` 版本号
  - [ ] 5.1.2 更新 `src/__init__.py` 版本号
  - [ ] 5.1.3 更新 `src/database.py` 版本号
  - [ ] 5.1.4 更新 `mcp_server/lobster_mcp_server.py` 版本号
  - [ ] 5.1.5 更新 `README.md` 版本号
  - [ ] 5.1.6 添加 `CHANGELOG.md` 条目

- [ ] 5.2 发布流程
  - [ ] 5.2.1 提交代码到 Git
  - [ ] 5.2.2 创建 Git tag
  - [ ] 5.2.3 推送 tag 到 GitHub
  - [ ] 5.2.4 创建 GitHub Release
  - [ ] 5.2.5 发布到 npmjs.org
  - [ ] 5.2.6 发布到 GitHub Packages
  - [ ] 5.2.7 验证 npm 版本
  - [ ] 5.2.8 验证 GitHub Packages 版本

---

## 预计时间

| 阶段 | 预计时间 |
|------|---------|
| 1. 准备阶段 | 30 分钟 |
| 2. 设计阶段 | 20 分钟 |
| 3. 实施阶段 | 60 分钟 |
| 4. 验证阶段 | 40 分钟 |
| 5. 发布阶段 | 30 分钟 |
| **总计** | **3 小时** |

---

## 开始时间

2026-03-25 15:07 UTC

## 当前状态

准备开始 1.1.1：阅读 `three_pass_trimmer.py`
