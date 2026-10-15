{{- define "cf.name" -}}{{ .Release.Name }}{{- end -}}

{{- define "cf.labels" -}}
app.kubernetes.io/part-of: clinicflow
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{/* Selector labels for one component: include "cf.selector" (dict "ctx" . "component" "backend") */}}
{{- define "cf.selector" -}}
app.kubernetes.io/name: clinicflow-{{ .component }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
{{- end -}}

{{/* The image reference. An empty tag is an error: deploys must name the commit SHA. */}}
{{- define "cf.image" -}}
{{ .image.repository }}:{{ required (printf "%s.image.tag is required (the commit SHA to deploy)" .component) .image.tag }}
{{- end -}}

{{- define "cf.secretName" -}}
{{- if .Values.postgres.existingSecret -}}{{ .Values.postgres.existingSecret }}{{- else -}}{{ include "cf.name" . }}-db{{- end -}}
{{- end -}}

{{- define "cf.dbHost" -}}
{{- if .Values.postgres.enabled -}}{{ include "cf.name" . }}-postgres{{- else -}}{{ required "externalDatabase.host is required when postgres.enabled=false" .Values.externalDatabase.host }}{{- end -}}
{{- end -}}

{{- define "cf.podSecurity" -}}
runAsNonRoot: true
seccompProfile: { type: RuntimeDefault }
{{- end -}}

{{- define "cf.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities: { drop: ["ALL"] }
{{- end -}}
