"""敏感词过滤中间件"""

import re

# 基础敏感词列表，涵盖违法、骚扰、诈骗等类别
SENSITIVE_WORDS: list[str] = [
    # 违法内容
    "毒品", "海洛因", "冰毒", "大麻", "制毒", "吸毒",
    "赌博", "赌场", "赌球", "赌资", "赌博网站",
    "枪支", "弹药", "管制刀具", "仿真枪",
    "爆炸物", "炸药", "雷管",
    "卖淫", "嫖娼", "招嫖",
    "走私", "偷渡",
    "洗钱", "非法集资", "高利贷",
    "暴力催收", "套路贷",
    "诈骗", "电信诈骗", "网络诈骗", "刷单",
    "传销", "非法传销",
    "黑客", "木马", "病毒", "入侵系统",
    "钓鱼网站", "伪基站",
    "窃听", "偷拍", "针孔摄像头",
    "伪造证件", "假币", "假发票",
    "代办信用卡套现",
    "刷单", "刷信誉",
    "恶意软件", "勒索病毒",
    "暗网",
    # 暴力血腥
    "杀人", "自杀教程", "自残",
    # 政治敏感
    "分裂国家", "颠覆国家",
    # 色情
    "色情", "裸聊", "裸照", "成人视频", "色情直播",
]

# 编译正则用于匹配变体（如带空格的敏感词）
_SENSITIVE_PATTERNS = [re.compile(re.escape(w), re.IGNORECASE) for w in SENSITIVE_WORDS]


def contains_sensitive(text: str) -> bool:
    """Check if text contains any sensitive keywords."""
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def filter_sensitive(text: str, replacement: str = "***") -> str:
    """Replace sensitive words with replacement string."""
    result = text
    for pattern in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result
