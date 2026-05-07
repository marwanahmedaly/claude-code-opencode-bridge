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
LiteLLM Proxy (:8000)
    |
    v
https://opencode.ai/zen/go/v1/chat/completions
    |
    v
OpenCode Go Plan (kimi-k2.6, deepseek-v4-pro, etc.)
```

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/installation)
- An [OpenCode](https://opencode.ai) account with API access

---

## Quick Start

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd litellm-opencode-proxy
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

This starts two containers:
- `litellm-opencode` — The LiteLLM proxy (internal port `8000`)
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
source /home/marwan/litellm/aliases.zsh
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

### `config.yaml`

Defines the models and their upstream OpenCode endpoints. The `model_list` maps friendly names to OpenCode's API.

Key settings:
- `api_base: https://opencode.ai/zen/go/v1` — OpenCode's gateway
- `api_key: "os.environ/OPCODE_API_KEY"` — Reads key from env
- `drop_params: true` — Strips unsupported parameters to prevent errors

### `docker-compose.yml`

```yaml
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    environment:
      - OPCODE_API_KEY=${OPCODE_API_KEY}
      - LITELLM_USE_CHAT_COMPLETIONS_URL_FOR_ANTHROPIC_MESSAGES=true  # CRITICAL
    # ...
  proxy:
    image: caddy:2-alpine
    ports:
      - "38765:38765"
```

### `Caddyfile`

Routes `/anthropic/*` requests from Claude Code to the LiteLLM container:

```caddy
:38765
handle_path /anthropic/* {
    reverse_proxy litellm:8000
}
```

### `.mcp.json` (Optional)

Project-level MCP server config for Claude Code. Currently includes Context7 for documentation lookup.

---

## The Critical Fix

**If you see 404 errors or HTML responses from OpenCode**, LiteLLM is routing Anthropic `/v1/messages` to the unsupported OpenAI **Responses API** (`/v1/responses`) instead of **Chat Completions** (`/v1/chat/completions`).

**Fix:** Set this environment variable in `docker-compose.yml`:

```yaml
environment:
  - LITELLM_USE_CHAT_COMPLETIONS_URL_FOR_ANTHROPIC_MESSAGES=true
```

Then restart:

```bash
docker compose down && docker compose up -d
```

### Why This Happens

LiteLLM 1.82+ introduced experimental Anthropic passthrough that routes `openai/...` models to the OpenAI Responses API by default. OpenCode only supports Chat Completions. This flag forces LiteLLM to use the legacy (working) path.

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
├── .claude/
│   └── settings.local.json      # Claude Code project settings (model aliases)
├── .env                         # Your API key (not committed)
├── .env.example                 # Template for .env
├── .gitignore                   # Ignores .env
├── .mcp.json                    # MCP server config for Claude Code
├── aliases.zsh                  # Shell aliases for Claude Code models
├── Caddyfile                    # Reverse proxy rules
├── config.yaml                  # LiteLLM model configuration
├── config2.yaml                 # Alternative config (legacy)
├── docker-compose.yml           # Docker services
├── README.md                    # This file
└── script.py                    # Example OpenAI SDK usage
```

---

## License

MIT — use at your own risk. This is an unofficial bridge and not affiliated with Anthropic or OpenCode.
