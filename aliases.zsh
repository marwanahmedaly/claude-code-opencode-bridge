#!/usr/bin/env zsh
# LiteLLM OpenCode Proxy — Claude Code Aliases
# Source this file in your .zshrc:
#   source /home/marwan/litellm/aliases.zsh

export ANTHROPIC_BASE_URL=http://localhost:38765/anthropic
export ANTHROPIC_API_KEY=dummy

# Generic: claude-opencode <model-name> [args...]
claude-opencode() {
  local model="$1"
  shift
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL="$model" \
  claude "$@"
}

# ── OpenAI-compatible models ──

# Moonshot AI — best overall
claude-kimi() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=kimi-k2.6 \
  claude "$@"
}

# Moonshot AI — fast
claude-kimi25() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=kimi-k2.5 \
  claude "$@"
}

# DeepSeek — reasoning
claude-deepseek() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=deepseek-v4-pro \
  claude "$@"
}

# DeepSeek — fast
claude-deepseek-flash() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=deepseek-v4-flash \
  claude "$@"
}

# Zhipu AI
claude-glm51() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=glm-5.1 \
  claude "$@"
}

claude-glm5() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=glm-5 \
  claude "$@"
}

# 01.AI
claude-mimo() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=mimo-v2.5-pro \
  claude "$@"
}

claude-mimo-fast() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=mimo-v2.5 \
  claude "$@"
}

# Alibaba Qwen
claude-qwen() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=qwen3.6-plus \
  claude "$@"
}

claude-qwen-fast() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=qwen3.5-plus \
  claude "$@"
}

# ── Anthropic-native models ──

# MiniMax
claude-minimax() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=minimax-m2.7 \
  claude "$@"
}

claude-minimax-fast() {
  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL \
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  ANTHROPIC_MODEL=minimax-m2.5 \
  claude "$@"
}
