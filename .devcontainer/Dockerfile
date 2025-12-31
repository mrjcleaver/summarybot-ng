FROM mcr.microsoft.com/devcontainers/base:bookworm

# System deps + Python tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git pkg-config libffi-dev libssl-dev ca-certificates \
    python3 python3-venv python-is-python3 pipx \
  && rm -rf /var/lib/apt/lists/*

# Node.js (install FIRST; provides both node + npm)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get update \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# pipx locations
ENV PIPX_BIN_DIR=/usr/local/bin
ENV PIPX_HOME=/opt/pipx

# Poetry via pipx (no PEP 668 issues)
RUN pipx install poetry

# CLIs (now using the NodeSource npm)
RUN npm install -g @anthropic-ai/claude-code agentic-flow@1.10.2
