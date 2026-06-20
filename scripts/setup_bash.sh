#!/bin/bash
set -e

check_deps() {
  for cmd in docker terraform kubectl helm; do
    if ! command -v $cmd &> /dev/null; then
      echo "❌ $cmd не найден"
      exit 1
    fi
  done
  echo "✅ All dependencies found"
}

lint() {
  echo "🔍 Checking Helm chart..."
  helm lint ./mona-chart

  echo "🔍 Rendering templates..."
  helm template ./mona-chart | kubeconform -

  echo "🔍 Checking Terraform..."
  cd yaml
  terraform fmt -check
  terraform validate
  cd ..

  echo "✅ All checks passed"
}

deploy() {
  echo "🚀 Starting deployment..."
  cd yaml
  terraform init
  terraform apply -auto-approve
}

check_deps
lint
deploy