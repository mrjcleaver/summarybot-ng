FROM mcr.microsoft.com/devcontainers/base:bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git pkg-config libffi-dev libssl-dev \
    python3 python3-pip python3-venv python-is-python3 \
    nodejs npm \
  && rm -rf /var/lib/apt/lists/*

# pipx/poetry tooling
RUN python -m pip install --upgrade pip pipx \
  && pipx ensurepath

# CLIs (baked, cached)
RUN npm install -g @anthropic-ai/claude-code agentic-flow@1.10.2
