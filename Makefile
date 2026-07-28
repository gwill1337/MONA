.PHONY: all build deploy help

help:
	@echo "Usage: make [all|build|deploy]"
	@echo "  make build   - build Docker images"
	@echo "  make deploy  - deploy infrastructure (Terraform)"
	@echo "  make all     - build + deploy"

build:
	@echo "=== Building Docker images ==="
	docker build -t mona-fastapi:local -f ./docker/dockerfile.fastapi .
	docker build -t mona-react:local -f ./docker/dockerfile.react .
	docker build -t mona-celery:local -f ./docker/dockerfile.celery .

deploy:
	@echo "=== Deploying infrastructure (Terraform) ==="
	terraform -chdir=terraform init
	terraform -chdir=terraform apply -auto-approve

all: build deploy