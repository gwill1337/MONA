$ErrorActionPreference = "Stop"

$deps = @("docker", "terraform", "kubectl", "helm", "kind")
foreach ($dep in $deps) {
    if (-not (Get-Command $dep -ErrorAction SilentlyContinue)) {
        Write-Error "$dep not found in PATH"
        exit 1
    }
}
Write-Host "Dependencies: OK"

Write-Host "Helm lint..."
helm lint ./../mona-chart

Push-Location ..\yaml

Write-Host "Terraform fmt..."
terraform fmt -check

Write-Host "Terraform validate..."
terraform validate

Pop-Location

if (Get-Command kubeconform -ErrorAction SilentlyContinue) {
    Write-Host "Kubeconform..."
    helm template ./../mona-chart | kubeconform -ignore-missing-schemas -
}

Push-Location ..\yaml

Write-Host "Deploying..."
terraform init
terraform apply -auto-approve

Pop-Location

Write-Host "Deployment complete."