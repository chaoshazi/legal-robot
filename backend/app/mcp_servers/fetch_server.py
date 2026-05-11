"""MCP server — fetch web pages for the legal consultation LLM agent.

Fetches URLs and returns content as markdown-style text.
Useful for looking up legal documents, news, or any web content.

Run as a standalone process (stdio transport):
    python -m app.mcp_servers.fetch_server
"""

import json
import os
import sys
from typing import Any

_backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import httpx
from mcp.server.fastmcp import FastMCP

server = FastMCP(
    name="fetch-server",
    instructions="抓取网页内容并返回 markdown 格式文本，适用于查询法律条文、新闻资讯等在线信息。",
)


@server.tool()
async def fetch_url(url: str) -> str:
    """抓取指定 URL 的网页内容并返回 markdown 格式文本。

    适用于：
    - 查询法律法规（如 flk.npc.gov.cn、gov.cn 等政府网站）
    - 获取新闻资讯
    - 搜索法律相关内容

    Args:
        url: 完整的网页 URL，必须以 http:// 或 https:// 开头。
    """
    if not url.startswith(("http://", "https://")):
        return json.dumps({"error": "URL 必须以 http:// 或 https:// 开头"}, ensure_ascii=False)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

        content_type = resp.headers.get("content-type", "")
        text = resp.text

        # Try to extract meaningful text
        import re

        # Remove scripts and styles
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.DOTALL | re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""

        # Convert to text
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</(div|h[1-6]|li|tr|th|td|blockquote|pre)>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&quot;", '"', text)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n")]
        lines = [line for line in lines if line]
        content = "\n".join(lines)

        # Truncate if too long
        max_len = 10000
        if len(content) > max_len:
            content = content[:max_len] + "\n\n...（内容过长，已截断）"

        result = f"# {title}\n\nURL: {url}\n\n{content}" if title else f"URL: {url}\n\n{content}"
        return result

    except httpx.TimeoutException:
        return json.dumps({"error": "请求超时（15s），目标网站响应过慢"}, ensure_ascii=False)
    except httpx.RequestError as e:
        return json.dumps({"error": f"网络请求失败: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"处理失败: {e}"}, ensure_ascii=False)


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
