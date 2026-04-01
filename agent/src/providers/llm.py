"""LLM factory and JSON extraction helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # type: ignore

AGENT_DIR = Path(__file__).resolve().parents[2]

# .env search order: ~/.vibe-trading/.env → agent/.env → $CWD/.env
_ENV_CANDIDATES = [
    Path.home() / ".vibe-trading" / ".env",
    AGENT_DIR / ".env",
    Path.cwd() / ".env",
]

_dotenv_loaded: bool = False


def _load_env_file(path: Path) -> None:
    """Load a single .env file into os.environ (setdefault, no override)."""
    if load_dotenv is not None:
        load_dotenv(dotenv_path=path, override=False)
    else:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def _ensure_dotenv() -> None:
    """Load `.env` from the first found candidate path."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    for candidate in _ENV_CANDIDATES:
        if candidate.exists():
            _load_env_file(candidate)
            break
    _dotenv_loaded = True


def _sync_provider_env() -> None:
    """Map provider-specific env vars to OPENAI_* for ChatOpenAI."""
    _ensure_dotenv()
    provider = os.getenv("LANGCHAIN_PROVIDER", "openai").lower()
    provider_env = {
        "openai": ("OPENAI_API_KEY", "OPENAI_API_BASE"),
        "openrouter": ("OPENAI_API_KEY", "OPENAI_API_BASE"),
        "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
        "qwen": ("QWEN_API_KEY", "QWEN_BASE_URL"),
    }
    key_env, base_env = provider_env.get(provider, provider_env["openai"])
    api_key = os.getenv(key_env) or os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv(base_env, "") or os.getenv("OPENAI_API_BASE", "") or os.getenv("OPENAI_BASE_URL", "")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["OPENAI_API_BASE"] = base_url
        os.environ.setdefault("OPENAI_BASE_URL", base_url)


def build_llm(*, model_name: Optional[str] = None, callbacks: Any = None) -> Any:
    """Construct a ChatOpenAI instance.

    Args:
        model_name: Model name; defaults to LANGCHAIN_MODEL_NAME.
        callbacks: Optional LangChain callbacks.

    Returns:
        ChatOpenAI instance.

    Raises:
        RuntimeError: If langchain-openai is missing or LANGCHAIN_MODEL_NAME is unset.
    """
    if ChatOpenAI is None:
        raise RuntimeError("langchain-openai is not installed")
    _sync_provider_env()
    name = model_name or os.getenv("LANGCHAIN_MODEL_NAME", "").strip()
    if not name:
        raise RuntimeError("LANGCHAIN_MODEL_NAME is not set")
    temperature = float(os.getenv("LANGCHAIN_TEMPERATURE", "0.0"))
    timeout = int(os.getenv("TIMEOUT_SECONDS", "600"))
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    return ChatOpenAI(
        model=name,
        temperature=temperature,
        timeout=timeout,
        max_retries=max_retries,
        callbacks=callbacks,
    )


def _extract_balanced_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract the outermost JSON object from text using bracket balancing.

    Args:
        text: Text that may embed a JSON object.

    Returns:
        Parsed dict, or None on failure.
    """
    start = -1
    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = -1
    return None
