"""LLM factory and JSON extraction helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # type: ignore


# Provider-specific reasoning field variants, in priority order.
# All normalize to the canonical key additional_kwargs["reasoning_content"].
#   * Moonshot / DeepSeek official API → "reasoning_content"
#   * OpenRouter relay (all thinking models) → "reasoning"
_REASONING_FIELDS: tuple[str, ...] = ("reasoning_content", "reasoning")


def _preserve(src: Mapping[str, Any], target_msg: Any) -> None:
    """Copy provider reasoning field from src into target_msg.additional_kwargs.

    Src is a response message dict (non-streaming) or stream delta dict.
    The first non-empty variant in _REASONING_FIELDS wins; all write to the
    same canonical key so downstream reads one place.
    """
    for field in _REASONING_FIELDS:
        value = src.get(field)
        if value:
            target_msg.additional_kwargs["reasoning_content"] = value
            return


if ChatOpenAI is not None:
    class ChatOpenAIWithReasoning(ChatOpenAI):  # type: ignore[misc,valid-type]
        """ChatOpenAI that preserves provider-specific reasoning fields.

        langchain-openai 0.3.x drops non-standard fields (reasoning_content
        from Moonshot K2.5, DeepSeek reasoner, Qwen thinking) in both
        response paths:
          * _convert_dict_to_message — invoke / ainvoke (non-streaming)
          * _convert_delta_to_message_chunk — stream / astream

        This subclass hooks both so downstream code always reads one place:
        msg.additional_kwargs["reasoning_content"]. For streaming, per-delta
        writes are accumulated by AIMessageChunk.__add__ via merge_dicts.
        """

        def _create_chat_result(self, response, generation_info=None):  # type: ignore[override]
            result = super()._create_chat_result(response, generation_info)
            raw = response if isinstance(response, dict) else response.model_dump()
            for gen, choice in zip(result.generations, raw["choices"]):
                _preserve(choice["message"], gen.message)
            return result

        def _convert_chunk_to_generation_chunk(  # type: ignore[override]
            self,
            chunk: dict,
            default_chunk_class: type,
            base_generation_info: Optional[dict],
        ):
            gen_chunk = super()._convert_chunk_to_generation_chunk(
                chunk, default_chunk_class, base_generation_info
            )
            if gen_chunk is None:
                return None
            choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices")
            if not choices:
                return gen_chunk
            _preserve(choices[0]["delta"], gen_chunk.message)
            return gen_chunk
else:
    ChatOpenAIWithReasoning = None  # type: ignore

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
    """Map provider-specific env vars to OPENAI_* for ChatOpenAI.

    Each entry: provider_name -> (api_key_env, base_url_env).
    All base URLs must be set explicitly in .env — no hardcoded defaults.
    api_key_env=None means no key required (e.g. Ollama local).
    """
    _ensure_dotenv()
    provider = os.getenv("LANGCHAIN_PROVIDER", "openai").lower()

    # (api_key_env, base_url_env)
    _PROVIDER_MAP: dict[str, tuple[str | None, str]] = {
        "openai":     ("OPENAI_API_KEY",     "OPENAI_BASE_URL"),
        "openrouter": ("OPENROUTER_API_KEY",  "OPENROUTER_BASE_URL"),
        "deepseek":   ("DEEPSEEK_API_KEY",    "DEEPSEEK_BASE_URL"),
        "gemini":     ("GEMINI_API_KEY",      "GEMINI_BASE_URL"),
        "groq":       ("GROQ_API_KEY",        "GROQ_BASE_URL"),
        "dashscope":  ("DASHSCOPE_API_KEY",   "DASHSCOPE_BASE_URL"),
        "qwen":       ("DASHSCOPE_API_KEY",   "DASHSCOPE_BASE_URL"),
        "zhipu":      ("ZHIPU_API_KEY",       "ZHIPU_BASE_URL"),
        "moonshot":   ("MOONSHOT_API_KEY",    "MOONSHOT_BASE_URL"),
        "minimax":    ("MINIMAX_API_KEY",     "MINIMAX_BASE_URL"),
        "mimo":       ("MIMO_API_KEY",        "MIMO_BASE_URL"),
        "zai":        ("ZAI_API_KEY",         "ZAI_BASE_URL"),
        "ollama":     (None,                  "OLLAMA_BASE_URL"),
    }

    spec = _PROVIDER_MAP.get(provider, _PROVIDER_MAP["openai"])
    key_env, base_env = spec

    # Resolve API key: provider-specific env → OPENAI_API_KEY fallback
    if key_env is not None:
        api_key = os.getenv(key_env, "") or os.getenv("OPENAI_API_KEY", "")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "") or "ollama"

    # Resolve base URL: provider-specific env → OPENAI_BASE_URL fallback
    base_url = os.getenv(base_env, "") or os.getenv("OPENAI_BASE_URL", "") or os.getenv("OPENAI_API_BASE", "")

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
    # MiniMax requires temperature in (0.0, 1.0] — clamp to 0.01 when the
    # default 0.0 is used to avoid an API validation error.
    if os.getenv("LANGCHAIN_PROVIDER", "openai").lower() == "minimax" and temperature <= 0.0:
        temperature = 0.01
    timeout = int(os.getenv("TIMEOUT_SECONDS", "120"))
    max_retries = int(os.getenv("MAX_RETRIES", "2"))
    kwargs: Dict[str, Any] = dict(
        model=name,
        temperature=temperature,
        timeout=timeout,
        max_retries=max_retries,
        callbacks=callbacks,
    )
    # Optional: enable reasoning on relays that require it (e.g. OpenRouter).
    # Moonshot/DeepSeek official APIs emit reasoning_content by default, so
    # this is only relevant for proxy layers. Unknown providers ignore the
    # extra_body field (OpenAI-compatible contract).
    effort = os.getenv("LANGCHAIN_REASONING_EFFORT", "").strip().lower()
    if effort:
        kwargs["extra_body"] = {"reasoning": {"effort": effort}}
    return ChatOpenAIWithReasoning(**kwargs)


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
