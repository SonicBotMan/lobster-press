# -*- coding: utf-8 -*-
"""
Shared mathematical utility functions.

Eliminates duplicate cosine similarity implementations across modules.
"""

import math
from collections import Counter
from typing import List, Union


def cosine_similarity(
    a: Union[List[str], Counter],
    b: Union[List[str], Counter],
) -> float:
    """Compute cosine similarity between two token vectors.

    Accepts either raw token lists (converted to TF Counter internally)
    or pre-computed Counter objects.

    Args:
        a: Token list or Counter for vector A.
        b: Token list or Counter for vector B.

    Returns:
        Cosine similarity in [0.0, 1.0].
    """
    if not a or not b:
        return 0.0

    tf_a = Counter(a) if isinstance(a, list) else a
    tf_b = Counter(b) if isinstance(b, list) else b

    all_terms = set(tf_a.keys()) | set(tf_b.keys())
    dot_product = sum(tf_a.get(t, 0) * tf_b.get(t, 0) for t in all_terms)

    norm_a = math.sqrt(sum(v ** 2 for v in tf_a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in tf_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)
