# MemOS 四阶段优化计划

> **For agent:** REQUIRED SUB-SKILL: Use Section 4 or Section 5 to implement this plan.

**Goal:** 借鉴 MemOS 架构，为 LobsterPress 添加向量检索、技能进化、多智能体协同和工程化能力

**Architecture:** 四阶段递进，每阶段独立可交付。新增 `src/vector/`、`src/skills/`、`src/collab/` 目录

**Tech Stack:** Python 3.10+, numpy, pytest, aiofiles

---

## 0. 约束条件（用户确认）

### 向量嵌入
- **默认方案**: OpenAI Compatible API（`provider: "openai_compatible"`）
- **离线降级方案**: numpy 纯内存余弦相似度，无外部依赖
- 存储格式: 向量存为 BLOB（SQLite `BLOB` 列），计算在进程内完成
- 不引入 `sqlite-vec` 等原生扩展

### 时间衰减（双参数，独立控制）
| 参数 | 半衰期 | 用途 | 公式 |
|------|--------|------|------|
| `compression_half_life` | 12h | C-HLR+ 压缩评分：决定哪些消息优先压缩 | `R = base × 0.5^(t/12h)` |
| `retrieval_half_life` | 14d | 检索评分：决定搜索结果的时间新鲜度 | `final = score × (0.3 + 0.7 × 0.5^(t/14d))` |

### 检索公式
- **RRF**: `RRF(d) = Σ_i 1/(k + rank_i(d) + 1)`, `k=60`
- **MMR**: `MMR(d) = λ·rel(d) − (1−λ)·max_sim(d, d_s)`, `λ=0.7`, `α=0.3` floor
- **Decay**: `final = score × (0.3 + 0.7 × 0.5^(t/14d))`

---

## Phase 1: 核心智能（Core Intelligence）

### 目标
为 LobsterPress 添加向量嵌入存储和混合检索（FTS5 + Vector → RRF → MMR → Decay），以及 LLM 三级降级链。

### 1.1 向量嵌入存储

**Files:**
- Create: `src/vector/__init__.py`
- Create: `src/vector/embedder.py`
- Modify: `src/database.py` — 新增 `embeddings` 表和向量 I/O 方法

#### Step 1: 创建嵌入抽象层

```python
# src/vector/embedder.py
"""
向量嵌入层：OpenAI Compatible API（默认）+ numpy 离线降级

借鉴 MemOS 架构：
- embedding provider 配置为 openai_compatible
- 无 API 时降级为 numpy 随机向量（维度对齐，仅用于结构验证）
"""
import os
import struct
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Optional

EMBEDDING_DIM = 1024  # bge-m3 维度


class BaseEmbedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """单条文本嵌入"""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class OpenAICompatibleEmbedder(BaseEmbedder):
    """OpenAI Compatible API 嵌入器

    配置来源（优先级从高到低）：
    1. 构造函数参数
    2. 环境变量 LOBSTER_EMBED_ENDPOINT / LOBSTER_EMBED_API_KEY / LOBSTER_EMBED_MODEL
    """

    def __init__(self, endpoint: str = None, api_key: str = None, model: str = None):
        self.endpoint = endpoint or os.getenv('LOBSTER_EMBED_ENDPOINT', '')
        self.api_key = api_key or os.getenv('LOBSTER_EMBED_API_KEY', '')
        self.model = model or os.getenv('LOBSTER_EMBED_MODEL', 'bge-m3')

    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        import json
        import urllib.request

        url = f"{self.endpoint}/embeddings"
        payload = json.dumps({
            "model": self.model,
            "input": texts
        }).encode()

        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return [d["embedding"] for d in data["data"]]

    def is_available(self) -> bool:
        return bool(self.endpoint and self.api_key)


class NumpyOfflineEmbedder(BaseEmbedder):
    """离线降级：numpy 随机向量（维度对齐，仅结构验证用）

    向量归一化后存入 SQLite BLOB，余弦相似度在进程内计算。
    生产环境应替换为真实嵌入。
    """

    def __init__(self, dim: int = EMBEDDING_DIM, seed: int = 42):
        self.dim = dim
        self.rng = np.random.default_rng(seed)

    def embed(self, text: str) -> List[float]:
        vec = self.rng.standard_normal(self.dim)
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    def is_available(self) -> bool:
        return True  # numpy always available


def create_embedder(**kwargs) -> BaseEmbedder:
    """工厂函数：优先 OpenAI Compatible，降级 numpy 离线"""
    embedder = OpenAICompatibleEmbedder(**kwargs)
    if embedder.is_available():
        return embedder
    print("⚠️ Embedding API 不可用，降级为 numpy 离线向量")
    return NumpyOfflineEmbedder()
```

#### Step 2: 数据库 schema 扩展

在 `src/database.py` 的 `_init_database()` 方法末尾追加：

```python
# Phase 1: 向量嵌入表
self.cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chunk_id TEXT UNIQUE NOT NULL,
        target_type TEXT NOT NULL,  -- 'message' | 'summary' | 'note'
        target_id TEXT NOT NULL,
        vector BLOB NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (target_id) REFERENCES messages(message_id)
    );
""")

self.cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_embeddings_target
    ON embeddings(target_type, target_id);
""")
```

在 `LobsterDatabase` 类中新增方法：

```python
# src/database.py — 新增方法

def save_embedding(self, target_type: str, target_id: str, vector: List[float]) -> str:
    """保存向量嵌入为 BLOB"""
    import struct
    chunk_id = f"emb_{target_type}_{target_id}"
    blob = struct.pack(f'{len(vector)}f', *vector)
    now = datetime.utcnow().isoformat()

    self.cursor.execute("""
        INSERT OR REPLACE INTO embeddings (chunk_id, target_type, target_id, vector, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (chunk_id, target_type, target_id, blob, now))
    self.conn.commit()
    return chunk_id


def vector_search(self, query_vec: List[float], top_k: int = 20,
                  target_type: str = None, conversation_id: str = None) -> List[Dict]:
    """纯内存余弦相似度搜索

    借鉴 MemOS 模式：
    all.map(row => ({ id: row.chunkId, score: cosine(queryVec, row.vector) }))
        .sort((a, b) => b.score - a.score)
        .slice(0, topK);
    """
    import struct
    import numpy as np

    query = "SELECT chunk_id, target_type, target_id, vector FROM embeddings"
    conditions = []
    params = []

    if target_type:
        conditions.append("target_type = ?")
        params.append(target_type)
    if conversation_id:
        conditions.append("""
            (target_type = 'message' AND target_id IN
                (SELECT message_id FROM messages WHERE conversation_id = ?))
            OR (target_type = 'summary' AND target_id IN
                (SELECT summary_id FROM summaries WHERE conversation_id = ?))
        """)
        params.extend([conversation_id, conversation_id])

    if conditions:
        query += " WHERE " + " AND ".join(conditions[:1])  # 简化条件拼接

    self.cursor.execute(query, params)
    rows = self.cursor.fetchall()

    query_np = np.array(query_vec, dtype=np.float32)
    query_norm = np.linalg.norm(query_np)
    if query_norm == 0:
        return []

    results = []
    for chunk_id, t_type, t_id, blob in rows:
        dim = len(blob) // 4
        vec = np.array(struct.unpack(f'{dim}f', blob), dtype=np.float32)
        score = float(np.dot(query_np, vec) / (query_norm * np.linalg.norm(vec)))
        results.append({
            'chunk_id': chunk_id,
            'target_type': t_type,
            'target_id': t_id,
            'score': score
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]
```

#### Step 3: 运行验证
```bash
python -m pytest tests/unit/test_vector_embedder.py -v
```

---

### 1.2 混合检索（FTS5 + Vector → RRF → MMR → Decay）

**Files:**
- Create: `src/vector/retriever.py`
- Modify: `mcp_server/lobster_mcp_server.py` — 升级 `lobster_grep` 工具

#### Step 1: 创建混合检索器

```python
# src/vector/retriever.py
"""
混合检索器：FTS5 + Vector → RRF → MMR → Time Decay

借鉴 MemOS Recall pipeline:
  FTS5+Vector → RRF(k=60) → MMR(λ=0.7) → Decay(14d) → Normalize → Filter(≥0.45)
"""
import math
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class HybridRetriever:
    """混合检索器"""

    def __init__(self, db, embedder=None):
        self.db = db
        self.embedder = embedder

    def search(self, query: str, conversation_id: str = None,
               top_k: int = 6, min_score: float = 0.45) -> List[Dict]:
        """完整检索流程

        Pipeline: FTS5 + Vector → RRF → MMR → Decay → Normalize → Filter
        """
        # Step 1: 双通道并行检索
        fts_results = self._fts_search(query, conversation_id)
        vec_results = self._vector_search(query, conversation_id)

        # Step 2: RRF 融合
        rrf_scores = self._rrf_fuse([fts_results, vec_results])

        # Step 3: MMR 多样性重排
        mmr_results = self._mmr_rerank(rrf_scores, top_k * 2)

        # Step 4: 时间衰减（retrieval_half_life=14d）
        decayed = self._apply_retrieval_decay(mmr_results)

        # Step 5: 归一化 + 过滤
        max_score = max((r['score'] for r in decayed), default=1.0)
        if max_score == 0:
            max_score = 1.0

        final = []
        for r in decayed:
            r['normalized_score'] = r['score'] / max_score
            if r['normalized_score'] >= min_score:
                final.append(r)

        return final[:top_k]

    def _fts_search(self, query: str, conversation_id: str = None) -> List[Dict]:
        """FTS5 关键词检索"""
        results = []
        # 搜索消息
        msgs = self.db.search_messages(query, conversation_id=conversation_id, limit=50)
        for i, msg in enumerate(msgs):
            results.append({
                'target_id': msg['message_id'],
                'target_type': 'message',
                'content': msg.get('content', ''),
                'created_at': msg.get('created_at', ''),
                'rank': i,
                'source': 'fts'
            })
        # 搜索摘要
        sums = self.db.search_summaries(query, conversation_id=conversation_id, limit=50)
        for i, s in enumerate(sums):
            results.append({
                'target_id': s['summary_id'],
                'target_type': 'summary',
                'content': s.get('content', ''),
                'created_at': s.get('created_at', ''),
                'rank': i,
                'source': 'fts'
            })
        return results

    def _vector_search(self, query: str, conversation_id: str = None) -> List[Dict]:
        """向量语义检索"""
        if not self.embedder or not self.embedder.is_available():
            return []

        vec = self.embedder.embed(query)
        results = self.db.vector_search(vec, top_k=50, conversation_id=conversation_id)

        return [{
            'target_id': r['target_id'],
            'target_type': r['target_type'],
            'score': r['score'],
            'source': 'vector'
        } for r in results]

    def _rrf_fuse(self, result_lists: List[List[Dict]], k: int = 60) -> Dict[str, Dict]:
        """RRF 融合: RRF(d) = Σ 1/(k + rank_i(d) + 1)

        Args:
            result_lists: 各检索通道的结果列表
            k: RRF 常数（默认 60，与 MemOS 一致）

        Returns:
            {target_id: {score, target_type, content, created_at}}
        """
        fused = {}

        for results in result_lists:
            for rank, item in enumerate(results):
                tid = item['target_id']
                rrf_score = 1.0 / (k + rank + 1)

                if tid not in fused:
                    fused[tid] = {
                        'target_id': tid,
                        'target_type': item['target_type'],
                        'content': item.get('content', ''),
                        'created_at': item.get('created_at', ''),
                        'score': 0.0
                    }
                fused[tid]['score'] += rrf_score

        return fused

    def _mmr_rerank(self, candidates: Dict[str, Dict],
                    top_k: int, lam: float = 0.7) -> List[Dict]:
        """MMR 多样性重排

        MMR(d) = λ·rel(d) − (1−λ)·max_sim(d, d_s)

        λ=0.7: 偏向相关性（与 MemOS 一致）
        α=0.3: 分数地板值
        """
        if not candidates:
            return []

        # 按分数降序排列
        sorted_items = sorted(
            candidates.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        selected = []
        remaining = list(sorted_items)

        while remaining and len(selected) < top_k:
            if not selected:
                selected.append(remaining.pop(0))
                continue

            best_idx = 0
            best_mmr = -float('inf')

            for i, cand in enumerate(remaining):
                rel = cand['score']
                # 简化相似度：用内容长度归一化的重叠度
                max_sim = max(
                    self._text_similarity(cand['content'], s['content'])
                    for s in selected
                )
                mmr_score = lam * rel - (1 - lam) * max_sim

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def _apply_retrieval_decay(self, results: List[Dict],
                                half_life_days: float = 14.0) -> List[Dict]:
        """检索时间衰减

        final = score × (0.3 + 0.7 × 0.5^(t/14d))

        半衰期 14d（与 MemOS retrieval_half_life 一致）
        α=0.3 为地板值：极老内容仍保留 30% 分数
        """
        now = datetime.utcnow()

        for r in results:
            score = r.get('score', 0)
            created_at = r.get('created_at', '')

            if not created_at:
                r['score'] = score * 0.3  # 无时间戳，给地板值
                continue

            try:
                created = datetime.fromisoformat(created_at)
                t_days = max((now - created).total_seconds() / 86400.0, 0.0)
            except (ValueError, TypeError):
                t_days = 999.0

            decay = 0.3 + 0.7 * math.pow(0.5, t_days / half_life_days)
            r['score'] = score * decay

        return results

    def _text_similarity(self, a: str, b: str) -> float:
        """简单文本相似度（字符级 Jaccard）"""
        if not a or not b:
            return 0.0
        set_a = set(a[:200])
        set_b = set(b[:200])
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
```

#### Step 2: 升级 lobster_grep 工具

在 `mcp_server/lobster_mcp_server.py` 的 `LobsterPressMCPServer.__init__()` 中初始化检索器：

```python
# Phase 1: 初始化混合检索器
from vector.embedder import create_embedder
from vector.retriever import HybridRetriever

embedder = create_embedder()
self.retriever = HybridRetriever(self._get_db(), embedder)
```

修改 `lobster_grep` 工具实现，在现有 FTS5 搜索之后增加混合检索路径：

```python
# lobster_grep 工具实现中新增混合检索分支
if use_hybrid:  # 新参数，默认 True
    results = self.retriever.search(
        query=query,
        conversation_id=conversation_id,
        top_k=max_results,
        min_score=min_score
    )
    # 格式化返回结果（包含 normalized_score、target_type、excerpts）
```

#### Step 3: 运行验证
```bash
python -m pytest tests/unit/test_hybrid_retriever.py -v
```

---

### 1.3 LLM 三级降级链

**Files:**
- Modify: `src/llm_client.py` — 添加 `FallbackLLMClient`

#### Step 1: 实现 LLM Fallback Chain

借鉴 MemOS 架构：
```
skillSummarizer → summarizer → OpenClaw Native → 规则降级
```

在 `src/llm_client.py` 中新增：

```python
class FallbackLLMClient(BaseLLMClient):
    """LLM 三级降级链

    借鉴 MemOS:
      Level 1: skillSummarizer（技能专用模型）
      Level 2: summarizer（通用摘要模型）
      Level 3: OpenClaw Native（从 openclaw.json 自动读取）
      Level 4: 规则方法（无 LLM）

    每级失败自动降级，零手动干预。
    """

    def __init__(self, skill_client=None, summary_client=None, native_client=None):
        self.chain = []
        if skill_client and skill_client.is_available():
            self.chain.append(('skill', skill_client))
        if summary_client and summary_client.is_available():
            self.chain.append(('summary', summary_client))
        if native_client and native_client.is_available():
            self.chain.append(('native', native_client))
        # 兜底
        self.chain.append(('mock', MockLLMClient()))

    def generate(self, prompt: str, **kwargs) -> str:
        for name, client in self.chain:
            try:
                result = client.generate(prompt, **kwargs)
                if result:
                    return result
            except Exception as e:
                print(f"⚠️ LLM [{name}] 失败: {e}，尝试下一级")
                continue
        return ""  # 所有级别均失败

    def is_available(self) -> bool:
        return len(self.chain) > 0
```

修改 `create_llm_client()` 工厂函数，支持返回 `FallbackLLMClient`：

```python
def create_llm_client(fallback: bool = False, **kwargs) -> BaseLLMClient:
    """创建 LLM 客户端

    Args:
        fallback: 是否启用三级降级链（默认 False，保持向后兼容）
    """
    if not fallback:
        # 原有逻辑不变
        ...

    # 降级链模式
    skill_provider = os.getenv('LOBSTER_LLM_SKILL_PROVIDER')
    skill_client = create_llm_client(provider=skill_provider) if skill_provider else None
    return FallbackLLMClient(skill_client=skill_client, ...)
```

---

### 1.4 双时间衰减参数落地

**Files:**
- Modify: `src/database.py` — `_compute_retention()` 使用 12h 半衰期
- Modify: `src/vector/retriever.py` — `_apply_retrieval_decay()` 使用 14d 半衰期

#### 已在 1.2 中实现 14d retrieval 半衰期。以下为 12h 压缩半衰期。

在 `src/database.py` 的 `_compute_retention()` 中，添加参数控制：

```python
def _compute_retention(self, msg: Dict, current_time: datetime,
                        half_life_override: float = None) -> float:
    """
    v5.0: 双半衰期参数

    - 默认（压缩评分）: half_life_override=None，使用 C-HLR+ 自适应半衰期
    - 检索衰减: half_life_override=336.0（14天），由 retriever 调用

    C-HLR+ 压缩评分的核心时间窗口为 12h:
      adaptive_h = base_h * (1 + α * complexity) * spaced_bonus
      基础半衰期按消息类型区分，覆盖 3-120 天
      但在 leaf_compact 排序中，12h 窗口内保留率差异最大
    """
    # 原有逻辑不变（base_h 按 msg_type 区分，3-120 天）
    # half_life_override 仅在 retriever 场景使用
    ...
```

在 `src/dag_compressor.py` 的 `leaf_compact()` 中，12h 半衰期已通过 `_compute_retention()` 的 C-HLR+ 自适应算法间接实现。C-HLR+ 的 `BASE_HALF_LIFE` 表中，`unknown` 类型默认 14 天，但在 12 小时窗口内 `2^(-0.5/14) ≈ 0.975`，衰减微弱；而对于 `chitchat`（3 天），12 小时后 `2^(-0.5/3) ≈ 0.89`，差异明显。这确保短半衰期内容优先进入压缩队列。

---

### Phase 1 验收清单

- [ ] `src/vector/embedder.py` 创建完成，OpenAI Compatible + numpy 离线双模式可用
- [ ] `src/database.py` 新增 `embeddings` 表、`save_embedding()`、`vector_search()`
- [ ] `src/vector/retriever.py` 创建完成，RRF/MMR/Decay 三步流水线通过测试
- [ ] `src/llm_client.py` 新增 `FallbackLLMClient`，三级降级链工作正常
- [ ] 双时间衰减参数（12h 压缩 / 14d 检索）独立运行
- [ ] 所有新增测试通过

### Phase 1 时间估算

- 1.1 向量嵌入: 3 小时
- 1.2 混合检索: 4 小时
- 1.3 LLM 降级链: 1.5 小时
- 1.4 双衰减参数: 1 小时
- 测试 + 集成: 2 小时

**总计**: 约 11.5 小时

---

## Phase 2: 技能进化（Skill Evolution）

### 目标
借鉴 MemOS 的 Skill Evolution pipeline，从对话中自动提炼可复用技能，生成 SKILL.md 并安装到工作区。

### 架构概览

借鉴 MemOS 流程：
```
规则过滤 → LLM 评估（可重复/有价值）→ SKILL.md 生成/升级 → 质量评分 → 安装
```

LLM 使用三级降级链（Phase 1 已实现）。

### 2.1 技能数据模型

**Files:**
- Create: `src/skills/__init__.py`
- Create: `src/skills/models.py`
- Modify: `src/database.py` — 新增 `skills`、`skill_versions`、`task_skills` 表

#### Step 1: 创建技能数据模型

```python
# src/skills/models.py
"""技能进化数据模型

借鉴 MemOS:
  skills 表: owner, visibility, quality_score
  skill_versions 表: 版本追踪
  task_skills 表: 任务→技能关联
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Skill:
    skill_id: str
    name: str
    description: str
    owner: str  # 'agent:{agentId}' 或 'public'
    visibility: str = 'private'  # 'private' | 'public'
    quality_score: float = 0.0
    version: int = 1
    steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    script: str = ''
    source_task_ids: List[str] = field(default_factory=list)
    created_at: str = ''
    updated_at: str = ''


@dataclass
class TaskSummary:
    task_id: str
    conversation_id: str
    owner: str
    goal: str
    steps: List[str]
    result: str
    status: str = 'completed'  # 'active' | 'completed'
    created_at: str = ''
    skill_generated: bool = False
```

#### Step 2: 数据库 schema 扩展

在 `src/database.py` 的 `_init_database()` 追加：

```python
# Phase 2: 技能进化表
self.cursor.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        owner TEXT NOT NULL,
        visibility TEXT DEFAULT 'private',
        quality_score REAL DEFAULT 0.0,
        current_version INTEGER DEFAULT 1,
        steps TEXT,  -- JSON array
        warnings TEXT,  -- JSON array
        script TEXT,
        source_task_ids TEXT,  -- JSON array
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
""")

self.cursor.execute("""
    CREATE TABLE IF NOT EXISTS skill_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        content TEXT NOT NULL,  -- SKILL.md full content
        quality_score REAL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
    );
""")

self.cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_skills (
        task_id TEXT NOT NULL,
        skill_id TEXT NOT NULL,
        PRIMARY KEY (task_id, skill_id)
    );
""")

# FTS5 技能搜索
self.cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts
    USING fts5(
        skill_id,
        name,
        description,
        content='skills',
        content_rowid='id'
    );
""")
```

---

### 2.2 任务边界检测与摘要

**Files:**
- Create: `src/skills/task_detector.py`
- Modify: `src/dag_compressor.py` — 压缩后触发任务检测

#### Step 1: 任务边界检测

借鉴 MemOS:
```
分组为用户回合 → 第一条直接分配 → 后续每条由 LLM 判断话题是否切换
（强偏向 SAME，避免过度分割）→ 2h 超时强制切分 → 结构化摘要
```

```python
# src/skills/task_detector.py
"""任务边界检测器

借鉴 MemOS Task Summarization:
  异步逐轮检测任务边界：用户回合分组 → LLM 话题判断 → 2h 超时切分
"""
import json
from typing import List, Dict, Optional
from datetime import datetime


class TaskDetector:
    TOPIC_IDLE_HOURS = 2.0  # 与 MemOS taskIdle 一致
    SKILL_MIN_CHUNKS = 6    # 与 MemOS skillMinChunks 一致

    def __init__(self, db, llm_client=None):
        self.db = db
        self.llm_client = llm_client

    def detect_tasks(self, conversation_id: str) -> List[Dict]:
        """从对话消息中检测任务边界

        算法：
        1. 按用户回合分组（连续 user 消息 → 一个回合）
        2. 第一回合直接分配为新任务
        3. 后续回合：
           a. 时间间隔 > 2h → 强制切分
           b. LLM 判断话题是否切换（偏向 SAME）
        4. 为每个任务生成结构化摘要（目标/步骤/结果）
        """
        messages = self.db.get_messages(conversation_id)
        if not messages:
            return []

        # 分组为用户回合
        turns = self._group_user_turns(messages)

        # 检测任务边界
        tasks = []
        current_task_turns = []

        for i, turn in enumerate(turns):
            if i == 0:
                current_task_turns.append(turn)
                continue

            # 2h 超时强制切分
            prev_time = self._get_turn_time(current_task_turns[-1])
            curr_time = self._get_turn_time(turn)
            if prev_time and curr_time:
                gap_hours = (curr_time - prev_time).total_seconds() / 3600.0
                if gap_hours > self.TOPIC_IDLE_HOURS:
                    if current_task_turns:
                        tasks.append(self._summarize_task(
                            current_task_turns, conversation_id
                        ))
                    current_task_turns = [turn]
                    continue

            # LLM 话题判断（偏向 SAME）
            if self.llm_client and len(current_task_turns) >= 1:
                is_same_topic = self._llm_judge_topic(
                    current_task_turns, turn
                )
                if not is_same_topic:
                    tasks.append(self._summarize_task(
                        current_task_turns, conversation_id
                    ))
                    current_task_turns = [turn]
                    continue

            current_task_turns.append(turn)

        # 最后一个任务
        if current_task_turns:
            tasks.append(self._summarize_task(
                current_task_turns, conversation_id
            ))

        return tasks

    def _group_user_turns(self, messages: List[Dict]) -> List[List[Dict]]:
        """将消息按用户回合分组"""
        turns = []
        current_turn = []

        for msg in messages:
            if msg.get('role') == 'user' and current_turn:
                # 新的用户消息开始新回合
                turns.append(current_turn)
                current_turn = [msg]
            else:
                current_turn.append(msg)

        if current_turn:
            turns.append(current_turn)

        return turns

    def _llm_judge_topic(self, prev_turns: List[List[Dict]], new_turn: List[Dict]) -> bool:
        """LLM 话题判断（强偏向 SAME）

        返回 True 表示同一话题，False 表示话题切换
        """
        prev_text = ' '.join(
            m.get('content', '')[:200]
            for turn in prev_turns[-2:]
            for m in turn
        )[:1000]
        new_text = ' '.join(m.get('content', '')[:200] for m in new_turn)[:500]

        prompt = f"""判断以下两段对话是否属于同一任务话题。

之前的对话: {prev_text}
新的对话: {new_text}

请回答 SAME 或 NEW。如果不确定，倾向于 SAME（避免过度分割）。
只回答一个词。"""

        try:
            result = self.llm_client.generate(prompt, temperature=0.0, max_tokens=10)
            return 'NEW' not in result.upper()
        except Exception:
            return True  # 失败时偏向 SAME

    def _summarize_task(self, turns: List[List[Dict]], conversation_id: str) -> Dict:
        """生成任务结构化摘要"""
        all_msgs = [m for turn in turns for m in turn]
        combined = '\n'.join(
            f"[{m.get('role','?')}]: {m.get('content','')[:300]}"
            for m in all_msgs[:30]
        )

        if self.llm_client:
            try:
                prompt = f"""从以下对话片段中提取结构化任务摘要。

返回 JSON 格式:
{{"goal": "...", "steps": ["...", "..."], "result": "..."}}

对话内容:
{combined}

只返回 JSON，不要其他文字。"""
                raw = self.llm_client.generate(prompt, temperature=0.3, max_tokens=500)
                start = raw.find('{')
                end = raw.rfind('}') + 1
                if start >= 0 and end > start:
                    return json.loads(raw[start:end])
            except Exception:
                pass

        # 降级：提取式摘要
        return {
            'goal': all_msgs[0].get('content', '')[:100] if all_msgs else '',
            'steps': [m.get('content', '')[:80] for m in all_msgs[:5]],
            'result': all_msgs[-1].get('content', '')[:100] if all_msgs else ''
        }

    def _get_turn_time(self, turn: List[Dict]) -> Optional[datetime]:
        """获取回合的时间戳"""
        for msg in turn:
            ts = msg.get('created_at') or msg.get('timestamp')
            if ts:
                try:
                    return datetime.fromisoformat(ts)
                except (ValueError, TypeError):
                    continue
        return None
```

---

### 2.3 技能生成与质量评分

**Files:**
- Create: `src/skills/evolver.py`

#### Step 1: 技能进化器

```python
# src/skills/evolver.py
"""技能进化器

借鉴 MemOS Skill Evolution:
  规则过滤 → LLM 评估（可重复/有价值）→ SKILL.md 生成/升级 → 质量评分 → 安装
"""
import json
import hashlib
from typing import List, Dict, Optional


class SkillEvolver:
    SKILL_MIN_CHUNKS = 6  # 与 MemOS skillMinChunks 一致

    def __init__(self, db, llm_client=None):
        self.db = db
        self.llm_client = llm_client

    def evaluate_and_generate(self, task: Dict, conversation_id: str,
                               owner: str = 'default') -> Optional[str]:
        """评估任务并生成技能

        流程:
        1. 规则过滤：chitchat/question 类消息跳过
        2. LLM 评估：判断是否可重复、有价值
        3. 生成 SKILL.md 内容
        4. 质量评分（0-1）
        5. 保存到数据库
        """
        # 规则过滤
        if not self._passes_rules(task):
            return None

        # LLM 评估
        if not self._llm_evaluate(task):
            return None

        # 生成 SKILL.md
        skill_md = self._generate_skill_md(task)
        if not skill_md:
            return None

        # 质量评分
        quality = self._score_quality(task, skill_md)

        # 保存
        skill_id = self._save_skill(
            task, skill_md, quality, conversation_id, owner
        )

        return skill_id

    def _passes_rules(self, task: Dict) -> bool:
        """规则过滤：跳过不适合生成技能的任务"""
        goal = task.get('goal', '').lower()
        # 过滤闲聊、简单问答
        skip_keywords = ['你好', 'hello', '谢谢', 'thank', '闲聊', '测试']
        return not any(kw in goal for kw in skip_keywords)

    def _llm_evaluate(self, task: Dict) -> bool:
        """LLM 评估：判断任务是否可重复、有价值"""
        if not self.llm_client:
            return True  # 无 LLM 时默认通过

        prompt = f"""评估以下任务是否值得提炼为可复用技能。

任务目标: {task.get('goal', '')}
步骤: {json.dumps(task.get('steps', []), ensure_ascii=False)}
结果: {task.get('result', '')}

判断标准：
1. 该任务是否可重复执行（非一次性操作）
2. 是否包含有价值的技术知识或工作流程

回答 YES 或 NO。不确定时倾向于 NO（避免低质量技能）。
只回答一个词。"""

        try:
            result = self.llm_client.generate(prompt, temperature=0.0, max_tokens=10)
            return 'YES' in result.upper()
        except Exception:
            return False

    def _generate_skill_md(self, task: Dict) -> Optional[str]:
        """生成 SKILL.md 内容

        格式借鉴 MemOS:
          步骤/警告/脚本
        """
        if self.llm_client:
            try:
                prompt = f"""基于以下任务信息，生成一个 SKILL.md 技能文件。

任务目标: {task.get('goal', '')}
步骤: {json.dumps(task.get('steps', []), ensure_ascii=False)}
结果: {task.get('result', '')}

格式要求：
# 技能名称
## 目标
一句话描述
## 步骤
1. ...
2. ...
## 警告
- ...
## 脚本（可选）
```bash
...
```

只返回 Markdown 内容。"""

                return self.llm_client.generate(
                    prompt, temperature=0.3, max_tokens=800
                )
            except Exception:
                pass

        # 降级：模板生成
        steps_md = '\n'.join(
            f"{i+1}. {s}" for i, s in enumerate(task.get('steps', []))
        )
        return f"""# {task.get('goal', '未命名技能')[:50]}

## 目标
{task.get('goal', '')}

## 步骤
{steps_md}

## 警告
- 此技能由规则模板自动生成，建议人工审核
"""

    def _score_quality(self, task: Dict, skill_md: str) -> float:
        """质量评分（0-1）

        评分维度：
        1. 步骤完整性（有步骤 = +0.3）
        2. 结果明确性（有结果 = +0.2）
        3. 内容长度（>200字 = +0.2）
        4. 有脚本（+0.15）
        5. 有警告（+0.15）
        """
        score = 0.0
        if task.get('steps') and len(task['steps']) >= 2:
            score += 0.3
        if task.get('result') and len(task['result']) > 20:
            score += 0.2
        if len(skill_md) > 200:
            score += 0.2
        if '```' in skill_md:
            score += 0.15
        if '## 警告' in skill_md or '## Warnings' in skill_md:
            score += 0.15
        return min(score, 1.0)

    def _save_skill(self, task: Dict, skill_md: str, quality: float,
                     conversation_id: str, owner: str) -> str:
        """保存技能到数据库"""
        goal = task.get('goal', 'untitled')[:50]
        skill_id = f"skill_{hashlib.sha256((owner + goal).encode()).hexdigest()[:16]}"
        now = datetime.utcnow().isoformat()

        self.db.cursor.execute("""
            INSERT OR REPLACE INTO skills
            (skill_id, name, description, owner, visibility, quality_score,
             current_version, steps, warnings, script, source_task_ids,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill_id, goal, task.get('result', ''), owner, 'private',
            quality, 1,
            json.dumps(task.get('steps', []), ensure_ascii=False),
            json.dumps([], ensure_ascii=False),
            skill_md,
            json.dumps([], ensure_ascii=False),
            now, now
        ))

        # 保存版本
        self.db.cursor.execute("""
            INSERT INTO skill_versions (skill_id, version, content, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (skill_id, 1, skill_md, quality, now))

        self.db.conn.commit()
        return skill_id
```

---

### 2.4 MCP 工具集成

**Files:**
- Modify: `mcp_server/lobster_mcp_server.py` — 新增 `lobster_skill` 工具

在 MCP Server 中注册新工具：

```python
# lobster_skill — 技能查询与安装
{
    "name": "lobster_skill",
    "description": "查询或安装技能（借鉴 MemOS skill_get/skill_install）",
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["get", "install", "list"]},
            "skill_id": {"type": "string"},
            "task_id": {"type": "string"}
        }
    }
}
```

---

### Phase 2 验收清单

- [ ] `src/skills/models.py` 创建完成
- [ ] `src/database.py` 新增 skills/skill_versions/task_skills 表
- [ ] `src/skills/task_detector.py` 创建完成，2h 超时 + LLM 话题判断
- [ ] `src/skills/evolver.py` 创建完成，规则过滤 → LLM 评估 → SKILL.md → 评分
- [ ] MCP 工具 `lobster_skill` 注册并可用
- [ ] 所有新增测试通过

### Phase 2 时间估算

- 2.1 数据模型: 1.5 小时
- 2.2 任务检测: 3 小时
- 2.3 技能进化器: 3 小时
- 2.4 MCP 集成: 1.5 小时
- 测试: 2 小时

**总计**: 约 11 小时

---

## Phase 3: 多智能体协同（Multi-Agent）

### 目标
借鉴 MemOS 的多 Agent 架构，通过 `owner` 字段实现记忆隔离、公共记忆和技能共享。

### 3.1 Owner 字段扩展

**Files:**
- Modify: `src/database.py` — 扩展 `owner` 字段到消息、摘要、笔记、技能表
- Modify: `src/incremental_compressor.py` — 初始化时设置 owner

#### Step 1: Schema 迁移

在 `src/database.py` 新增 `migrate_v50()`：

```python
def migrate_v50(self):
    """v5.0 schema 迁移：多智能体协同

    借鉴 MemOS: owner 字段隔离 Agent 记忆（格式 'agent:{agentId}'）
    检索时自动过滤为当前 Agent + public
    """
    migrations = [
        "ALTER TABLE messages ADD COLUMN owner TEXT DEFAULT 'default'",
        "ALTER TABLE summaries ADD COLUMN owner TEXT DEFAULT 'default'",
        "ALTER TABLE notes ADD COLUMN owner TEXT DEFAULT 'default'",
        # skills 表已在 Phase 2 包含 owner 字段
        "CREATE INDEX IF NOT EXISTS idx_messages_owner ON messages(owner)",
        "CREATE INDEX IF NOT EXISTS idx_summaries_owner ON summaries(owner)",
        "CREATE INDEX IF NOT EXISTS idx_notes_owner ON notes(owner)",
    ]

    for sql in migrations:
        try:
            self.cursor.execute(sql)
        except sqlite3.OperationalError:
            pass

    self.conn.commit()
```

#### Step 2: 查询自动过滤

在 `search_messages()`、`search_summaries()`、`get_active_notes()` 中添加 owner 过滤逻辑：

```python
# 搜索方法中追加 owner 过滤条件
# 借鉴 MemOS: 检索自动过滤为当前 Agent + public
AND (owner = ? OR owner = 'public')
```

新增辅助方法：

```python
def set_owner(self, owner: str):
    """设置当前数据库连接的 owner"""
    self.owner = owner

def _owner_filter(self) -> tuple:
    """返回 owner 过影的 SQL 片段和参数"""
    return "(owner = ? OR owner = 'public')", (self.owner,)
```

---

### 3.2 公共记忆

**Files:**
- Modify: `mcp_server/lobster_mcp_server.py` — 新增 `lobster_memory_write_public` 工具

#### Step 1: 公共记忆写入

```python
# lobster_memory_write_public — 写入公共记忆
{
    "name": "lobster_memory_write_public",
    "description": "写入公共记忆（owner='public'），所有 Agent 可检索",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "summary": {"type": "string"},
            "conversation_id": {"type": "string"}
        },
        "required": ["content"]
    }
}
```

实现逻辑：

```python
async def _handle_memory_write_public(self, args: Dict) -> List[Dict]:
    """写入公共记忆

    借鉴 MemOS memory_write_public:
      owner='public'，所有 Agent 均可检索
    """
    content = args['content']
    conversation_id = args.get('conversation_id', 'public')

    msg = {
        'id': f"pub_{hashlib.sha256(content.encode()).hexdigest()[:16]}",
        'conversationId': conversation_id,
        'role': 'system',
        'content': content,
        'timestamp': datetime.utcnow().isoformat(),
        'owner': 'public'  # 关键：公共记忆
    }

    self._get_db().save_message(msg)
    return [{"type": "text", "text": json.dumps({"status": "ok", "owner": "public"})}]
```

---

### 3.3 技能共享

**Files:**
- Modify: `mcp_server/lobster_mcp_server.py` — 新增 `lobster_skill_search`、`lobster_skill_publish` 工具

#### Step 1: 技能搜索（跨 Agent）

```python
# lobster_skill_search — 搜索技能（FTS5 + 向量双通道 + RRF 融合）
{
    "name": "lobster_skill_search",
    "description": "搜索技能，支持 self/public/mix 范围",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "scope": {
                "type": "string",
                "enum": ["mix", "self", "public"],
                "default": "mix"
            }
        },
        "required": ["query"]
    }
}
```

实现中 `scope` 参数的行为：

| scope | 搜索范围 |
|-------|---------|
| `self` | 仅当前 Agent 的私有技能 |
| `public` | 仅公共技能 |
| `mix` | 当前 Agent + 公共（默认） |

#### Step 2: 技能发布/取消发布

```python
# lobster_skill_publish / lobster_skill_unpublish
{
    "name": "lobster_skill_publish",
    "description": "将技能设为公开，其他 Agent 可发现",
    "inputSchema": {
        "type": "object",
        "properties": {
            "skill_id": {"type": "string"}
        },
        "required": ["skill_id"]
    }
}
```

实现：修改 `skills` 表中对应记录的 `visibility` 字段为 `public`/`private`。

---

### 3.4 命名空间隔离增强

**Files:**
- Modify: `src/database.py` — `search_messages()`、`search_summaries()` 增强 owner + namespace 双过滤

在现有 `namespace` 过滤基础上，叠加 `owner` 过滤：

```python
# 现有: WHERE c.namespace = ?
# 增强为: WHERE c.namespace = ? AND (m.owner = ? OR m.owner = 'public')
```

---

### Phase 3 验收清单

- [ ] `database.py` 新增 `migrate_v50()`，owner 字段扩展到 messages/summaries/notes
- [ ] 所有搜索方法支持 owner + public 双过滤
- [ ] `lobster_memory_write_public` 工具可用
- [ ] `lobster_skill_search` 支持 self/public/mix 范围
- [ ] `lobster_skill_publish`/`lobster_skill_unpublish` 工具可用
- [ ] 多 Agent 场景下记忆隔离验证通过

### Phase 3 时间估算

- 3.1 Owner 扩展: 2 小时
- 3.2 公共记忆: 1.5 小时
- 3.3 技能共享: 2 小时
- 3.4 隔离增强: 1.5 小时
- 测试: 2 小时

**总计**: 约 9 小时

---

## Phase 4: 工程化（Engineering）

### 目标
添加 Viewer Web UI、异步队列和 OpenClaw 原生记忆迁移。

### 4.1 Viewer Web UI

**Files:**
- Create: `src/viewer/__init__.py`
- Create: `src/viewer/server.py`
- Create: `src/viewer/templates/` — HTML 模板

#### Step 1: 最小化 Viewer 服务

借鉴 MemOS Viewer:
- 7 页: 记忆/任务/技能/分析/日志/导入/设置
- 仅 127.0.0.1，密码保护

```python
# src/viewer/server.py
"""LobsterPress Memory Viewer

借鉴 MemOS Viewer 架构：
  7 页: memories, tasks, skills, analytics, logs, import, settings
  安全: 仅 127.0.0.1，密码 SHA-256，HttpOnly Cookie
"""
import hashlib
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class ViewerHandler(BaseHTTPRequestHandler):
    """Viewer HTTP Handler"""

    def do_GET(self):
        path = urlparse(self.path).path

        routes = {
            '/': self._serve_viewer_html,
            '/api/memories': self._api_memories,
            '/api/tasks': self._api_tasks,
            '/api/skills': self._api_skills,
            '/api/stats': self._api_stats,
            '/api/config': self._api_config,
        }

        handler = routes.get(path)
        if handler:
            handler()
        else:
            self.send_error(404)

    def _api_memories(self):
        """记忆列表（分页、过滤）"""
        # 借鉴 MemOS: GET /api/memories
        params = parse_qs(urlparse(self.path).query)
        page = int(params.get('page', [1])[0])
        limit = int(params.get('limit', [20])[0])
        # 查询数据库，返回 JSON
        ...

    def _api_stats(self):
        """统计与分析"""
        # 消息数、摘要数、压缩比、时间分布
        ...


def start_viewer(db, port: int = 18799, password: str = None):
    """启动 Viewer 服务"""
    server = HTTPServer(('127.0.0.1', port), ViewerHandler)
    print(f"🦞 LobsterPress Viewer: http://127.0.0.1:{port}")
    server.serve_forever()
```

---

### 4.2 异步队列

**Files:**
- Create: `src/async_queue/__init__.py`
- Create: `src/async_queue/worker.py`

#### Step 1: 异步任务队列

借鉴 MemOS Ingest 异步队列：
```
语义分片 → LLM 摘要 → 向量化 → 智能去重 → 存储
```

```python
# src/async_queue/worker.py
"""异步任务队列

借鉴 MemOS:
  异步队列：语义分片 → LLM 摘要 → Embed → 智能去重 → 存储
  任务检测、技能进化也走此队列
"""
import asyncio
import threading
from typing import Callable, Dict, Any
from collections import deque


class AsyncWorker:
    """简单异步工作队列（单线程，异步 I/O）"""

    def __init__(self, db, embedder=None, llm_client=None):
        self.db = db
        self.embedder = embedder
        self.llm_client = llm_client
        self._queue = deque()
        self._running = False
        self._thread = None

    def start(self):
        """启动后台工作线程"""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止工作线程"""
        self._running = False

    def enqueue(self, task_type: str, payload: Dict[str, Any]):
        """入队任务"""
        self._queue.append({
            'type': task_type,
            'payload': payload
        })

    def _run_loop(self):
        while self._running:
            if not self._queue:
                import time
                time.sleep(1.0)
                continue

            task = self._queue.popleft()
            try:
                self._process(task)
            except Exception as e:
                print(f"⚠️ Async task failed: {e}")

    def _process(self, task: Dict):
        """处理单个任务"""
        task_type = task['type']

        if task_type == 'embed':
            self._process_embed(task['payload'])
        elif task_type == 'task_detect':
            self._process_task_detect(task['payload'])
        elif task_type == 'skill_eval':
            self._process_skill_eval(task['payload'])

    def _process_embed(self, payload: Dict):
        """异步嵌入：向量化消息/摘要"""
        target_type = payload['target_type']
        target_id = payload['target_id']
        content = payload['content']

        if self.embedder and self.embedder.is_available():
            vec = self.embedder.embed(content)
            self.db.save_embedding(target_type, target_id, vec)

    def _process_task_detect(self, payload: Dict):
        """异步任务检测"""
        # 委托给 TaskDetector（Phase 2）
        ...

    def _process_skill_eval(self, payload: Dict):
        """异步技能评估"""
        # 委托给 SkillEvolver（Phase 2）
        ...
```

---

### 4.3 OpenClaw 原生记忆迁移

**Files:**
- Create: `src/migration/__init__.py`
- Create: `src/migration/importer.py`

#### Step 1: 记忆导入器

借鉴 MemOS 🦐 记忆迁移：
- 一键导入 OpenClaw 原生 SQLite 数据
- 智能去重、断点续传、实时进度

```python
# src/migration/importer.py
"""OpenClaw 原生记忆导入器

借鉴 MemOS 🦐 记忆迁移：
  一键导入 · 智能去重 · 断点续传 · 🦐 标识导入来源
"""
import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional


class MemoryImporter:
    """OpenClaw 原生记忆导入"""

    OPENCLAW_DB_PATH = Path.home() / ".openclaw" / "agents" / "main" / "sessions"

    def __init__(self, db):
        self.db = db
        self._progress = {'stored': 0, 'skipped': 0, 'merged': 0, 'errors': 0}
        self._checkpoint_file = None

    def scan(self) -> Dict:
        """扫描 OpenClaw 原生记忆"""
        stats = {'files': 0, 'sessions': 0, 'messages': 0}

        for db_path in self.OPENCLAW_DB_PATH.glob("*.db"):
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM messages")
                count = cursor.fetchone()[0]
                stats['files'] += 1
                stats['messages'] += count
                conn.close()
            except Exception:
                continue

        return stats

    def import_memories(self, on_progress=None) -> Dict:
        """导入记忆（支持断点续传）

        Args:
            on_progress: 进度回调 fn(stored, skipped, merged, errors)

        Returns:
            导入统计
        """
        for db_path in self.OPENCLAW_DB_PATH.glob("*.db"):
            try:
                self._import_session_db(db_path)
            except Exception as e:
                self._progress['errors'] += 1

            if on_progress:
                on_progress(self._progress)

        return self._progress

    def _import_session_db(self, db_path: Path):
        """导入单个会话数据库"""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM messages ORDER BY seq ASC")
            rows = cursor.fetchall()

            for row in rows:
                msg = dict(row)
                content = msg.get('content', '')

                # 去重：按 content hash 检查是否已存在
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                self.db.cursor.execute(
                    "SELECT id FROM messages WHERE metadata LIKE ?",
                    (f'%{content_hash}%',)
                )
                if self.db.cursor.fetchone():
                    self._progress['skipped'] += 1
                    continue

                # 导入（标记 🦐 来源）
                msg['content'] = f"🦐 {content}"  # MemOS 风格来源标识
                self.db.save_message(msg)
                self._progress['stored'] += 1

        finally:
            conn.close()
```

---

### 4.4 MCP 工具注册

**Files:**
- Modify: `mcp_server/lobster_mcp_server.py` — 新增 Phase 4 工具

```python
# Phase 4 新增工具
{
    "name": "lobster_viewer",
    "description": "打开 Memory Viewer Web UI",
    "inputSchema": {"type": "object", "properties": {}}
},
{
    "name": "lobster_import",
    "description": "导入 OpenClaw 原生记忆（🦐 标识）",
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {"enum": ["scan", "start", "stop"]},
        }
    }
}
```

---

### Phase 4 验收清单

- [ ] `src/viewer/server.py` 创建完成，127.0.0.1 绑定 + 密码保护
- [ ] Viewer API 路由（/api/memories, /api/stats 等）工作正常
- [ ] `src/async_queue/worker.py` 创建完成，embed/task_detect/skill_eval 三类任务
- [ ] `src/migration/importer.py` 创建完成，扫描/导入/断点续传
- [ ] MCP 工具 `lobster_viewer` 和 `lobster_import` 注册
- [ ] 所有新增测试通过

### Phase 4 时间估算

- 4.1 Viewer UI: 6 小时
- 4.2 异步队列: 3 小时
- 4.3 记忆迁移: 3 小时
- 4.4 MCP 集成: 1.5 小时
- 测试: 2 小时

**总计**: 约 15.5 小时

---

## 总览

| Phase | 内容 | 文件数 | 预估工时 | 前置依赖 |
|-------|------|--------|---------|----------|
| Phase 1 | 核心智能 | 4 新增 + 2 修改 | 11.5h | 无 |
| Phase 2 | 技能进化 | 4 新增 + 1 修改 | 11h | Phase 1 |
| Phase 3 | 多智能体 | 0 新增 + 3 修改 | 9h | Phase 2 |
| Phase 4 | 工程化 | 5 新增 + 1 修改 | 15.5h | Phase 1, 2 |

**总工时**: 约 47 小时

### 新增文件清单

```
src/
├── vector/
│   ├── __init__.py
│   ├── embedder.py           # OpenAI Compatible + numpy 离线嵌入
│   └── retriever.py          # RRF/MMR/Decay 混合检索
├── skills/
│   ├── __init__.py
│   ├── models.py             # Skill/TaskSummary 数据模型
│   ├── task_detector.py      # 任务边界检测（2h 超时 + LLM 话题判断）
│   └── evolver.py            # 技能进化器（规则→评估→SKILL.md→评分）
├── async_queue/
│   ├── __init__.py
│   └── worker.py             # 异步任务队列
├── viewer/
│   ├── __init__.py
│   └── server.py             # Viewer Web UI
└── migration/
    ├── __init__.py
    └── importer.py           # OpenClaw 原生记忆导入
```

### 修改文件清单

```
src/database.py               # embeddings/skills 表, save_embedding(), vector_search(), owner 字段
src/dag_compressor.py          # 压缩后触发任务检测
src/incremental_compressor.py  # owner 设置, 异步队列集成
src/llm_client.py              # FallbackLLMClient 三级降级链
mcp_server/lobster_mcp_server.py  # 新工具注册 (skill, search, publish, viewer, import)
```

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 向量维度不匹配（不同嵌入模型） | 统一 1024 维，`NumpyOfflineEmbedder` 降级 |
| 大库向量搜索性能 | 可设 `vectorSearchMaxChunks=200000` 限制扫描范围 |
| LLM 降级链全部失败 | 最终降级为规则方法（提取式摘要/模板技能） |
| 多 Agent owner 过滤遗漏 | 全局 `_owner_filter()` 方法统一管理 |
| Viewer 安全暴露 | 强制 127.0.0.1，SHA-256 密码，HttpOnly Cookie |

---

## 关联

- 灵感来源: [MemOS OpenClaw Plugin](https://memos-claw.openmem.net/docs/)
- 参考: `arXiv:2502.15957` — R³Mem: Bridging Memory Retention and Retrieval
- 参考: `arXiv:2004.11327` — Adaptive Forgetting Curves for Spaced Repetition
