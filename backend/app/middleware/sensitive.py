"""敏感词过滤中间件"""

import re

# 基础敏感词列表，生产环境建议导入外部词库
SENSITIVE_WORDS: list[str] = []


def contains_sensitive(text: str) -> bool:
    """Check if text contains any sensitive keywords."""
    for word in SENSITIVE_WORDS:
        if word in text:
            return True
    return False


def filter_sensitive(text: str, replacement: str = "***") -> str:
    """Replace sensitive words with replacement string."""
    for word in SENSITIVE_WORDS:
        text = text.replace(word, replacement)
    return text
