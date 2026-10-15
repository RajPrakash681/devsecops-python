#!/usr/bin/env bash
# Sample the backend HPA every 15 s for $1 seconds (default 300): CPU vs target, desired/current replicas, ready pods.
#   ./scripts/hpa-watch.sh 450
end=$((SECONDS + ${1:-300}))
printf "%-8s %-10s %-9s %-9s %s\n" TIME CPU/TARGET DESIRED CURRENT READY-PODS
while [ $SECONDS -lt $end ]; do
  read cpu desired current <<<"$(kubectl get hpa clinicflow-backend -n clinicflow -o jsonpath='{.status.currentMetrics[0].resource.current.averageUtilization} {.status.desiredReplicas} {.status.currentReplicas}')"
  ready=$(kubectl get pods -n clinicflow -l app.kubernetes.io/name=clinicflow-backend --no-headers 2>/dev/null | awk '$2=="1/1"' | wc -l | tr -d ' ')
  printf "%-8s %-10s %-9s %-9s %s\n" "$(date +%H:%M:%S)" "${cpu:-?}%/60%" "$desired" "$current" "$ready"
  sleep 15
done
