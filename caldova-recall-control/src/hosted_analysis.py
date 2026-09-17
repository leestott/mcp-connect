from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


class HostedAnalysisError(Exception):
    pass


class HostedAnalysisTimeout(HostedAnalysisError, TimeoutError):
    pass


@dataclass(frozen=True)
class HostedAnswer:
    text: str
    response_id: str
    request_id: str | None


def parse_answer(payload: dict[str, Any], request_id: str | None) -> HostedAnswer:
    if payload.get("status") != "completed" or payload.get("error"):
        raise HostedAnalysisError("The live agent did not complete its response.")
    response_id = payload.get("id")
    output = payload.get("output")
    if not isinstance(response_id, str) or not response_id or not isinstance(output, list):
        raise HostedAnalysisError("The live agent returned an invalid response.")
    text_parts = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        if item.get("role") != "assistant":
            continue
        if item.get("status", "completed") != "completed":
            raise HostedAnalysisError("The live agent returned a partial response.")
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
    if not text_parts:
        raise HostedAnalysisError("The live agent returned an empty response. No local fallback was used.")
    return HostedAnswer("\n\n".join(text_parts), response_id, request_id)


async def analyze(
    endpoint: str,
    prompt: str,
    correlation_id: str,
    token_provider: Callable[[], Awaitable[str]],
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> HostedAnswer:
    parsed = urlparse(endpoint)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".services.ai.azure.com")
        or parsed.username
        or parsed.password
        or parsed.fragment
        or not parsed.path.endswith("/endpoint/protocols/openai/responses")
    ):
        raise HostedAnalysisError("The live agent endpoint is not configured correctly.")
    try:
        async with asyncio.timeout(180):
            token = await token_provider()
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(170, connect=15), transport=transport, follow_redirects=False
            ) as client:
                response = await client.post(
                    endpoint,
                    params={"api-version": "v1"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "x-ms-client-request-id": correlation_id,
                    },
                    json={"input": prompt, "stream": False},
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise HostedAnalysisError("The live agent returned an invalid response.")
            return parse_answer(payload, response.headers.get("x-ms-request-id"))
    except (TimeoutError, httpx.TimeoutException):
        raise HostedAnalysisTimeout("The live agent request timed out. No inventory was changed.") from None
    except HostedAnalysisError:
        raise
    except Exception:
        raise HostedAnalysisError("The live agent is unavailable. No inventory was changed.") from None