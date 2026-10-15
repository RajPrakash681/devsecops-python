#!/usr/bin/env bash
# Thin wrapper so the README commands read the same as the other scripts.
#   ./scripts/seed.sh                                   # docker compose  (http://localhost:8000)
#   API=http://clinicflow.local ./scripts/seed.sh       # through the Kubernetes Ingress
set -euo pipefail
exec python3 "$(dirname "$0")/seed.py"
