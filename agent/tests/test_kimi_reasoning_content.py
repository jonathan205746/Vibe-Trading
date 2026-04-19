"""Regression tests for Kimi thinking/tool-call compatibility."""

from __future__ import annotations

import os
from types import SimpleNamespace

from src.agent.context import ContextBuilder
from src.providers.chat import ChatLLM, ToolCallRequest
from src.providers.llm import ChatOpenAIWithReasoning


class TestKimiReasoningContent:
    def test_parse_response_keeps_reasoning_content(self) -> None:
        ai_message = SimpleNamespace(
            content="",
            reasoning_content="step-by-step reasoning",
            tool_calls=[
                {
                    "id": "tc_1",
                    "name": "bash",
                    "args": {"command": "pwd"},
                }
            ],
            additional_kwargs={},
            response_metadata={"finish_reason": "tool_calls"},
        )

        response = ChatLLM._parse_response(ai_message)

        assert response.reasoning_content == "step-by-step reasoning"
        assert response.finish_reason == "tool_calls"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].arguments == {"command": "pwd"}

    def test_parse_response_falls_back_to_additional_kwargs(self) -> None:
        ai_message = SimpleNamespace(
            content="",
            tool_calls=[],
            additional_kwargs={"reasoning_content": "fallback reasoning"},
            response_metadata={"finish_reason": "stop"},
        )

        response = ChatLLM._parse_response(ai_message)

        assert response.reasoning_content == "fallback reasoning"

    def test_format_assistant_tool_calls_preserves_reasoning_content(self) -> None:
        message = ContextBuilder.format_assistant_tool_calls(
            [
                ToolCallRequest(
                    id="tc_1",
                    name="bash",
                    arguments={"command": "pwd"},
                )
            ],
            content="",
            reasoning_content="step-by-step reasoning",
        )

        assert message["role"] == "assistant"
        assert message["reasoning_content"] == "step-by-step reasoning"
        assert message["tool_calls"][0]["id"] == "tc_1"

    def test_format_assistant_tool_calls_omits_reasoning_when_absent(self) -> None:
        message = ContextBuilder.format_assistant_tool_calls(
            [
                ToolCallRequest(
                    id="tc_1",
                    name="bash",
                    arguments={"command": "pwd"},
                )
            ],
            content="",
        )

        assert "reasoning_content" not in message


class TestChatOpenAIWithReasoning:
    """End-to-end test that reasoning_content survives the langchain-openai layer.

    langchain-openai 0.3.x's _convert_dict_to_message drops unknown fields
    (reasoning_content included). Our subclass re-reads the raw response
    and restores them into additional_kwargs.
    """

    def test_subclass_preserves_reasoning_content_on_tool_call_response(self) -> None:
        os.environ.setdefault("OPENAI_API_KEY", "sk-test")
        instance = ChatOpenAIWithReasoning(model="kimi-k2.5", api_key="sk-test")

        moonshot_like_response = {
            "id": "chatcmpl-test",
            "model": "kimi-k2.5",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "reasoning_content": "step-by-step reasoning from provider",
                        "tool_calls": [
                            {
                                "id": "tc_1",
                                "type": "function",
                                "function": {
                                    "name": "bash",
                                    "arguments": "{\"command\":\"pwd\"}",
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        result = instance._create_chat_result(moonshot_like_response)
        message = result.generations[0].message

        assert message.additional_kwargs.get("reasoning_content") == "step-by-step reasoning from provider"

    def test_subclass_no_reasoning_content_when_absent(self) -> None:
        """Non-thinking providers (OpenAI, Claude, etc.) must see no change."""
        os.environ.setdefault("OPENAI_API_KEY", "sk-test")
        instance = ChatOpenAIWithReasoning(model="gpt-4", api_key="sk-test")

        openai_like_response = {
            "id": "chatcmpl-test",
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "hello",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
        }

        result = instance._create_chat_result(openai_like_response)
        message = result.generations[0].message

        assert "reasoning_content" not in message.additional_kwargs
