# Monitoring - Prometheus + Grafana

Installed with the community **kube-prometheus-stack** chart: Prometheus Operator, Prometheus,
Alertmanager, Grafana, node-exporter and kube-state-metrics.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
kubectl create namespace monitoring
kubectl -n monitoring create secret generic grafana-admin \
  --from-literal=admin-user=admin --from-literal=admin-password="$(openssl rand -base64 18)"
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring -f monitoring/kube-prometheus-stack-values.yaml
```

The ClinicFlow chart then plugs itself in; nothing is configured by hand:

| Object (in `helm/clinicflow/templates/`) | Effect |
|---|---|
| `ServiceMonitor` | Prometheus scrapes `/metrics` on every backend pod every 15 s |
| `PrometheusRule` | availability alerts (backend down, 5xx ratio, p95 latency, HPA at max) and clinic alerts (no-show rate, waiting room, double-booking attempts) |
| `ConfigMap` labelled `grafana_dashboard: "1"` | Grafana's sidecar loads the **ClinicFlow** dashboard automatically |

UIs, through ingress-nginx (map the hostnames to 127.0.0.1 in `/etc/hosts`):

| URL | |
|---|---|
| http://prometheus.clinicflow.local/targets | scrape targets; `clinicflow-backend` should be UP |
| http://prometheus.clinicflow.local/alerts | the ClinicFlow alert rules |
| http://grafana.clinicflow.local/d/clinicflow | the dashboard. Password: `kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' \| base64 -d` |
