"""
Anthropic-to-OpenCode proxy with reasoning_content fix.

This proxy sits between Claude Code and OpenCode, translating
Anthropic API format to OpenAI format while injecting missing
reasoning_content into assistant messages with tool_calls.

This fixes the 400 error from Moonshot/DeepSeek/GLM providers
when tool results are sent back in multi-turn conversations.
"""

import json
import os
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

app = FastAPI()

# Config
OPCODE_API_KEY = os.environ["OPCODE_API_KEY"]
OPCODE_BASE = "https://opencode.ai/zen/go/v1"

# Model mapping: Anthropic name -> OpenCode name
MODEL_MAP = {
    "kimi-k2.6": "kimi-k2.6",
    "kimi-k2.5": "kimi-k2.5",
    "deepseek-v4-pro": "deepseek-v4-pro",
    "deepseek-v4-flash": "deepseek-v4-flash",
    "glm-5.1": "glm-5.1",
    "glm-5": "glm-5",
    "mimo-v2.5-pro": "mimo-v2.5-pro",
    "mimo-v2.5": "mimo-v2.5",
    "qwen3.6-plus": "qwen3.6-plus",
    "qwen3.5-plus": "qwen3.5-plus",
    "minimax-m2.7": "minimax-m2.7",
    "minimax-m2.5": "minimax-m2.5",
}

async def _proxy_openai(path: str, request: Request):
    """Forward OpenAI-format requests directly (used by /v1/models etc)."""
    body = await request.body()
    headers = {
        "Authorization": f"Bearer {OPCODE_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method=request.method,
            url=f"{OPCODE_BASE}/{path}",
            headers=headers,
            content=body,
            timeout=300.0,
        )
    # Remove compression headers since httpx already decompressed
    response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in ("content-encoding", "transfer-encoding")}
    return Response(content=resp.content, status_code=resp.status_code, headers=response_headers)

@app.get("/v1/models")
async def list_models(request: Request):
    return await _proxy_openai("models", request)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    return await _proxy_openai("chat/completions", request)

@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    """Translate Anthropic /v1/messages to OpenAI /v1/chat/completions."""
    body = await request.json()

    # Extract fields
    model = MODEL_MAP.get(body.get("model", "kimi-k2.6"), body.get("model"))
    max_tokens = body.get("max_tokens", 4096)
    messages = body.get("messages", [])
    system = body.get("system")
    tools = body.get("tools", [])
    stream = body.get("stream", False)
    temperature = body.get("temperature")
    top_p = body.get("top_p")

    # Convert messages
    openai_messages = []
    if system:
        if isinstance(system, str):
            openai_messages.append({"role": "system", "content": system})
        elif isinstance(system, list):
            # Anthropic system can be array of text blocks
            text_parts = [s.get("text", "") for s in system if s.get("type") == "text"]
            if text_parts:
                openai_messages.append({"role": "system", "content": "\n".join(text_parts)})

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "user":
            if isinstance(content, list):
                # Convert content blocks
                text_parts = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        # Tool result becomes a tool message
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id", ""),
                            "content": block.get("content", ""),
                        })
                        continue
                if text_parts:
                    openai_messages.append({"role": "user", "content": "\n".join(text_parts)})
            else:
                openai_messages.append({"role": "user", "content": content or ""})

        elif role == "assistant":
            assistant_msg = {"role": "assistant", "content": None}

            if isinstance(content, list):
                text_parts = []
                tool_calls = []
                reasoning_parts = []

                for block in content:
                    btype = block.get("type")
                    if btype == "text":
                        text_parts.append(block.get("text", ""))
                    elif btype == "thinking":
                        reasoning_parts.append(block.get("thinking", ""))
                    elif btype == "tool_use":
                        tool_calls.append({
                            "id": block.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": block.get("name", ""),
                                "arguments": json.dumps(block.get("input", {})),
                            }
                        })

                if text_parts:
                    assistant_msg["content"] = "\n".join(text_parts)
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                if reasoning_parts:
                    assistant_msg["reasoning_content"] = "\n".join(reasoning_parts)
                elif tool_calls and not reasoning_parts:
                    # FIX: inject minimal reasoning_content when tool_calls exist but no thinking
                    assistant_msg["reasoning_content"] = "."

            else:
                assistant_msg["content"] = content or ""

            openai_messages.append(assistant_msg)

    # Convert tools
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            }
        })

    payload = {
        "model": model,
        "messages": openai_messages,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if openai_tools:
        payload["tools"] = openai_tools

    # Forward to OpenCode
    headers = {
        "Authorization": f"Bearer {OPCODE_API_KEY}",
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",  # Disable compression to avoid gzip issues
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OPCODE_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=300.0,
        )

    if not stream:
        openai_data = resp.json()
        anthropic_resp = _openai_to_anthropic(openai_data)
        return Response(
            content=json.dumps(anthropic_resp),
            status_code=resp.status_code,
            headers={"Content-Type": "application/json"},
        )
    else:
        # Streaming: translate SSE events
        async def stream_generator():
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    try:
                        chunk = json.loads(data)
                        for event in _openai_chunk_to_anthropic(chunk):
                            yield f"data: {json.dumps(event)}\n\n"
                    except json.JSONDecodeError:
                        yield f"data: {data}\n\n"
                else:
                    yield line + "\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

def _openai_to_anthropic(openai_data: dict) -> dict:
    """Convert OpenAI chat.completion to Anthropic message format."""
    choice = openai_data.get("choices", [{}])[0]
    msg = choice.get("message", {})

    content = []

    # Add thinking/reasoning if present
    reasoning = msg.get("reasoning") or msg.get("reasoning_content")
    if reasoning:
        content.append({
            "type": "thinking",
            "thinking": reasoning,
            "signature": None,
        })

    # Add text content
    text = msg.get("content")
    if text:
        content.append({"type": "text", "text": text})

    # Add tool_calls
    tool_calls = msg.get("tool_calls", [])
    for tc in tool_calls:
        func = tc.get("function", {})
        content.append({
            "type": "tool_use",
            "id": tc.get("id", ""),
            "name": func.get("name", ""),
            "input": json.loads(func.get("arguments", "{}")),
        })

    usage = openai_data.get("usage", {})

    return {
        "id": openai_data.get("id", ""),
        "type": "message",
        "role": "assistant",
        "model": openai_data.get("model", ""),
        "content": content,
        "stop_reason": _map_finish_reason(choice.get("finish_reason")),
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }

def _openai_chunk_to_anthropic(chunk: dict):
    """Convert OpenAI streaming chunk to Anthropic SSE events."""
    choice = chunk.get("choices", [{}])[0]
    delta = choice.get("delta", {})

    events = []

    # Start message
    if chunk.get("choices") and not delta.get("content") and not delta.get("tool_calls") and not delta.get("reasoning"):
        events.append({
            "type": "message_start",
            "message": {
                "id": chunk.get("id", ""),
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": chunk.get("model", ""),
                "stop_reason": None,
            }
        })

    # Text delta
    text = delta.get("content")
    if text:
        events.append({
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": text},
        })

    # Thinking delta
    reasoning = delta.get("reasoning") or delta.get("reasoning_content")
    if reasoning:
        events.append({
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "thinking_delta", "thinking": reasoning},
        })

    # Tool calls
    tool_calls = delta.get("tool_calls", [])
    for tc in tool_calls:
        func = tc.get("function", {})
        events.append({
            "type": "content_block_delta",
            "index": tc.get("index", 0),
            "delta": {
                "type": "tool_use_delta",
                "id": tc.get("id", ""),
                "name": func.get("name", ""),
                "input": func.get("arguments", ""),
            }
        })

    # Stop reason
    finish_reason = choice.get("finish_reason")
    if finish_reason:
        events.append({
            "type": "message_delta",
            "delta": {"stop_reason": _map_finish_reason(finish_reason)},
        })

    return events

def _map_finish_reason(reason: str) -> str:
    mapping = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "content_filter": "content_filter",
    }
    return mapping.get(reason, reason)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
