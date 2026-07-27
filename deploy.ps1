param (
    [switch]$Build,
    [switch]$Deploy,
    [switch]$All
)

if ($All -or $Build) {
    Write-Host "=== Building Docker images ===" -ForegroundColor Cyan
    docker build -t mona-fastapi:local -f ./docker/dockerfile.fastapi .
    docker build -t mona-react:local -f ./docker/dockerfile.react .
    docker build -t mona-celery:local -f ./docker/dockerfile.celery .
}

if ($All -or $Deploy) {
    Write-Host "=== Deploying infrastructure (Terraform) ===" -ForegroundColor Cyan
    terraform -chdir=terraform init
    terraform -chdir=terraform apply -auto-approve
}

if (-not $All -and -not $Build -and -not $Deploy) {
    Write-Host "Using: .\deploy.ps1 -All (Or -Build, or -Deploy)" -ForegroundColor Yellow
}