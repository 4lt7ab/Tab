"""Tests for :class:`tab_cli.models.OllamaNativeModel`.

Covers the three places translation can break: pydantic-ai messages →
Ollama wire format on the way in, pydantic-ai tool definitions →
Ollama tool spec, and Ollama responses → pydantic-ai ``ModelResponse``
on the way out. The actual ``/api/chat`` round-trip is tested with a
mocked ``ollama.AsyncClient`` so the suite stays Ollama-server-free.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

from ollama import ChatResponse, Message
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.tools import ToolDefinition

from tab_cli.models import OllamaNativeModel


def _run(coro: Any) -> Any:
    """Run an async coroutine in a fresh event loop. Mirrors test_mcp_server."""
    return asyncio.run(coro)


# --- model_name / system / base_url contract ---


def test_model_name_returns_constructed_value():
    assert OllamaNativeModel("gemma3:latest").model_name == "gemma3:latest"


def test_system_returns_ollama():
    assert OllamaNativeModel("gemma3:latest").system == "ollama"


def test_base_url_defaults_to_localhost_when_host_unset():
    assert OllamaNativeModel("gemma3:latest").base_url == "http://localhost:11434"


def test_base_url_passes_through_explicit_host():
    model = OllamaNativeModel("gemma3:latest", host="http://ollama.lan:11434")
    assert model.base_url == "http://ollama.lan:11434"


def test_provider_returns_none():
    assert OllamaNativeModel("gemma3:latest").provider is None


# --- _translate_messages: pydantic-ai → Ollama wire format ---


def test_translate_system_prompt_part():
    messages = [ModelRequest(parts=[SystemPromptPart(content="Be Tab.")])]
    result = OllamaNativeModel._translate_messages(messages)
    assert result == [{"role": "system", "content": "Be Tab."}]


def test_translate_user_prompt_part_string_content():
    messages = [ModelRequest(parts=[UserPromptPart(content="hi")])]
    result = OllamaNativeModel._translate_messages(messages)
    assert result == [{"role": "user", "content": "hi"}]


def test_translate_user_prompt_part_sequence_content_flattens_strings():
    # Multi-modal content (images, etc.) is out of scope for v0 — non-string
    # parts get dropped, not silently corrupted.
    messages = [ModelRequest(parts=[UserPromptPart(content=["hello ", "world"])])]
    result = OllamaNativeModel._translate_messages(messages)
    assert result == [{"role": "user", "content": "hello world"}]


def test_translate_tool_return_part():
    messages = [
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="web_search",
                    content={"results": ["foo", "bar"]},
                    tool_call_id="call_123",
                )
            ]
        )
    ]
    result = OllamaNativeModel._translate_messages(messages)
    assert len(result) == 1
    assert result[0]["role"] == "tool"
    assert result[0]["tool_name"] == "web_search"
    assert "results" in result[0]["content"]


def test_translate_model_response_text_only():
    messages = [ModelResponse(parts=[TextPart(content="ok")])]
    result = OllamaNativeModel._translate_messages(messages)
    assert result == [{"role": "assistant", "content": "ok"}]


def test_translate_model_response_concatenates_multiple_text_parts():
    # Multi-part assistant turn collapses into a single Ollama message.
    messages = [
        ModelResponse(
            parts=[
                TextPart(content="part one. "),
                TextPart(content="part two."),
            ]
        )
    ]
    result = OllamaNativeModel._translate_messages(messages)
    assert result == [{"role": "assistant", "content": "part one. part two."}]


def test_translate_model_response_with_tool_call():
    messages = [
        ModelResponse(
            parts=[
                TextPart(content="I'll search."),
                ToolCallPart(
                    tool_name="web_search",
                    args={"query": "premature abstraction"},
                    tool_call_id="call_abc",
                ),
            ]
        )
    ]
    result = OllamaNativeModel._translate_messages(messages)
    assert len(result) == 1
    msg = result[0]
    assert msg["role"] == "assistant"
    assert msg["content"] == "I'll search."
    assert msg["tool_calls"] == [
        {
            "function": {
                "name": "web_search",
                "arguments": {"query": "premature abstraction"},
            }
        }
    ]


def test_translate_model_response_tool_call_only_emits_empty_content():
    # Tool-only responses still need a ``content`` field; empty string is the
    # cleanest representation.
    messages = [
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="web_search",
                    args={"query": "x"},
                    tool_call_id="call_x",
                )
            ]
        )
    ]
    result = OllamaNativeModel._translate_messages(messages)
    assert result[0]["content"] == ""
    assert "tool_calls" in result[0]


# --- _translate_tools: pydantic-ai ToolDefinition → Ollama tool spec ---


def test_translate_tools_none_returns_none():
    assert OllamaNativeModel._translate_tools(None) is None
    assert OllamaNativeModel._translate_tools([]) is None


def test_translate_tools_emits_openai_shaped_function_spec():
    tools = [
        ToolDefinition(
            name="web_search",
            description="Search the web for recent information.",
            parameters_json_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )
    ]
    result = OllamaNativeModel._translate_tools(tools)
    assert result == [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for recent information.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]


def test_translate_tools_handles_missing_description():
    tools = [
        ToolDefinition(
            name="t",
            description=None,
            parameters_json_schema={"type": "object", "properties": {}},
        )
    ]
    result = OllamaNativeModel._translate_tools(tools)
    # Empty string keeps Ollama's schema validator happy.
    assert result is not None
    assert result[0]["function"]["description"] == ""


# --- _translate_response: Ollama ChatResponse → pydantic-ai ModelResponse ---


def test_translate_response_text_only():
    response = ChatResponse(
        model="gemma3:latest",
        message=Message(role="assistant", content="hi from ollama"),
    )
    model = OllamaNativeModel("gemma3:latest")
    result = model._translate_response(response)
    assert isinstance(result, ModelResponse)
    assert len(result.parts) == 1
    assert isinstance(result.parts[0], TextPart)
    assert result.parts[0].content == "hi from ollama"
    assert result.model_name == "gemma3:latest"
    assert result.provider_name == "ollama"


def test_translate_response_with_tool_call():
    response = ChatResponse(
        model="gemma3:latest",
        message=Message(
            role="assistant",
            content="searching",
            tool_calls=[
                Message.ToolCall(
                    function=Message.ToolCall.Function(
                        name="web_search",
                        arguments={"query": "ollama vs vllm"},
                    )
                )
            ],
        ),
    )
    model = OllamaNativeModel("gemma3:latest")
    result = model._translate_response(response)
    assert len(result.parts) == 2
    assert isinstance(result.parts[0], TextPart)
    assert result.parts[0].content == "searching"
    assert isinstance(result.parts[1], ToolCallPart)
    assert result.parts[1].tool_name == "web_search"
    assert result.parts[1].args == {"query": "ollama vs vllm"}


def test_translate_response_empty_content_no_tool_calls_yields_no_parts():
    # Honest "model declined to respond" rather than a synthetic empty TextPart.
    response = ChatResponse(
        model="gemma3:latest",
        message=Message(role="assistant", content=None),
    )
    model = OllamaNativeModel("gemma3:latest")
    result = model._translate_response(response)
    assert result.parts == []


# --- request: end-to-end with a mocked AsyncClient ---


def test_request_translates_and_calls_async_client():
    model = OllamaNativeModel("gemma3:latest")
    fake_response = ChatResponse(
        model="gemma3:latest",
        message=Message(role="assistant", content="hello back"),
    )
    model._client = AsyncMock()
    model._client.chat.return_value = fake_response

    messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="be tab"),
                UserPromptPart(content="hi"),
            ]
        )
    ]
    request_params = ModelRequestParameters(
        function_tools=[],
        output_mode="text",
        output_object=None,
        output_tools=[],
        allow_text_output=True,
    )

    result = _run(
        model.request(
            messages=messages,
            model_settings=None,
            model_request_parameters=request_params,
        )
    )

    model._client.chat.assert_awaited_once()
    call_kwargs = model._client.chat.await_args.kwargs
    assert call_kwargs["model"] == "gemma3:latest"
    assert call_kwargs["stream"] is False
    assert call_kwargs["tools"] is None
    assert call_kwargs["messages"] == [
        {"role": "system", "content": "be tab"},
        {"role": "user", "content": "hi"},
    ]
    assert isinstance(result, ModelResponse)
    assert len(result.parts) == 1
    assert isinstance(result.parts[0], TextPart)
    assert result.parts[0].content == "hello back"


def test_request_passes_tools_through_when_present():
    model = OllamaNativeModel("gemma3:latest")
    model._client = AsyncMock()
    model._client.chat.return_value = ChatResponse(
        model="gemma3:latest",
        message=Message(role="assistant", content=""),
    )

    request_params = ModelRequestParameters(
        function_tools=[
            ToolDefinition(
                name="web_search",
                description="Search the web.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            )
        ],
        output_mode="text",
        output_object=None,
        output_tools=[],
        allow_text_output=True,
    )

    _run(
        model.request(
            messages=[ModelRequest(parts=[UserPromptPart(content="x")])],
            model_settings=None,
            model_request_parameters=request_params,
        )
    )

    call_kwargs = model._client.chat.await_args.kwargs
    assert call_kwargs["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]


# --- compile_tab_agent dispatcher ---


def test_compile_tab_agent_dispatches_ollama_prefix_to_native_model():
    """``compile_tab_agent("ollama:<name>")`` builds an agent on the in-house
    ``OllamaNativeModel``, not stock ``OllamaModel`` (which routes through
    ``/v1`` OpenAI-compat).
    """
    from tab_cli.personality import compile_tab_agent

    agent = compile_tab_agent(model="ollama:gemma3:latest")
    assert isinstance(agent.model, OllamaNativeModel)
    assert agent.model.model_name == "gemma3:latest"


def test_compile_tab_agent_passes_anthropic_string_through_verbatim():
    from tab_cli.personality import compile_tab_agent

    agent = compile_tab_agent(model="anthropic:claude-sonnet-4-5")
    assert not isinstance(agent.model, OllamaNativeModel)


def test_compile_tab_agent_none_model_passes_through():
    from tab_cli.personality import compile_tab_agent

    agent = compile_tab_agent(model=None)
    assert not isinstance(agent.model, OllamaNativeModel)


# --- streaming: OllamaNativeModel.request_stream + _OllamaStreamedResponse ---


def _async_iter(items: list[Any]) -> Any:
    """Wrap a list as an async iterator for streamed-response stubs."""

    async def _gen():
        for item in items:
            yield item

    return _gen()


def test_request_stream_yields_text_deltas_through_parts_manager():
    """Streamed ``message.content`` fragments must reach the parts manager
    as text deltas — chat.py's ``stream_text(delta=True)`` reads those events."""
    model = OllamaNativeModel("gemma3:latest")
    chunks = [
        ChatResponse(
            model="gemma3:latest",
            message=Message(role="assistant", content="hello"),
        ),
        ChatResponse(
            model="gemma3:latest",
            message=Message(role="assistant", content=", "),
        ),
        ChatResponse(
            model="gemma3:latest",
            message=Message(role="assistant", content="world."),
            done=True,
        ),
    ]
    model._client = AsyncMock()
    model._client.chat.return_value = _async_iter(chunks)

    request_params = ModelRequestParameters(
        function_tools=[],
        output_mode="text",
        output_object=None,
        output_tools=[],
        allow_text_output=True,
    )

    async def _drain() -> str:
        out: list[str] = []
        async with model.request_stream(
            messages=[ModelRequest(parts=[UserPromptPart(content="hi")])],
            model_settings=None,
            model_request_parameters=request_params,
        ) as streamed:
            async for _event in streamed:
                pass
            response = streamed.get()
            for part in response.parts:
                if isinstance(part, TextPart):
                    out.append(part.content)
        return "".join(out)

    text = _run(_drain())
    assert text == "hello, world."


def test_request_stream_passes_messages_and_tools_to_client():
    """Streamed path calls ``AsyncClient.chat`` with ``stream=True`` and
    the same translated payload the non-stream path uses."""
    model = OllamaNativeModel("gemma3:latest")
    model._client = AsyncMock()
    model._client.chat.return_value = _async_iter(
        [
            ChatResponse(
                model="gemma3:latest",
                message=Message(role="assistant", content="ok"),
                done=True,
            )
        ]
    )

    tool = ToolDefinition(
        name="web_search",
        description="search",
        parameters_json_schema={"type": "object", "properties": {}},
    )
    request_params = ModelRequestParameters(
        function_tools=[tool],
        output_mode="text",
        output_object=None,
        output_tools=[],
        allow_text_output=True,
    )

    async def _drain() -> None:
        async with model.request_stream(
            messages=[
                ModelRequest(
                    parts=[
                        SystemPromptPart(content="be tab"),
                        UserPromptPart(content="search please"),
                    ]
                )
            ],
            model_settings=None,
            model_request_parameters=request_params,
        ) as streamed:
            async for _event in streamed:
                pass

    _run(_drain())

    call_kwargs = model._client.chat.await_args.kwargs
    assert call_kwargs["model"] == "gemma3:latest"
    assert call_kwargs["stream"] is True
    assert call_kwargs["messages"] == [
        {"role": "system", "content": "be tab"},
        {"role": "user", "content": "search please"},
    ]
    assert call_kwargs["tools"] is not None
    assert call_kwargs["tools"][0]["function"]["name"] == "web_search"


def test_request_stream_emits_tool_call_when_chunk_has_tool_calls():
    """Ollama emits the full tool-call as one chunk after text streaming;
    the parts list contains both ``TextPart`` and ``ToolCallPart``."""
    model = OllamaNativeModel("gemma3:latest")
    chunks = [
        ChatResponse(
            model="gemma3:latest",
            message=Message(role="assistant", content="searching"),
        ),
        ChatResponse(
            model="gemma3:latest",
            message=Message(
                role="assistant",
                content="",
                tool_calls=[
                    Message.ToolCall(
                        function=Message.ToolCall.Function(
                            name="web_search",
                            arguments={"query": "ollama streaming"},
                        )
                    )
                ],
            ),
            done=True,
        ),
    ]
    model._client = AsyncMock()
    model._client.chat.return_value = _async_iter(chunks)

    request_params = ModelRequestParameters(
        function_tools=[],
        output_mode="text",
        output_object=None,
        output_tools=[],
        allow_text_output=True,
    )

    async def _drain() -> Any:
        async with model.request_stream(
            messages=[ModelRequest(parts=[UserPromptPart(content="search")])],
            model_settings=None,
            model_request_parameters=request_params,
        ) as streamed:
            async for _event in streamed:
                pass
            return streamed.get()

    response = _run(_drain())
    text_parts = [p for p in response.parts if isinstance(p, TextPart)]
    tool_parts = [p for p in response.parts if isinstance(p, ToolCallPart)]
    assert len(text_parts) == 1
    assert text_parts[0].content == "searching"
    assert len(tool_parts) == 1
    assert tool_parts[0].tool_name == "web_search"
    assert tool_parts[0].args == {"query": "ollama streaming"}


def test_streamed_response_metadata_properties():
    """``model_name``, ``provider_name``, ``provider_url``, ``timestamp`` —
    diagnostic surface answerable without a real request."""
    from datetime import datetime

    from tab_cli.models.ollama_native import _OllamaStreamedResponse

    request_params = ModelRequestParameters(
        function_tools=[],
        output_mode="text",
        output_object=None,
        output_tools=[],
        allow_text_output=True,
    )
    streamed = _OllamaStreamedResponse(
        model_request_parameters=request_params,
        _model_name="gemma3:latest",
        _provider_url="http://localhost:11434",
        _response=None,
    )

    assert streamed.model_name == "gemma3:latest"
    assert streamed.provider_name == "ollama"
    assert streamed.provider_url == "http://localhost:11434"
    assert isinstance(streamed.timestamp, datetime)
