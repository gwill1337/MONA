terraform {
  required_version = ">= 1.0.0"
  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "0.6.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "2.17.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.6.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0.0"
    }
  }
}

# ─── providers ───────────────────────────────────────────────────────────────

provider "kind" {}

provider "helm" {
  kubernetes {
    host                   = kind_cluster.mona_cluster.endpoint
    cluster_ca_certificate = kind_cluster.mona_cluster.cluster_ca_certificate
    client_certificate     = kind_cluster.mona_cluster.client_certificate
    client_key             = kind_cluster.mona_cluster.client_key
  }
}

# ─── Resources ───────────────────────────────────────────────────────────────

resource "random_password" "postgres_password" {
  length  = 16
  special = false
}

resource "kind_cluster" "mona_cluster" {
  name           = "mona"
  node_image     = "kindest/node:v1.31.0"
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
      extra_port_mappings {
        container_port = 30080
        host_port      = 30080
      }
      extra_port_mappings {
        container_port = 30081
        host_port      = 30081
      }
      extra_port_mappings {
        container_port = 30082
        host_port      = 30082
      }
      extra_port_mappings {
        container_port = 30091
        host_port      = 30091
      }
      extra_port_mappings {
        container_port = 30300
        host_port      = 30300
      }
      extra_port_mappings {
        container_port = 30391
        host_port      = 30391
      }

    }
  }
}

# ─── Uploading images into Kind ────────────────────────────────────────────────

resource "null_resource" "kind_load_images" {

  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "kind load docker-image mona-fastapi:local mona-celery:local mona-react:local mona-mcp:local --name ${kind_cluster.mona_cluster.name}"
  }

  depends_on = [kind_cluster.mona_cluster]
}

# ─── Helm Releases ───────────────────────────────────────────────────────────

resource "helm_release" "loki_stack" {
  name             = "loki-stack"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "loki-stack"
  version          = "2.10.2"
  namespace        = "mona"
  create_namespace = true

  set {
    name  = "loki.enabled"
    value = "true"
  }
  set {
    name  = "promtail.enabled"
    value = "true"
  }
  set {
    name  = "grafana.enabled"
    value = "false"
  }
  set {
    name  = "grafana.sidecar.datasources.enabled"
    value = "false"
  }
  set {
    name  = "loki.isDefault"
    value = "false"
  }

  depends_on = [kind_cluster.mona_cluster]
}

resource "helm_release" "mona_app" {
  name             = "mona"
  chart            = "${path.module}/../mona-chart"
  namespace        = "mona"
  create_namespace = true

  values = [
    file("${path.module}/../mona-chart/values.yaml"),
    yamlencode({
      celeryWorker = {
        env = {
          EXPORTERS = var.exporters
        }
      }
    })
  ]

  set {
    name  = "fastapi.env.LOG_LEVEL_FASTAPI"
    value = var.LOG_LEVEL_FASTAPI
  }

  set {
    name  = "celeryBeat.env.LOG_LEVEL_CELERY_BEAT"
    value = var.LOG_LEVEL_CELERY_BEAT
  }

  set {
    name  = "celeryWorker.env.LOG_LEVEL_CELERY_WORKER"
    value = var.LOG_LEVEL_CELERY_WORKER
  }

  set {
    name  = "postgres.auth.user"
    value = var.postgres_user
  }
  set {
    name  = "postgres.auth.db"
    value = var.postgres_db
  }
  set {
    name  = "postgres.service.port"
    value = var.postgres_port
  }

  set {
    name  = "postgres.enabled"
    value = var.postgres_enabled
  }
  set_sensitive {
    name  = "postgres.external.url"
    value = var.external_postgres_url
  }
  set {
    name  = "migration.enabled"
    value = var.migration_enabled
  }
  set {
    name  = "redis.enabled"
    value = var.redis_enabled
  }
  set_sensitive {
    name  = "redis.external.url"
    value = var.external_redis_url
  }

  set {
    name  = "celeryWorker.env.WINDOW"
    value = var.window
  }

  set {
    name  = "celeryWorker.env.MIN_POINTS"
    value = var.min_points
  }

  set {
    name  = "celeryWorker.env.CONTAMINATION"
    value = var.contamination
  }

  set {
    name  = "celeryWorker.env.SCORE_THRESHOLD"
    value = var.score_threshold
  }

  set {
    name  = "fastapi.env.MAX_ATTEMPTS"
    value = var.max_attempts
  }

  set {
    name  = "fastapi.env.LOCKOUT_SECONDS"
    value = var.lockout_seconds
  }

  set {
    name  = "fastapi.env.SESSION_TTL"
    value = var.session_ttl
  }

  # set {
  #   name = "celeryWorker.env.EXPORTERS"
  #   value = replace(var.exporters, ",", "\\\\,")
  # }

  set_sensitive {
    name  = "postgres.auth.password"
    value = random_password.postgres_password.result
  }
  set_sensitive {
    name  = "fastapi.env.ADMIN_USERNAMES"
    value = replace(join(",", var.admin_username), ",", "\\,")
  }
  set_sensitive {
    name  = "fastapi.env.ADMIN_PASSWORDS"
    value = replace(join(",", var.admin_password), ",", "\\,")
  }
  set_sensitive {
    name  = "fastapi.env.USER_USERNAMES"
    value = replace(join(",", var.user_username), ",", "\\,")
  }
  set_sensitive {
    name  = "fastapi.env.USER_PASSWORDS"
    value = replace(join(",", var.user_password), ",", "\\,")
  }

  set_sensitive {
    name  = "kube-prometheus-stack.alertmanager.config.receivers[1].telegram_configs[0].bot_token"
    value = var.telegram_bot_token
  }
  set_sensitive {
    name  = "kube-prometheus-stack.alertmanager.config.receivers[1].telegram_configs[0].chat_id"
    value = var.telegram_chat_id
  }
  set_sensitive {
    name  = "kube-prometheus-stack.grafana.adminPassword"
    value = var.grafana_admin_password
  }

  depends_on = [
    helm_release.loki_stack,
    null_resource.kind_load_images
  ]
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "postgres_password" {
  value     = random_password.postgres_password.result
  sensitive = true
}

output "kubeconfig_path" {
  value = kind_cluster.mona_cluster.kubeconfig_path
}
