"""强制免责声明中间件 — 在所有 AI 回答末尾拼接法律声明"""

DISCLAIMER = (
    "\n\n---\n"
    "*以上内容由 AI 生成，仅供参考，不构成法律意见。"
    "如涉及重大权益，请咨询执业律师。*"
)


async def add_disclaimer(answer: str) -> str:
    """Append disclaimer if not already present."""
    if DISCLAIMER not in answer:
        return answer + DISCLAIMER
    return answer
