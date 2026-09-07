from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Event, Timer
from typing import Any, Protocol

from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError, OpenAI

from .configuration import ModelConfig


class ModelClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
    ) -> str: ...


class ModelOutputError(RuntimeError):
    """A completed HTTP exchange did not contain usable model output."""


@dataclass
class OpenAICompatibleClient:
    api_key: str = field(repr=False)
    model: str
    base_url: str
    timeout_seconds: float = 90
    streaming: bool = False
    reasoning_effort: str | None = None
    max_completion_tokens: int | None = None
    max_tokens: int | None = None
    on_progress: Callable[[int], None] | None = field(default=None, repr=False)
    on_notice: Callable[[str], None] | None = field(default=None, repr=False)

    @classmethod
    def from_config(cls, config: ModelConfig):
        return cls(config.api_key, config.model, config.base_url)

    def _sdk(self) -> OpenAI:
        if not self.api_key:
            raise RuntimeError("请先保存模型配置")
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            max_retries=0,
        )

    def _failure(self, error: Exception) -> RuntimeError:
        if isinstance(error, APIStatusError):
            # Redact before truncation so the length cap cannot reveal a key prefix.
            detail = str(error.body).replace(self.api_key, "[REDACTED]")[:500]
            return RuntimeError(f"模型服务 HTTP {error.status_code}: {detail}")
        if isinstance(error, APITimeoutError):
            return RuntimeError("模型服务超时，请稍后重试")
        if isinstance(error, APIConnectionError):
            return RuntimeError("无法连接模型服务，请检查 API 地址和网络")
        if isinstance(error, APIError):
            # Streams can carry service errors after HTTP 200, such as busy.
            detail = str(error).replace(self.api_key, "[REDACTED]")[:500]
            return RuntimeError("模型服务返回错误：" + detail)
        return RuntimeError("模型服务返回了无效响应，请检查 API 地址是否指向兼容 API")

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        # SDK owns HTTP/authentication/error parsing. Omit temperature for models that reject it.
        timed_out = Event()
        try:
            with self._sdk() as sdk:
                # SSE keep-alives must not keep a stalled generation alive
                # indefinitely. Close the transport at a wall-clock deadline.
                def expire():
                    timed_out.set()
                    sdk.close()

                deadline = Timer(self.timeout_seconds, expire)
                deadline.daemon = True
                deadline.start()
                try:
                    return self._complete(sdk, messages, response_format)
                finally:
                    deadline.cancel()
        except (APIError, ValueError, TypeError, AttributeError, IndexError) as error:
            if timed_out.is_set():
                raise RuntimeError(
                    "模型生成超过时间限制，未发布游戏；请重试或选择其他模型"
                ) from error
            if (
                isinstance(error, APIStatusError)
                and error.status_code == 400
                and self.max_tokens
                and "max_tokens" in str(error.body)
            ):
                self.max_completion_tokens, self.max_tokens = self.max_tokens, None
                if self.on_notice:
                    self.on_notice("服务要求新版输出长度参数，保持同一上限重试")
                return self.complete(messages, response_format=response_format)
            if (
                isinstance(error, APIStatusError)
                and error.status_code == 400
                and self.max_completion_tokens
                and "max_completion_tokens" in str(error.body)
            ):
                self.max_completion_tokens = None
                if self.on_notice:
                    self.on_notice("服务不接受输出长度参数，改用服务默认值重试")
                return self.complete(messages, response_format=response_format)
            if (
                isinstance(error, APIStatusError)
                and error.status_code == 400
                and self.reasoning_effort
                and "reasoning_effort" in str(error.body)
            ):
                self.reasoning_effort = None
                if self.on_notice:
                    self.on_notice("服务不接受思考强度提示，改用服务默认值重试")
                return self.complete(messages, response_format=response_format)
            raise self._failure(error) from error

    def _complete(self, sdk, messages, response_format):
        result = sdk.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=self.streaming,
            **(
                {"max_tokens": self.max_tokens}
                if self.max_tokens
                else {"max_completion_tokens": self.max_completion_tokens}
                if self.max_completion_tokens
                else {}
            ),
            **(
                {"reasoning_effort": self.reasoning_effort}
                if self.reasoning_effort
                else {}
            ),
            **({"response_format": response_format} if response_format else {}),
        )
        if self.streaming:
            parts, size, reported, finished = [], 0, 0, False
            with result:
                for chunk in result:
                    for choice in chunk.choices:
                        if choice.index != 0:
                            continue
                        if choice.finish_reason:
                            if choice.finish_reason != "stop":
                                raise ModelOutputError(
                                    "模型输出未完成："
                                    + choice.finish_reason
                                    + "，未使用截断内容"
                                )
                            finished = True
                        # Some compatible services use delta:null for their final
                        # chunk. Its finish_reason still completes the stream.
                        fragment = (
                            choice.delta.content if choice.delta is not None else None
                        )
                        if fragment:
                            parts.append(fragment)
                            size += len(fragment)
                            if size > 100000:
                                raise ModelOutputError(
                                    "模型输出超过长度限制，未使用该内容"
                                )
                            if self.on_progress and size - reported >= 1000:
                                self.on_progress(size)
                                reported = size
            if not finished:
                raise ModelOutputError("模型输出流提前结束，未使用不完整内容")
            content = "".join(parts)
        else:
            content = result.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty model message")
        return content

    def list_models(self) -> list[str]:
        try:
            with self._sdk() as sdk:
                # Inspect raw JSON to accept common compatible gateway envelopes.
                response = sdk.models.with_raw_response.list()
                body = response.http_response.json()
            candidates = (
                body.get("data", body.get("models")) if isinstance(body, dict) else body
            )
            if not isinstance(candidates, list):
                raise ValueError("expected model array")
            names = set()
            for item in candidates:
                value = (
                    item
                    if isinstance(item, str)
                    else next(
                        (
                            item[key]
                            for key in ("id", "name", "model")
                            if isinstance(item.get(key), str)
                        ),
                        None,
                    )
                    if isinstance(item, dict)
                    else None
                )
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("invalid model entry")
                names.add(value.strip())
            return sorted(names)
        except (
            APIStatusError,
            APIConnectionError,
            ValueError,
            TypeError,
            AttributeError,
        ) as error:
            raise self._failure(error) from error
