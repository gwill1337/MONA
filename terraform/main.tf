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

# ─── Resources ──────────────────────────────────────────────────────────────────

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
    file("${path.module}/../mona-chart/values-prod.yaml"),
  ]

  set_sensitive {
    name  = "postgres.auth.password"
    value = random_password.postgres_password.result
  }
  set_sensitive {
    name  = "celeryWorker.env.DATABASE_URL"
    value = "postgresql://myuser:${random_password.postgres_password.result}@postgres:5432/mydb"
  }
  set_sensitive {
    name  = "fastapi.env.DATABASE_URL"
    value = "postgresql://myuser:${random_password.postgres_password.result}@postgres:5432/mydb"
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

  depends_on = [helm_release.loki_stack]
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "postgres_password" {
  value     = random_password.postgres_password.result
  sensitive = true
}

output "kubeconfig_path" {
  value = kind_cluster.mona_cluster.kubeconfig_path
}
