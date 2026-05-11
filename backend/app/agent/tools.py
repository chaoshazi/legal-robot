"""Legal domain tools for LLM function calling.

Each tool is a LangChain @tool-decorated function.
The LLM decides when to call these tools via function calling.
"""

import ast
import operator
from datetime import datetime, timezone

import httpx
from langchain_core.tools import tool

from app.agent.sandbox import async_run_code
from app.core.config import get_settings
from app.rag.retriever import async_get_retriever


# ── Knowledge base ───────────────────────────────────────────────────────


@tool
async def search_knowledge_base(query: str) -> str:
    """搜索法律知识库，根据用户问题查找相关法律法规、条文规定和司法案例。
    当用户询问具体法律规定、法条内容、权利义务或司法案例时调用此工具。"""
    try:
        from app.agent.config import get_agent_config
        active_ids = get_agent_config().get("active_knowledge_ids") or None
        retriever = await async_get_retriever()
        docs = await retriever.ainvoke(query, doc_ids=active_ids)
        if not docs:
            return "【检索结果为空】知识库中未找到与问题相关的法律法规或条文。你无权依据自身知识作答，必须如实告知用户无法从知识库中找到答案。"
        parts = []
        for i, d in enumerate(docs, 1):
            source = d.metadata.get("source", "法律知识库")
            parts.append(f"[{i}] 来自《{source}》\n{d.page_content}")
        return "\n\n".join(parts)
    except Exception as e:
        return f"[检索服务暂时不可用: {e}]"


# ── Compensation calculator ──────────────────────────────────────────────


@tool
def calculate_compensation(injury_type: str, monthly_salary: float, work_years: int) -> str:
    """根据中国劳动法计算工伤赔偿金额。当用户询问工伤赔偿、补偿金金额时调用此工具。

    Args:
        injury_type: 受伤类型描述
        monthly_salary: 月均工资（元）
        work_years: 工作年限（年）
    """
    base = monthly_salary * work_years
    return f"针对'{injury_type}'的预估赔偿: {base * 1.5:.2f} 元（仅供参考，以实际伤残鉴定为准）"


# ── Web search ───────────────────────────────────────────────────────────


@tool
async def web_search(query: str) -> str:
    """搜索互联网获取最新信息。当用户询问实时新闻、最新政策、近期事件或需要联网查证的信息时调用此工具。

    Args:
        query: 搜索关键词
    """
    settings = get_settings()
    provider = settings.web_search_provider

    if provider == "custom" and settings.web_search_api_base:
        return await _custom_web_search(query, settings)
    return await _duckduckgo_search(query)


async def _duckduckgo_search(query: str) -> str:
    """Search via DuckDuckGo HTML API (no API key required)."""
    url = "https://html.duckduckgo.com/html/"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(url, data={"q": query})
            resp.raise_for_status()
            text = resp.text
    except Exception as e:
        return f"[联网搜索失败: {e}]"

    import re

    results: list[str] = []
    for match in re.finditer(
        r'<a[^>]+class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        text,
        re.DOTALL,
    ):
        link = match.group(1)
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if title:
            results.append(f"{title}\n  {link}")
        if len(results) >= 5:
            break

    if not results:
        return "【搜索结果为空】未找到相关结果，请尝试使用不同的搜索关键词。"

    return "互联网搜索结果（仅供参考，请以权威渠道为准）：\n" + "\n\n".join(
        f"{i+1}. {r}" for i, r in enumerate(results)
    )


async def _custom_web_search(query: str, settings) -> str:
    """Search via a configurable custom search API."""
    headers = {}
    if settings.web_search_api_key:
        headers["Authorization"] = f"Bearer {settings.web_search_api_key}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                settings.web_search_api_base,
                params={"q": query},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return f"[自定义搜索失败: {e}]"

    items = []
    if isinstance(data, dict):
        items = data.get("results", data.get("items", []))
    else:
        items = data

    if not items:
        return "【搜索结果为空】未找到相关结果。"

    parts = []
    for i, item in enumerate(items[:5], 1):
        title = item.get("title", item.get("name", ""))
        link = item.get("link", item.get("url", ""))
        snippet = item.get("snippet", item.get("content", ""))
        parts.append(f"{i}. {title}\n  {link}\n  {snippet}")

    return "互联网搜索结果（仅供参考，请以权威渠道为准）：\n" + "\n\n".join(parts)


# ── Time / Date ──────────────────────────────────────────────────────────


_TIMEZONE_ALIASES: dict[str, str] = {
    "北京时间": "Asia/Shanghai",
    "中国": "Asia/Shanghai",
    "上海": "Asia/Shanghai",
    "北京": "Asia/Shanghai",
    "香港": "Asia/Hong_Kong",
    "东京": "Asia/Tokyo",
    "纽约": "America/New_York",
    "伦敦": "Europe/London",
    "巴黎": "Europe/Paris",
    "新加坡": "Asia/Singapore",
    "UTC": "UTC",
    "utc": "UTC",
}


@tool
def get_current_datetime(timezone: str = "Asia/Shanghai") -> str:
    """获取指定时区的当前日期和时间。当用户询问当前日期、时间、星期几、或需要计算时间期限时调用此工具。

    Args:
        timezone: 时区名称（如 Asia/Shanghai、America/New_York）或中文别名（如 北京时间、纽约）
    """
    tz_name = _TIMEZONE_ALIASES.get(timezone, timezone)
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(tz_name)
    except (KeyError, TypeError):
        return f"不支持的时区: {timezone}，支持的时区如 Asia/Shanghai、America/New_York"

    now = datetime.now(tz)
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]

    return (
        f"当前时间（{tz_name}）\n"
        f"日期: {now.strftime('%Y-%m-%d')}\n"
        f"时间: {now.strftime('%H:%M:%S')}\n"
        f"星期: {weekday}\n"
        f"ISO: {now.isoformat()}"
    )


# ── Calculator ───────────────────────────────────────────────────────────


_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


@tool
def calculate(expression: str) -> str:
    """计算数学表达式。当用户需要进行精确的数值计算、统计或公式运算时调用此工具。

    Args:
        expression: 数学表达式，支持 + - * / // % ** 和括号，如 "(12 + 34) * 5 / 2"
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree.body)
        return f"{expression} = {result}"
    except SyntaxError:
        return f"表达式语法错误: {expression}"
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        return f"计算错误: {e}"


def _safe_eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"不支持的常量类型: {type(node.value).__name__}")
    if isinstance(node, ast.UnaryOp):
        op = _ALLOWED_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        return op(_safe_eval(node.operand))
    if isinstance(node, ast.BinOp):
        op = _ALLOWED_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        return op(_safe_eval(node.left), _safe_eval(node.right))
    raise ValueError(f"不支持的表达式: {type(node).__name__}")


# ── Code interpreter ──────────────────────────────────────────────────────


@tool
async def python_executor(code: str) -> str:
    """在沙箱环境中执行 Python 代码，用于处理超出四则运算范围的复杂计算、法律条款中的精确日期计算、多条件对比分析以及数据格式化输出。

    当你需要以下操作时调用此工具：
    - 复杂的数学计算（如含税率的赔偿计算、等额本息/等额本金分期计算）
    - 法定期间计算（诉讼时效、上诉期限等需要精确到日的计算）
    - 数据转换（将非结构化文本转为表格、JSON、CSV 等结构化格式）
    - 对多条法律条文进行程序化处理（统计、筛选、对比）
    - 需要循环、条件判断或多步骤逻辑的数值验证

    Args:
        code: 要执行的 Python 代码。代码中必须使用 print() 输出结果，print 的内容将被返回。
              可用模块: math, datetime, json, csv, re, collections, itertools, statistics, decimal, random, string, textwrap, typing, functools, operator, difflib, hashlib, uuid, fractions, numbers, time, dataclasses, enum, bisect, heapq, copy
    """
    return await async_run_code(code)
