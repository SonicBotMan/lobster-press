#!/usr/bin/env python3
"""Basic LobsterPress usage — Python API.

v5.1.1 (audit P2): 原示例调用了不存在的参数（search_messages(namespace=...),
IncrementalCompressor(conversation_id=...)），首跑即 TypeError。已改为可运行版本。
"""

from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor

db = LobsterDatabase(namespace="demo")

# Ingest messages
db.save_message({"id": "msg-1", "role": "user", "content": "Hello!", "conversationId": "conv-1"})
db.save_message({"id": "msg-2", "role": "assistant", "content": "Hi! How can I help?", "conversationId": "conv-1"})

# Search (FTS5 trigram: >=3 chars uses full-text index, shorter queries fall back to LIKE)
results = db.search_messages("hello", conversation_id="conv-1")
print(f"Found {len(results)} messages")

# Compress (requires LLM provider or falls back to extractive)
compressor = IncrementalCompressor(db)
summary = compressor.compress("conv-1")
print(f"Compressed: {summary}")

db.close()
