# Contributing to MONA

Thank you for considering contributing to MONA! This document provides guidelines and instructions for contributing code, reporting issues, and setting up your local development environment.

---

## Local Development Setup
Requirements:
* **Python 3.13+**
* [**uv**](https://github.com/astral-sh/uv) for packages
* **Docker Desktop** / **kind** / **helm** / **Terraform** for IaC


### 1. Clone the repository
```bash
git clone [https://github.com/gwill1337/MONA.git](https://github.com/gwill1337/MONA.git)
cd MONA
```

### 2. Install dependencies
```bash
uv sync --frozen --group dev
```

### 3. Set up pre-commit & pre-push hooks
```
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```


## Running Checks Manually
```bash
# Run pre-commit checks on all files
uv run pre-commit run --hook-stage pre-commit --all-files

# Run pre-push checks (Mypy & Pytest)
uv run pre-commit run --hook-stage pre-push --all-files

# Run tests directly with pytest
uv run pytest tests/
```

## MONA's dev build
For fust testing and preview use `docker-compose.dev.yml` with `Dockerfile.dev` and `.env.dev`
```bash
docker compose -p mona-dev --env-file dev/.env.dev -f dev/docker-compose.dev.yml up -d --build
```

## Workflow & Branching
### 1. Fork or Create a Branch
Always create a descriptive feature branch off the dev branch:
```bash
git checkout dev
git pull origin dev
git checkout -b feature/short-description
# or
git checkout -b fix/short-description
```
### 2. Commit Guidelines
* Keep commits atomic and focused.
* Write clear and concise commit messages.
* Do not use `--no-verify` to bypass Git hooks unless absolutely necessary.

### 3. Submitting a Pull Request (PR)
* Push your branch to GitHub and open a PR targeting the `dev` branch.
* Provide a concise description of your changes and reference any related issues.
* Ensure all automated GitHub Actions CI checks pass (Gitleaks, Checkov, Ruff, Mypy, Pytest, Docker Trivy scan).

## Coding Standards & Linting
* **Python:** Core code (`mona_core/`) must strictly pass `Ruff` (linting & formatting) and `Mypy` type checks. Test files are exempt from strict Ruff rules (e.g., `assert` statements).
* **Infrastructure:** Ensure Terraform files are formatted using `terraform fmt` and Helm charts pass `helm lint`.
* **Security:** Never commit real API keys, passwords, or secrets. `Gitleaks` will reject commits with hardcoded credentials.

## Reporting Bugs & Requesting Features
* Use **GitHub Issues** to report bugs or request new features.
* Include reproduction steps, environment details (OS, Docker version, etc.), and relevant logs when reporting bugs.