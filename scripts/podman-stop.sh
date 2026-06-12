#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
podman-compose -f docker-compose.podman.yml down
