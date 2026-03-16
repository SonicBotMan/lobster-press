# 🦞 LobsterPress 优化提案 - 基于 lossless-claw 经验

**日期**: 2026-03-16  
**作者**: 小云 (基于 lossless-claw 研究)  
**目标**: 将 LobsterPress 从"一次性压缩工具"升级为"无损记忆系统"

---

## 📊 当前状态 vs 目标状态

| 维度 | LobsterPress (当前) | lossless-claw | 目标 |
|------|---------------------|---------------|------|
| **压缩方式** | 一次性压缩 | 增量压缩 | ✅ 增量压缩 |
| **记忆保留** | 有损（丢弃消息） | 无损（永久保存） | ✅ 无损存储 |
| **摘要结构** | 单层摘要 | DAG 层次结构 | ✅ DAG 结构 |
| **搜索能力** | 无 | FTS5 全文搜索 | ✅ 全文搜索 |
| **展开能力** | 无 | 按需展开 | ✅ 摘要展开 |
| **Agent 工具** | 无 | 3 个工具 | ✅ 3+ 工具 |
| **数据存储** | JSONL 文件 | SQLite 数据库 | ✅ SQLite |

---

## 🎯 核心优化方向

### 1️⃣ **DAG 层次化摘要结构**

**当前问题：**
- LobsterPress 只生成单层摘要
- 无法追溯原始消息
- 无法建立层次关系

**lossless-claw 方案：**
```
消息层 (Messages)
    ↓
叶子摘要 (Leaf Summaries, depth=0)
    ↓
压缩摘要 (Condensed Summaries, depth=1+)
    ↓
DAG 结构形成
```

**优化方案：**

#### 数据库设计
```sql
-- 消息表（永久保存）
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    message_id TEXT UNIQUE,
    conversation_id TEXT,
    seq INTEGER,
    role TEXT,
    content TEXT,
    token_count INTEGER,
    created_at TEXT,
    metadata JSON
);

-- 摘要表（DAG 结构）
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY,
    summary_id TEXT UNIQUE,
    conversation_id TEXT,
    kind TEXT, -- 'leaf' or 'condensed'
    depth INTEGER,
    content TEXT,
    token_count INTEGER,
    earliest_at TEXT,
    latest_at TEXT,
    descendant_count INTEGER,
    created_at TEXT
);

-- 摘要-消息关系（叶子摘要）
CREATE TABLE summary_messages (
    summary_id TEXT,
    message_id TEXT,
    PRIMARY KEY (summary_id, message_id)
);

-- 摘要-摘要关系（压缩摘要）
CREATE TABLE summary_parents (
    summary_id TEXT,
    parent_summary_id TEXT,
    PRIMARY KEY (summary_id, parent_summary_id)
);

-- 上下文项（当前可见内容）
CREATE TABLE context_items (
    conversation_id TEXT,
    ordinal INTEGER,
    item_type TEXT, -- 'message' or 'summary'
    item_id TEXT,
    PRIMARY KEY (conversation_id, ordinal)
);
```

#### 压缩策略
```python
class DAGCompressor:
    """DAG 压缩器 - 借鉴 lossless-claw"""
    
    def leaf_compact(self, messages: List[Dict], chunk_tokens=20000) -> Summary:
        """叶子压缩：消息 → 叶子摘要"""
        # 1. 选择最老的连续消息块（排除 fresh tail）
        chunk = self.select_chunk(messages, max_tokens=chunk_tokens)
        
        # 2. 生成摘要（使用现有的 TF-IDF + Embedding + 提取式摘要）
        summary_content = self.generate_summary(chunk)
        
        # 3. 保存摘要和关系
        summary = Summary(
            kind='leaf',
            depth=0,
            content=summary_content,
            source_messages=[m['id'] for m in chunk]
        )
        
        return summary
    
    def condensed_compact(self, summaries: List[Summary], min_fanout=4) -> Summary:
        """压缩摘要：摘要 → 更高层的摘要"""
        # 1. 找到同深度的连续摘要（≥ min_fanout）
        if len(summaries) < min_fanout:
            return None
        
        # 2. 合并摘要内容
        combined_content = self.combine_summaries(summaries)
        
        # 3. 生成更高层的摘要
        summary = Summary(
            kind='condensed',
            depth=max(s.depth for s in summaries) + 1,
            content=self.generate_condensed_summary(combined_content),
            parent_summaries=[s.id for s in summaries]
        )
        
        return summary
```

---

### 2️⃣ **无损存储 + 全文搜索**

**当前问题：**
- 压缩后丢弃原始消息
- 无法搜索历史
- 无法恢复细节

**lossless-claw 方案：**
- 所有消息永久保存到 SQLite
- FTS5 全文搜索
- 大文件单独存储

**优化方案：**

#### 数据库初始化
```python
import sqlite3

def init_database(db_path='lobster_press.db'):
    """初始化数据库 - 借鉴 lossless-claw"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建表（见上面的 SQL）
    # ...
    
    # 创建 FTS5 索引（全文搜索）
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
        USING fts5(
            message_id,
            content,
            content='messages',
            content_rowid='id'
        );
    """)
    
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS summaries_fts 
        USING fts5(
            summary_id,
            content,
            content='summaries',
            content_rowid='id'
        );
    """)
    
    conn.commit()
    return conn
```

#### 全文搜索 API
```python
def search_messages(query: str, limit=50) -> List[Dict]:
    """搜索消息 - 借鉴 lcm_grep"""
    cursor.execute("""
        SELECT m.*, snippet(messages_fts, 1, '>>>', '<<<', '...', 10) as snippet
        FROM messages m
        JOIN messages_fts fts ON m.id = fts.rowid
        WHERE messages_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))
    
    return cursor.fetchall()

def search_summaries(query: str, limit=50) -> List[Dict]:
    """搜索摘要 - 借鉴 lcm_grep"""
    cursor.execute("""
        SELECT s.*, snippet(summaries_fts, 1, '>>>', '<<<', '...', 10) as snippet
        FROM summaries s
        JOIN summaries_fts fts ON s.id = fts.rowid
        WHERE summaries_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))
    
    return cursor.fetchall()
```

---

### 3️⃣ **Agent 工具（搜索、描述、展开）**

**当前问题：**
- 无 Agent 工具
- 无法与 AI Agent 集成
- 无法智能查询

**lossless-claw 方案：**
- `lcm_grep` - 搜索消息和摘要
- `lcm_describe` - 查看摘要详情
- `lcm_expand_query` - 展开摘要回答问题

**优化方案：**

#### 工具 1: lobster_grep
```python
def lobster_grep(
    pattern: str,
    mode: str = "regex",  # or "full_text"
    scope: str = "both",  # "messages", "summaries", "both"
    limit: int = 50
) -> List[Dict]:
    """搜索消息和摘要 - 借鉴 lcm_grep
    
    Args:
        pattern: 搜索模式
        mode: "regex" 或 "full_text"
        scope: "messages", "summaries", 或 "both"
        limit: 最大结果数
    
    Returns:
        匹配结果列表
    """
    results = []
    
    if scope in ["messages", "both"]:
        if mode == "full_text":
            results.extend(search_messages(pattern, limit))
        else:
            # Regex 搜索
            cursor.execute("""
                SELECT * FROM messages
                WHERE content REGEXP ?
                LIMIT ?
            """, (pattern, limit))
            results.extend(cursor.fetchall())
    
    if scope in ["summaries", "both"]:
        if mode == "full_text":
            results.extend(search_summaries(pattern, limit))
        else:
            cursor.execute("""
                SELECT * FROM summaries
                WHERE content REGEXP ?
                LIMIT ?
            """, (pattern, limit))
            results.extend(cursor.fetchall())
    
    return results
```

#### 工具 2: lobster_describe
```python
def lobster_describe(summary_id: str) -> Dict:
    """查看摘要详情 - 借鉴 lcm_describe
    
    Args:
        summary_id: 摘要 ID
    
    Returns:
        摘要详情（包括内容、元数据、子节点等）
    """
    # 获取摘要
    cursor.execute("SELECT * FROM summaries WHERE summary_id = ?", (summary_id,))
    summary = cursor.fetchone()
    
    if not summary:
        return {"error": "Summary not found"}
    
    # 获取子节点
    if summary['kind'] == 'leaf':
        cursor.execute("""
            SELECT m.* FROM messages m
            JOIN summary_messages sm ON m.message_id = sm.message_id
            WHERE sm.summary_id = ?
        """, (summary_id,))
        children = cursor.fetchall()
    else:
        cursor.execute("""
            SELECT s.* FROM summaries s
            JOIN summary_parents sp ON s.summary_id = sp.parent_summary_id
            WHERE sp.summary_id = ?
        """, (summary_id,))
        children = cursor.fetchall()
    
    return {
        **summary,
        "children": children,
        "children_count": len(children)
    }
```

#### 工具 3: lobster_expand
```python
def lobster_expand(summary_id: str) -> List[Dict]:
    """展开摘要 - 借鉴 lcm_expand
    
    Args:
        summary_id: 摘要 ID
    
    Returns:
        原始消息列表（递归展开 DAG）
    """
    summary = lobster_describe(summary_id)
    
    if summary['kind'] == 'leaf':
        # 叶子摘要：直接返回源消息
        return summary['children']
    else:
        # 压缩摘要：递归展开所有子摘要
        all_messages = []
        for child in summary['children']:
            all_messages.extend(lobster_expand(child['summary_id']))
        return all_messages
```

---

### 4️⃣ **增量压缩策略**

**当前问题：**
- 批量处理，无法增量
- 每次重新压缩所有内容

**lossless-claw 方案：**
- 增量压缩（after each turn）
- 保护 fresh tail（最近 N 条消息）
- 智能触发（75% 上下文窗口）

**优化方案：**

```python
class IncrementalCompressor:
    """增量压缩器 - 借鉴 lossless-claw"""
    
    def __init__(self, 
                 fresh_tail_count=32,
                 context_threshold=0.75,
                 leaf_chunk_tokens=20000):
        self.fresh_tail_count = fresh_tail_count
        self.context_threshold = context_threshold
        self.leaf_chunk_tokens = leaf_chunk_tokens
    
    def after_turn(self, conversation_id: str):
        """每次对话后检查是否需要压缩"""
        # 1. 获取当前上下文大小
        context_tokens = self.get_context_tokens(conversation_id)
        max_tokens = self.get_max_tokens()
        
        # 2. 检查是否超过阈值
        if context_tokens / max_tokens < self.context_threshold:
            return  # 无需压缩
        
        # 3. 执行增量压缩
        self.incremental_compact(conversation_id)
    
    def incremental_compact(self, conversation_id: str):
        """增量压缩"""
        # 1. 获取所有消息
        messages = self.get_all_messages(conversation_id)
        
        # 2. 分离 fresh tail
        fresh_tail = messages[-self.fresh_tail_count:]
        older_messages = messages[:-self.fresh_tail_count]
        
        # 3. 检查是否需要叶子压缩
        older_tokens = sum(m['token_count'] for m in older_messages)
        if older_tokens > self.leaf_chunk_tokens:
            # 执行叶子压缩
            summary = self.leaf_compact(older_messages)
            self.save_summary(summary)
            
            # 更新上下文项
            self.update_context_items(conversation_id, summary)
        
        # 4. 检查是否需要压缩摘要
        self.check_condensation(conversation_id)
    
    def check_condensation(self, conversation_id: str):
        """检查是否需要压缩摘要"""
        # 获取所有叶子摘要
        leaf_summaries = self.get_summaries(conversation_id, depth=0)
        
        # 检查是否有足够的连续摘要
        if len(leaf_summaries) >= 4:  # min_fanout
            # 执行压缩摘要
            condensed = self.condensed_compact(leaf_summaries)
            self.save_summary(condensed)
            
            # 更新上下文项
            self.update_context_items(conversation_id, condensed)
```

---

## 🚀 实施路线图

### Phase 1: 数据库基础（1-2 周）
- [ ] 设计数据库 schema（messages, summaries, context_items）
- [ ] 实现 SQLite 存储
- [ ] 实现 FTS5 全文搜索
- [ ] 迁移现有 JSONL 到 SQLite

### Phase 2: DAG 结构（2-3 周）
- [ ] 实现叶子压缩（messages → leaf summaries）
- [ ] 实现压缩摘要（summaries → condensed summaries）
- [ ] 建立摘要关系表（summary_messages, summary_parents）
- [ ] 实现 DAG 可视化

### Phase 3: Agent 工具（1-2 周）
- [ ] 实现 `lobster_grep` 工具
- [ ] 实现 `lobster_describe` 工具
- [ ] 实现 `lobster_expand` 工具
- [ ] 集成到 OpenClaw Skill

### Phase 4: 增量压缩（2-3 周）
- [ ] 实现增量压缩逻辑
- [ ] 实现 fresh tail 保护
- [ ] 实现智能触发
- [ ] 测试和优化

### Phase 5: 高级功能（可选）
- [ ] 实现 `lobster_expand_query`（子代理展开）
- [ ] 实现大文件存储（借鉴 lossless-claw）
- [ ] 实现跨会话搜索
- [ ] 实现 Web UI

---

## 📊 预期收益

| 维度 | 当前 | 优化后 | 提升 |
|------|------|--------|------|
| **记忆保留** | 有损 | 无损 | ∞ |
| **搜索能力** | 无 | FTS5 | ✅ |
| **展开能力** | 无 | DAG 展开 | ✅ |
| **Agent 集成** | 无 | 3 个工具 | ✅ |
| **压缩质量** | 单层 | 多层 DAG | 📈 |
| **可追溯性** | 无 | 完整追溯 | ✅ |

---

## 🎯 优先级建议

**P0（必须）:**
1. ✅ 数据库存储（SQLite）
2. ✅ FTS5 全文搜索
3. ✅ DAG 层次结构

**P1（重要）:**
1. ✅ Agent 工具（grep, describe, expand）
2. ✅ 增量压缩
3. ✅ Fresh tail 保护

**P2（可选）:**
1. 🔄 lobster_expand_query（子代理）
2. 🔄 大文件存储
3. 🔄 Web UI

---

## 💡 关键借鉴点

### 从 lossless-claw 学到的

1. **无损存储是基础**
   - 所有消息永久保存
   - SQLite 比 JSONL 更适合查询

2. **DAG 结构是核心**
   - 叶子摘要 + 压缩摘要
   - 层次化压缩，可追溯

3. **工具化是关键**
   - 搜索、描述、展开
   - Agent 可直接使用

4. **增量压缩是趋势**
   - 每次对话后检查
   - 保护 recent messages

5. **FTS5 是标配**
   - 全文搜索是刚需
   - SQLite 原生支持

---

## 🔗 参考资源

- **lossless-claw GitHub**: https://github.com/Martian-Engineering/lossless-claw
- **lossless-claw 文档**: https://github.com/Martian-Engineering/lossless-claw/tree/main/docs
- **LCM 论文**: https://papers.voltropy.com/LCM
- **SQLite FTS5**: https://www.sqlite.org/fts5.html

---

## 📝 总结

**核心思路：**
将 LobsterPress 从"一次性压缩工具"升级为"无损记忆系统"

**关键改变：**
1. JSONL → SQLite（永久存储）
2. 单层摘要 → DAG 结构（层次化）
3. 无搜索 → FTS5 全文搜索
4. 无工具 → 3 个 Agent 工具
5. 批量压缩 → 增量压缩

**预期效果：**
- 🚀 **无损记忆** - 永不丢失信息
- 🔍 **智能搜索** - 随时查找历史
- 🧠 **层次压缩** - DAG 结构可追溯
- 🤖 **Agent 集成** - AI 可直接使用
- ⚡ **增量处理** - 实时压缩，无需等待

---

**下一步：**
1. 评审这个提案
2. 确定 Phase 1 的具体任务
3. 开始实施

**让我们一起把 LobsterPress 打造成 lossless-claw 级别的无损记忆系统！** 🦞✨
