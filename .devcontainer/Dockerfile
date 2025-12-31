FROM mcr.microsoft.com/devcontainers/base:bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git pkg-config libffi-dev libssl-dev \
  && rm -rf /var/lib/apt/lists/*

# Node is typically provided by your feature; if not, install it here instead.
RUN npm install -g @anthropic-ai/claude-code agentic-flow@1.10.2

RUN python -m pip install --upgrade pip pipx \
  && pipx ensurepath
