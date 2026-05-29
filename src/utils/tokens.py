# -*- coding: utf-8 -*-
"""
Shared token estimation functions.

Eliminates duplicate token estimation implementations across modules.
English: ~4 chars per token. Chinese: ~1.5 chars per token.
"""


def estimate_tokens(text: str) -> int:
    """Estimate token count for mixed Chinese/English text.

    Uses the same formula as tiktoken's rough approximation:
    - English: 4 characters ≈ 1 token
    - Chinese: 1.5 characters ≈ 1 token

    Args:
        text: Input text.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0
    chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    english = len(text) - chinese
    return int(english / 4 + chinese / 1.5)
