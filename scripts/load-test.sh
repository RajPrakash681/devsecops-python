#!/usr/bin/env bash
# Sustained front-desk traffic so the request-rate / latency panels and the HPA have something to show.
#   API=http://clinicflow.local DURATION=300 CONCURRENCY=12 ./scripts/load-test.sh
# Without a hosts entry:  API=http://localhost HOST_HEADER=clinicflow.local ./scripts/load-test.sh
set -euo pipefail
API="${API:-http://localhost:8000}"; DURATION="${DURATION:-120}"; CONCURRENCY="${CONCURRENCY:-8}"
CURL=(curl -s -o /dev/null); [ -n "${HOST_HEADER:-}" ] && CURL+=(-H "Host: $HOST_HEADER")
TODAY=$(TZ=Asia/Kolkata date +%F)
echo "Load on $API for ${DURATION}s with $CONCURRENCY workers"
worker() {
  local end=$((SECONDS + DURATION))
  while [ $SECONDS -lt $end ]; do
    "${CURL[@]}" "$API/api/appointments?date=$TODAY"
    "${CURL[@]}" "$API/api/stats"
    "${CURL[@]}" "$API/api/doctors"
    "${CURL[@]}" "$API/api/doctors/1/slots?date=$TODAY"
    "${CURL[@]}" "$API/api/events?limit=20"
  done
}
for _ in $(seq "$CONCURRENCY"); do worker & done
wait
echo "done"
