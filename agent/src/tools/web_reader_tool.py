"""Web reader tool: fetch a URL as Markdown text via the Jina Reader API."""

from __future__ import annotations

import json

import requests

from src.agent.tools import BaseTool

_JINA_PREFIX = "https://r.jina.ai/"
_TIMEOUT = 30
_MAX_LENGTH = 8000


def read_url(url: str) -> str:
    """Fetch web page content via the Jina Reader API.

    Args:
        url: Target URL.

    Returns:
        JSON-formatted result containing title, content, and url.
    """
    try:
        resp = requests.get(
            f"{_JINA_PREFIX}{url}",
            headers={"Accept": "text/markdown"},
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return json.dumps({
                "status": "error",
                "error": f"Jina Reader returned {resp.status_code}: {resp.text[:500]}",
            }, ensure_ascii=False)

        text = resp.text
        title = ""
        for line in text.split("\n"):
            if line.startswith("Title:"):
                title = line[6:].strip()
                break

        if len(text) > _MAX_LENGTH:
            text = text[:_MAX_LENGTH] + f"\n\n... (truncated, total {len(resp.text)} chars)"

        return json.dumps({
            "status": "ok",
            "title": title,
            "url": url,
            "content": text,
            "length": len(resp.text),
        }, ensure_ascii=False)

    except requests.Timeout:
        return json.dumps({"status": "error", "error": f"Request timed out ({_TIMEOUT}s)"}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)


class WebReaderTool(BaseTool):
    """Web reader tool."""

    name = "read_url"
    description = "Fetch web page content: provide a URL and receive the page as Markdown text. Useful for reading docs, articles, API references, etc."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL of the web page to read"},
        },
        "required": ["url"],
    }
    repeatable = True

    def execute(self, **kwargs) -> str:
        """Fetch web page."""
        return read_url(kwargs["url"])
