#!/usr/bin/env bash
# From https://github.com/mrjcleaver/dev-context
# whereami - Detect where this shell script is running (Docker, Codespaces, macOS, etc.)

print_section() {
  echo ""
  echo "🧭 $1"
  echo "----------------------------------------"
}

detect_mac() {
  if [[ "$(uname)" == "Darwin" ]]; then
    echo "🍎 Running on macOS"
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
      echo "   Architecture: Apple Silicon (arm64)"
    else
      echo "   Architecture: Intel (x86_64)"
    fi
  fi
}

detect_mac_docker() {
  if [[ "$(uname -s)" == "Linux" ]] && [ -d "/Users" ] && mount | grep -q "/Users" ; then
    echo "🍎 Running in Docker on macOS (shared /Users volume detected)"
  fi
}

detect_docker() {
  if grep -qE '/docker|/lxc' /proc/1/cgroup; then
    echo "✅ Running inside a Docker container"
    CONTAINER_ID=$(cat /proc/self/cgroup | grep "docker" | sed 's/^.*\///' | head -n 1)
    echo "   Container ID: $CONTAINER_ID"
  fi
}

detect_devcontainer() {
  if [ -n "$REMOTE_CONTAINERS" ] || grep -qi "devcontainer" <<< "$HOSTNAME"; then
    echo "✅ Running in a VS Code Dev Container"
  fi
}

detect_codespaces() {
  if [ "$CODESPACES" = "true" ] || grep -qi "codespaces" <<< "$HOSTNAME"; then
    echo "✅ Running inside GitHub Codespaces"
  fi
}

detect_dind() {
  if [ -S /var/run/docker.sock ]; then
    docker info >/dev/null 2>&1 && echo "✅ Docker-in-Docker (dind) is enabled"
  fi
}

detect_wsl() {
  if grep -qEi "(Microsoft|WSL)" /proc/version &> /dev/null ; then
    echo "✅ Running inside WSL"
  fi
}

detect_host() {
  echo "🖥️ Host OS: $(uname -a)"
  echo "✅ Current user: $(whoami)"
  echo "📁 Current directory: $(pwd)"
  echo -n "🐳 Docker version: "
  docker --version 2>/dev/null || echo "Not available"
}

main() {
  echo "🔍 Detecting environment..."

  print_section "OS & Architecture"
  detect_mac
  detect_mac_docker
  detect_wsl

  print_section "Containerization"
  detect_docker
  detect_devcontainer
  detect_codespaces
  detect_dind

  print_section "System Info"
  detect_host
}

main
