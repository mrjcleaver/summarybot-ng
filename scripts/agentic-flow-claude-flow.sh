#!/usr/bin/env bash
set -euo pipefail

# --- Load repo env ---
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY not set}"

PROXY_PORT="${AGENTIC_FLOW_PROXY_PORT:-3000}"
PROXY_URL="http://localhost:${PROXY_PORT}"
DEFAULT_MODEL="${AGENTIC_FLOW_DEFAULT_MODEL:-openai/gpt-4o-mini}"
LOG_FILE="${AGENTIC_FLOW_PROXY_LOG:-/tmp/agentic-flow-proxy.log}"
#AGENTIC_FLOW_LOG_LEVEL="${AGENTIC_FLOW_LOG_LEVEL:-info}"


# Claude Code/claude-flow will talk to this (Anthropic-compatible) endpoint
export ANTHROPIC_BASE_URL="${PROXY_URL}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-sk-ant-proxy-dummy-key}"

started_proxy=0
proxy_pid=""

# Health check should match Anthropic-compatible surface
healthcheck() {
  # Prefer a real endpoint
  if curl -fsS "${PROXY_URL}/v1/models" >/dev/null 2>&1; then
    return 0
  fi
  # Fallback: just check port is open
  (echo >/dev/tcp/localhost/"${PROXY_PORT}") >/dev/null 2>&1
}

start_proxy() {
  nohup agentic-flow proxy \
    --provider openrouter \
    --port "${PROXY_PORT}" \
    --model "${DEFAULT_MODEL}" \
    --trust-request-chat-template \
    > "${LOG_FILE}" 2>&1 &
  proxy_pid="$!"
  started_proxy=1
}

stop_proxy() {
  if [ "${started_proxy}" -eq 1 ] && [ -n "${proxy_pid}" ]; then
    kill "${proxy_pid}" >/dev/null 2>&1 || true
  fi
}

trap stop_proxy INT TERM EXIT

if healthcheck; then
  echo "✓ agentic-flow proxy already up at ${PROXY_URL}"
else
  echo "Starting agentic-flow proxy at ${PROXY_URL} (model: ${DEFAULT_MODEL})"
  start_proxy
fi

MAX_WAIT="${AGENTIC_FLOW_PROXY_WAIT:-30}"
echo "Waiting for proxy..."
for ((i=1; i<=MAX_WAIT; i++)); do
  if healthcheck; then
    echo "✓ Proxy is up"
    break
  fi
  sleep 1
done

if ! healthcheck; then
  echo "✗ Proxy not reachable after ${MAX_WAIT}s"
  echo "  Log: ${LOG_FILE}"
  tail -n 120 "${LOG_FILE}" || true
  exit 1
fi

exec npx -y claude-flow@alpha "$@"