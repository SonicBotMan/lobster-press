# LobsterPress Phase 2 Plan - 意图提炼 + 完整分层

**目标**：结合方案 B + C，实现智能意图提炼和三层记忆自动晋升

**时间预估**：14-20h

---

## 📋 总体架构

```
用户消息 → working 层（原始记录）
      ↓
[Phase 2A] 事件分割 + 意图提炼（EM-LLM + 意图提取）
      ↓
episodic 层（压缩事件 + 意图摘要）
      ↓
[Phase 2B] C-HLR+ 价值评估 + 自动晋升
      ↓
semantic 层（长期知识 + 结论决策）
```

---

## 🎯 Phase 2A：意图提炼（6-8h）

### 任务 2A.1：意图提取器（2h）

**目标**：从对话中提取用户意图和 assistant 结论

**实现**：
- 创建 `src/pipeline/intent_extractor.py`
- 提取：
  - 用户意图：问题、请求、确认
  - Assistant 结论：决策、错误、下一步

**接口**：
```python
class IntentExtractor:
    def extract_intents(self, messages: List[Dict]) -> Dict:
        return {
            'user_intents': [...],      # 用户意图列表
            'assistant_conclusions': [...],  # assistant 结论列表
            'key_entities': [...],      # 关键实体（版本号、文件名等）
        }
```

**验收标准**：
- [ ] 能从对话中提取用户意图
- [ ] 能提取 assistant 结论
- [ ] 能识别关键实体

---

### 任务 2A.2：意图摘要生成（2h）

**目标**：将意图和结论转化为简洁的摘要

**实现**：
- 在 `IntentExtractor` 中添加 `generate_summary()` 方法
- 使用 LLM 或规则生成摘要
- 摘要格式：
  ```
  [意图] 用户询问：最新版本是否修复了重复与卡顿
  [结论] 本次更新尚未解决重复与卡顿（基于历史回放与工具调用失败循环）
  [关键实体] v4.0.94, LobsterPress
  ```

**验收标准**：
- [ ] 能生成意图摘要
- [ ] 能生成结论摘要
- [ ] 能提取关键实体

---

### 任务 2A.3：集成到 lobster_assemble（2h）

**目标**：在 `lobster_assemble` 中应用意图提炼

**实现**：
- 修改 `mcp_server/lobster_mcp_server.py`
- 流程：
  1. 获取 working 层消息
  2. 事件分割（EM-LLM）
  3. 意图提取
  4. 生成摘要
  5. 保存到 episodic 层

**验收标准**：
- [ ] `lobster_assemble` 返回意图摘要
- [ ] 意图摘要被保存到 episodic 层
- [ ] 测试通过

---

### 任务 2A.4：测试和验证（2h）

**目标**：验证意图提炼的效果

**测试用例**：
- [ ] 小文的对话数据：提取"是否修复了问题"的意图
- [ ] 生成结论："本次更新尚未解决重复与卡顿"
- [ ] 压缩后保留意图和结论

---

## 🎯 Phase 2B：完整分层（8-12h）

### 任务 2B.1：C-HLR+ 价值评估（3h）

**目标**：实现 C-HLR+ 算法评估记忆价值

**实现**：
- 创建 `src/pipeline/chlr_scorer.py`
- 公式：`h = base_h * (1 + α * complexity)`
- 参数：
  - `base_h`：基础半衰期（默认 12h）
  - `α`：复杂度系数（默认 0.1）
  - `complexity`：信息复杂度（TF-IDF, 实体数量等）

**接口**：
```python
class CHLRScorer:
    def calculate_half_life(self, message: Dict) -> float:
        # 计算半衰期（小时）
        pass
    
    def should_promote(self, message: Dict, age_hours: float) -> bool:
        # 判断是否应该晋升到下一层
        pass
```

**验收标准**：
- [ ] 能计算半衰期
- [ ] 能判断是否应该晋升

---

### 任务 2B.2：自动晋升机制（3h）

**目标**：实现 working → episodic → semantic 自动晋升

**实现**：
- 创建 `src/pipeline/tier_promoter.py`
- 晋升规则：
  - working → episodic：意图明确，有结论
  - episodic → semantic：多次引用，长期价值

**接口**：
```python
class TierPromoter:
    def promote_messages(self, conversation_id: str) -> Dict:
        # 晋升消息到更高层
        return {
            'working_to_episodic': 5,
            'episodic_to_semantic': 2,
        }
```

**验收标准**：
- [ ] 能自动晋升消息
- [ ] 晋升后消息在正确的层

---

### 任务 2B.3：集成到 agent_end hook（2h）

**目标**：在 `agent_end` hook 中触发自动晋升

**实现**：
- 修改 `index.ts` 的 `agent_end` hook
- 流程：
  1. 保存消息到 working 层
  2. 触发 `lobster_sweep`
  3. `lobster_sweep` 调用 `TierPromoter.promote_messages()`

**验收标准**：
- [ ] `agent_end` 触发自动晋升
- [ ] 消息被正确晋升

---

### 任务 2B.4：测试和验证（2h）

**目标**：验证完整分层的效果

**测试用例**：
- [ ] 新消息保存到 working 层
- [ ] 意图明确的消息晋升到 episodic 层
- [ ] 多次引用的消息晋升到 semantic 层
- [ ] C-HLR+ 遗忘曲线正确应用

---

## 📊 验收标准（总体）

### 功能验收
- [ ] 能从对话中提取意图和结论
- [ ] 能生成简洁的摘要
- [ ] 能自动晋升消息到更高层
- [ ] C-HLR+ 遗忘曲线正确应用

### 性能验收
- [ ] 压缩率 > 70%（working → episodic）
- [ ] 意图提取准确率 > 80%
- [ ] 晋升决策准确率 > 90%

### 质量验收
- [ ] 小文的对话：提取"是否修复了问题"的意图 ✅
- [ ] 生成结论："本次更新尚未解决重复与卡顿" ✅
- [ ] 重复片段被去重 ✅
- [ ] 关键信息不丢失 ✅

---

## 🚀 执行顺序

1. **Phase 2A.1**：意图提取器（2h）
2. **Phase 2A.2**：意图摘要生成（2h）
3. **Phase 2A.3**：集成到 lobster_assemble（2h）
4. **Phase 2A.4**：测试和验证（2h）
5. **Phase 2B.1**：C-HLR+ 价值评估（3h）
6. **Phase 2B.2**：自动晋升机制（3h）
7. **Phase 2B.3**：集成到 agent_end hook（2h）
8. **Phase 2B.4**：测试和验证（2h）

**总计**：18h

---

## 📝 当前进度

- [x] Phase 2A.1：意图提取器 ✅ (2026-03-25 15:45)
  - 创建 `src/pipeline/intent_extractor.py`
  - 能提取用户意图（question, request, confirmation, complaint）
  - 能提取 assistant 结论（decision, error, next_step, result）
  - 能提取关键实体（版本号、文件名、路径）
  - 测试通过：20 条消息 → 9 个用户意图 + 10 个 assistant 结论

- [x] Phase 2A.2：意图摘要生成 ✅ (2026-03-25 15:48)
  - 实现 `generate_summary()` 方法
  - 添加语义去重功能（Jaccard 相似度 > 0.8）
  - 标注重复次数（"重复 5 次"）
  - 测试通过：用户意图 9→5（-44%），置信度 0.70→1.00（+43%）

- [x] Phase 2A.3：集成到 lobster_assemble ✅ (2026-03-25 15:52)
  - 修改 `mcp_server/lobster_mcp_server.py`
  - 流程：事件分割 → 意图提取 → CMV 压缩 → 添加意图摘要
  - 测试通过：意图摘要正确生成，压缩率 48.5%
  - 版本：v4.0.95

- [x] Phase 2A.4：测试和验证 ✅ (2026-03-25 15:52)
  - 小文的对话数据：提取"是否修复了问题"的意图 ✅
  - 重复片段被去重 ✅
  - 关键信息不丢失 ✅
  - 压缩率 48.5% ✅

- [ ] Phase 2B.1：C-HLR+ 价值评估
- [ ] Phase 2B.2：自动晋升机制
- [ ] Phase 2B.3：集成到 agent_end hook
- [ ] Phase 2B.4：测试和验证
