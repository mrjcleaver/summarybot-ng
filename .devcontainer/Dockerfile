FROM mcr.microsoft.com/devcontainers/base:bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git pkg-config libffi-dev libssl-dev \
  && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip pipx \
  && pipx ensurepath
