# LiteLLM OpenCode Proxy

A Dockerized [LiteLLM](https://github.com/BerriAI/litellm) proxy setup that bridges **Claude Code** with **OpenCode Go Plan** models. It translates Anthropic's native API format (`/v1/messages`) to OpenAI-compatible endpoints (`/v1/chat/completions`) so Claude Code can use models like `kimi-k2.6`, `deepseek-v4-pro`, `glm-5.1`, and others.

---

## Architecture

```
Claude Code (Anthropic API)
    |
    v
http://localhost:38765/anthropic/v1/messages
    |
    v
Caddy Reverse Proxy (:38765)
    |
    v
Custom Proxy (:8001)  ← Anthropic → OpenAI translation + reasoning_content fix
    |
    v
https://opencode.ai/zen/go/v1/chat/completions
    |
    v
OpenCode Go Plan (kimi-k2.6, deepseek-v4-pro, etc.)
```

> **Why a custom proxy?** LiteLLM 1.82+ drops `thinking` content when translating Anthropic assistant messages with `tool_calls` to OpenAI format. OpenCode's providers (Moonshot, DeepSeek, GLM) require `reasoning_content` on every assistant message that contains `tool_calls`. The custom proxy preserves this content, fixing the `400 BadRequest` error on multi-turn tool conversations.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/installation)
- An [OpenCode](https://opencode.ai) account with API access

---

## Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/marwanahmedaly/claude-code-opencode-bridge.git
cd claude-code-opencode-bridge
```

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenCode API key:

```env
OPCODE_API_KEY=sk-your-opencode-api-key-here
```

> Get your API key from [OpenCode Settings](https://opencode.ai/settings/api-keys).

### 2. Start the Proxy

```bash
docker compose up -d
```

This starts three containers:
- `litellm-opencode` — The LiteLLM proxy (internal port `8000`)
- `opencode-proxy` — Custom FastAPI proxy that translates Anthropic → OpenAI with `reasoning_content` fix (internal port `8001`)
- `litellm-proxy` — Caddy reverse proxy (exposed on `38765`)

### 3. Verify It's Working

```bash
# Test health
curl http://localhost:38765/anthropic/v1/models \
  -H "x-api-key: dummy"

# Test a chat completion
curl -X POST http://localhost:38765/anthropic/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: dummy" \
  -d '{
    "model": "kimi-k2.6",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 50
  }'
```

### 4. Use with Claude Code

#### Option A: Shell Aliases (Recommended)

Source the provided aliases in your `.zshrc`:

```bash
source /path/to/claude-code-opencode-bridge/aliases.zsh
```

This gives you one-command shortcuts for every model:

```bash
# Interactive sessions
claude-kimi              # kimi-k2.6 (best overall)
claude-kimi25            # kimi-k2.5 (fast)
claude-deepseek          # deepseek-v4-pro (reasoning)
claude-deepseek-flash    # deepseek-v4-flash
claude-glm51             # glm-5.1
claude-glm5              # glm-5
claude-mimo              # mimo-v2.5-pro
claude-mimo-fast         # mimo-v2.5
claude-qwen              # qwen3.6-plus
claude-qwen-fast         # qwen3.5-plus
claude-minimax           # minimax-m2.7
claude-minimax-fast      # minimax-m2.5

# One-shot / pipe mode
claude-kimi -p "Refactor this function"
echo "Explain this error" | claude-deepseek -p

# Generic: pass any model name
claude-opencode kimi-k2.6 -p "Hello"
```

All arguments pass through — add `-p`, `--allowed-tools`, etc. as usual.

#### Option B: Manual Environment Variables

```bash
export ANTHROPIC_BASE_URL=http://localhost:38765/anthropic
export ANTHROPIC_API_KEY=dummy
export ANTHROPIC_MODEL=kimi-k2.6

# Interactive mode
claude

# Or one-shot mode
claude -p "Explain quantum computing in simple terms"
```

#### Option C: Claude Code Settings File

Add to `~/.claude/settings.json` or `.claude/settings.local.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:38765/anthropic",
    "ANTHROPIC_API_KEY": "dummy",
    "ANTHROPIC_MODEL": "kimi-k2.6"
  }
}
```

---

## Available Models

| Model | Format | Notes |
|-------|--------|-------|
| `kimi-k2.6` | OpenAI | Moonshot AI — best overall |
| `kimi-k2.5` | OpenAI | Moonshot AI — fast |
| `deepseek-v4-pro` | OpenAI | DeepSeek reasoning |
| `deepseek-v4-flash` | OpenAI | DeepSeek fast |
| `glm-5.1` | OpenAI | Zhipu AI |
| `glm-5` | OpenAI | Zhipu AI |
| `mimo-v2.5-pro` | OpenAI | 01.AI |
| `mimo-v2.5` | OpenAI | 01.AI |
| `qwen3.6-plus` | OpenAI | Alibaba |
| `qwen3.5-plus` | OpenAI | Alibaba |
| `minimax-m2.7` | Anthropic | Native messages format |
| `minimax-m2.5` | Anthropic | Native messages format |

---

## Configuration Files

### `opencode-proxy.py`

**The core of this setup.** A custom FastAPI proxy that:
- Receives Anthropic `/v1/messages` requests from Claude Code
- Translates Anthropic format → OpenAI format
- **Injects `reasoning_content`** into assistant messages that have `tool_calls` but no thinking content
- Forwards to OpenCode and translates the response back to Anthropic format

This fixes the `400 BadRequest` error that occurs on multi-turn tool conversations.

### `Dockerfile.proxy`

Builds the custom proxy image from `python:3.12-slim` with `fastapi`, `httpx`, and `uvicorn`.

### `docker-compose.yml`

```yaml
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: litellm-opencode
    expose:
      - "8000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    environment:
      - OPCODE_API_KEY=${OPCODE_API_KEY}
      - LITELLM_USE_CHAT_COMPLETIONS_URL_FOR_ANTHROPIC_MESSAGES=true
    command: >
      --config /app/config.yaml
      --port 8000
    restart: unless-stopped

  opencode-proxy:
    build:
      context: .
      dockerfile: Dockerfile.proxy
    container_name: opencode-proxy
    expose:
      - "8001"
    environment:
      - OPCODE_API_KEY=${OPCODE_API_KEY}
    restart: unless-stopped

  proxy:
    image: caddy:2-alpine
    container_name: litellm-proxy
    ports:
      - "38765:38765"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
    restart: unless-stopped
```

### `Caddyfile`

Routes `/anthropic/*` requests from Claude Code to the custom proxy:

```caddy
:38765
handle_path /anthropic/* {
    reverse_proxy opencode-proxy:8001
}

# Direct LiteLLM access (OpenAI format)
handle_path /openai/* {
    reverse_proxy litellm:8000
}

handle {
    respond "Not Found" 404
}
```

### `config.yaml` (Fallback)

LiteLLM config for direct OpenAI-format access. The custom proxy handles Anthropic translation instead.

### `.mcp.json` (Optional)

Project-level MCP server config for Claude Code. Currently includes Context7 for documentation lookup.

---

## The Critical Fix: `reasoning_content`

When Claude Code sends a multi-turn conversation with tools, the assistant message contains `tool_calls` (from a previous turn). OpenCode's providers (Moonshot AI, DeepSeek, Zhipu GLM) require every assistant message with `tool_calls` to also include `reasoning_content`.

**Without the fix:**
```
API Error: 400 litellm.BadRequestError: OpenAIException - Error from provider:
Provider returned error. Received Model Group=kimi-k2.6
```

**Root cause:** LiteLLM drops the `thinking` content block when translating Anthropic assistant messages to OpenAI format. The resulting assistant message has `tool_calls` but no `reasoning_content`, which Moonshot/DeepSeek/GLM reject.

**Our fix:** The custom proxy (`opencode-proxy.py`) detects assistant messages with `tool_calls` but no `reasoning_content`, and injects a minimal placeholder (the original thinking content if available, otherwise `.`). This satisfies the provider's validation while preserving the conversation flow.

---

## Troubleshooting

### `404 Not Found` from OpenCode

You see the OpenCode HTML 404 page in error logs. **Apply the critical fix above.**

### `Connection refused` to localhost:8000

LiteLLM takes ~5–10 seconds to fully initialize. Wait a moment, or check logs:

```bash
docker logs -f litellm-opencode
```

### Claude Code says "No models available"

Ensure `ANTHROPIC_BASE_URL` ends with `/anthropic` (not `/anthropic/`):

```bash
export ANTHROPIC_BASE_URL=http://localhost:38765/anthropic
```

### API key errors

Verify your `.env` file is loaded and the key is valid:

```bash
curl https://opencode.ai/zen/go/v1/models \
  -H "Authorization: Bearer $OPCODE_API_KEY"
```

### Reset everything

```bash
docker compose down -v
docker compose up -d --build
```

---

## Advanced: Using the OpenAI SDK Directly

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:38765/anthropic",  # Note: /anthropic path
    api_key="dummy"
)

response = client.chat.completions.create(
    model="kimi-k2.6",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=1000
)

print(response.choices[0].message.content)
```

---

## Project Structure

```
.
├── .env                         # Your API key (not committed)
├── .env.example                 # Template for .env
├── .gitignore                   # Ignores .env
├── .mcp.json                    # MCP server config for Claude Code
├── aliases.zsh                  # Shell aliases for Claude Code models
├── Caddyfile                    # Reverse proxy rules
├── config.yaml                  # LiteLLM model configuration (fallback)
├── docker-compose.yml           # Docker services
├── Dockerfile.proxy             # Custom proxy image
├── opencode-proxy.py            # Custom Anthropic→OpenAI proxy with reasoning fix
├── README.md                    # This file
└── script.py                    # Example OpenAI SDK usage
```

---

## Known limitations

- Streaming responses use a simplified Anthropic event translation and have not been verified end to end. Non-streaming requests are the tested path.
- The proxy is stateless and forwards requests to the OpenCode endpoint with your API key; keep it on localhost or behind your own network controls.
- The model list reflects the OpenCode Go Plan at the time of writing and may change.

---

## License

MIT — use at your own risk. This is an unofficial bridge and not affiliated with Anthropic or OpenCode.
