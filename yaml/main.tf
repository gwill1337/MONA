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
  name            = "mona"
  node_image      = "kindest/node:v1.31.0"
  wait_for_ready  = true

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
        container_port = 30091
        host_port      = 30091
    }
    extra_port_mappings {
        container_port = 30300
        host_port      = 30300
    }
  }
}
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
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "postgres_password" {
  value     = random_password.postgres_password.result
  sensitive = true
}

output "kubeconfig_path" {
  value = kind_cluster.mona_cluster.kubeconfig_path
}