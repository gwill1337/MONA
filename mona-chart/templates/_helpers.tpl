{{/*
Expand the name of the chart.
*/}}
{{- define "mona-chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "mona-chart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mona-chart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mona-chart.labels" -}}
helm.sh/chart: {{ include "mona-chart.chart" . }}
{{ include "mona-chart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mona-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mona-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mona-chart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mona-chart.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}


{{- define "mona.databaseUrl" -}}
postgresql://{{ .Values.postgres.auth.user }}:{{ .Values.postgres.auth.password }}@postgres:{{ .Values.postgres.service.port }}/{{ .Values.postgres.auth.db }}
{{- end -}}

{{- define "mona.redisUrl" -}}
redis://redis:{{ .Values.redis.service.port }}/0
{{- end -}}

{{- define "mona.prometheusServiceAccount" -}}
{{- printf "%s-prometheus-metrics" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "mona.prometheusClusterRole" -}}
{{- printf "%s-%s-prometheus-discovery" .Release.Namespace .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}