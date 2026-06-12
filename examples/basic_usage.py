#!/usr/bin/env python3
"""Basic LobsterPress usage — Python API."""

from src.database import LobsterDatabase
from src.incremental_compressor import IncrementalCompressor

db = LobsterDatabase(namespace="demo")

# Ingest messages
db.save_message({"id": "msg-1", "role": "user", "content": "Hello!", "conversationId": "conv-1"})
db.save_message({"id": "msg-2", "role": "assistant", "content": "Hi! How can I help?", "conversationId": "conv-1"})

# Search
results = db.search_messages("hello", namespace="demo")
print(f"Found {len(results)} messages")

# Compress (requires LLM provider or falls back to extractive)
compressor = IncrementalCompressor(db, conversation_id="conv-1")
summary = compressor.compress()
print(f"Compressed: {summary}")
