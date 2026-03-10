#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
IMAGE="${OPENHANDS_DOCKER_IMAGE:-ghcr.io/openhands/agent-server:latest-python}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER_NAME="${CONTAINER_NAME:-evaluating-skills-agent-server}"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run \
  --name "$CONTAINER_NAME" \
  --rm \
  -p "${PORT}:8000" \
  -e LLM_API_KEY \
  -e LMNR_PROJECT_API_KEY \
  -e OTEL_EXPORTER_OTLP_ENDPOINT \
  -e OTEL_EXPORTER_OTLP_HEADERS \
  -e OTEL_SERVICE_NAME \
  -v "${REPO_ROOT}:/workspace/project/evaluating-skills-tutorial" \
  "$IMAGE"
