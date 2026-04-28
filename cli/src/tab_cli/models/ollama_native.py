"""A pydantic-ai ``Model`` backed by ``ollama-python``'s ``/api/chat``.

Why this exists: pydantic-ai's stock ``OllamaModel`` extends ``OpenAIChatModel``
and routes through Ollama's ``/v1`` OpenAI-compat endpoint. That layer has
known model-registration drift on some installs — local Ollama daemons can
have chat models pulled and runnable via ``ollama run`` while ``/v1/models``
and ``/v1/chat/completions`` return 404 for the same names. ``/api/chat`` is
the canonical Ollama surface and works regardless.

The wrapper is the bug-fixing minimum: ``request`` + ``request_stream`` +
message/tool/response translators. When pydantic-ai upstream fixes the
``/v1`` registration drift, retire this in favor of stock ``OllamaModel``.
"""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, cast

from ollama import AsyncClient as _OllamaAsyncClient
from ollama import ChatResponse as _OllamaChatResponse
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponseStreamEvent,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse
from pydantic_ai.profiles import ModelProfileSpec
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import ToolDefinition


class OllamaNativeModel(Model):
    """A pydantic-ai ``Model`` that talks to Ollama via the official client.

    Construct with the bare model name (no ``ollama:`` prefix). When ``host``
    is ``None``, ``ollama-python`` resolves from ``OLLAMA_HOST`` then
    ``localhost:11434``.
    """

    def __init__(
        self,
        model_name: str,
        *,
        host: str | None = None,
        settings: ModelSettings | None = None,
        profile: ModelProfileSpec | None = None,
    ) -> None:
        super().__init__(settings=settings, profile=profile)
        self._model_name = model_name
        self._host = host
        self._client = _OllamaAsyncClient(host=host)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system(self) -> str:
        return "ollama"

    @property
    def base_url(self) -> str | None:
        # Report the canonical default rather than ``None`` so diagnostics
        # ("which Ollama did this hit?") stay answerable from the model alone.
        return self._host or "http://localhost:11434"

    @property
    def provider(self) -> None:
        # We hold our own ``ollama.AsyncClient``; no pydantic-ai ``Provider``.
        return None

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        response = await self._client.chat(
            model=self._model_name,
            messages=self._translate_messages(messages),
            tools=self._translate_tools(model_request_parameters.function_tools),
            stream=False,
        )
        return self._translate_response(response)

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: Any | None = None,
    ) -> AsyncIterator[StreamedResponse]:
        response_iter = await self._client.chat(
            model=self._model_name,
            messages=self._translate_messages(messages),
            tools=self._translate_tools(model_request_parameters.function_tools),
            stream=True,
        )
        yield _OllamaStreamedResponse(
            model_request_parameters=model_request_parameters,
            _model_name=self._model_name,
            _provider_url=self.base_url,
            _response=response_iter,
        )

    @staticmethod
    def _translate_messages(messages: list[ModelMessage]) -> list[dict[str, Any]]:
        """Convert pydantic-ai messages to Ollama's ``{role, content}`` shape.

        Multi-part assistant responses collapse into a single message —
        Ollama expects one assistant turn on the wire. Multi-modal user
        content flattens to text (v0 scope).
        """
        out: list[dict[str, Any]] = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, SystemPromptPart):
                        out.append({"role": "system", "content": part.content})
                    elif isinstance(part, UserPromptPart):
                        if isinstance(part.content, str):
                            text = part.content
                        else:
                            text = "".join(
                                p if isinstance(p, str) else "" for p in part.content
                            )
                        out.append({"role": "user", "content": text})
                    elif isinstance(part, ToolReturnPart):
                        out.append(
                            {
                                "role": "tool",
                                "content": part.model_response_str(),
                                "tool_name": part.tool_name,
                            }
                        )
            elif isinstance(msg, ModelResponse):
                content_segments: list[str] = []
                tool_calls: list[dict[str, Any]] = []
                for part in msg.parts:
                    if isinstance(part, TextPart):
                        content_segments.append(part.content)
                    elif isinstance(part, ToolCallPart):
                        tool_calls.append(
                            {
                                "function": {
                                    "name": part.tool_name,
                                    "arguments": part.args_as_dict(),
                                }
                            }
                        )
                msg_dict: dict[str, Any] = {
                    "role": "assistant",
                    "content": "".join(content_segments),
                }
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
                out.append(msg_dict)
        return out

    @staticmethod
    def _translate_tools(
        tools: list[ToolDefinition] | None,
    ) -> list[dict[str, Any]] | None:
        """Convert pydantic-ai ``ToolDefinition`` list to Ollama's tool spec."""
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.parameters_json_schema,
                },
            }
            for tool in tools
        ]

    def _translate_response(self, response: _OllamaChatResponse) -> ModelResponse:
        """Convert an Ollama ``ChatResponse`` to a pydantic-ai ``ModelResponse``."""
        parts: list[Any] = []
        msg = response.message
        if msg.content:
            parts.append(TextPart(content=msg.content))
        if msg.tool_calls:
            for call in msg.tool_calls:
                args: dict[str, Any] = (
                    dict(call.function.arguments) if call.function.arguments else {}
                )
                parts.append(
                    ToolCallPart(
                        tool_name=call.function.name,
                        args=cast(dict[str, Any], args),
                    )
                )
        return ModelResponse(
            parts=parts,
            model_name=self._model_name,
            provider_name="ollama",
        )


@dataclass
class _OllamaStreamedResponse(StreamedResponse):
    """pydantic-ai ``StreamedResponse`` adapter for ``ollama-python`` streams."""

    _model_name: str = ""
    _provider_url: str | None = None
    _response: AsyncIterable[_OllamaChatResponse] | None = None
    _timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:
        if self._response is None:
            return
        tool_call_index = 0
        async for chunk in self._response:
            msg = chunk.message
            if msg.content:
                for event in self._parts_manager.handle_text_delta(
                    vendor_part_id=None,
                    content=msg.content,
                ):
                    yield event
            if msg.tool_calls:
                for call in msg.tool_calls:
                    args: dict[str, Any] = (
                        dict(call.function.arguments)
                        if call.function.arguments
                        else {}
                    )
                    vendor_id = f"tc_{tool_call_index}"
                    tool_call_index += 1
                    event = self._parts_manager.handle_tool_call_delta(
                        vendor_part_id=vendor_id,
                        tool_name=call.function.name,
                        args=cast(dict[str, Any], args),
                        tool_call_id=vendor_id,
                    )
                    if event is not None:
                        yield event

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def provider_url(self) -> str | None:
        return self._provider_url

    @property
    def timestamp(self) -> datetime:
        return self._timestamp
