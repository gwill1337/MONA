# Configuration guide for v1.0.0

This guide covers the main options and flags for configuring MONA. There are two ways to run it: with Terraform (`terraform.tfvars`) or with Docker Compose (`.env`).

The first part shows the **minimal setup**, which is enough to start MONA. The second part describes **all options** in detail.

---

# Minimal setup

Only the required options are listed here. Everything else uses default values.

## Terraform

### 1. Create `terraform.tfvars`

From the root folder of the project, go to the `terraform` folder and copy the example file.

For bash (Linux):
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

For PowerShell (Windows):
```powershell
cd terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```

### 2. Fill in `terraform.tfvars`

```hcl
# Usernames and passwords (lists go in pairs by position)
admin_username = ["admin"]
admin_password = ["change_me"]
user_username  = ["user1"]
user_password  = ["change_me"]

# Physical PCs to monitor, format: jobName:host
exporters = "pc-home:10.0.0.10,pc-test:10.0.0.8"

# Postgres (the password is generated automatically)
postgres_user = "myuser"
postgres_db   = "mydb"
postgres_port = 5432

# Grafana
grafana_admin_password = "change_me"
```

Telegram alerts are optional. If `telegram_bot_token` and `telegram_chat_id` are empty, alerts are disabled.

### 3. Start

**Windows:**
```Powershell
.\deploy.ps1 -all # or .\deploy.ps1 -deploy
```

**Linux/MacOS:**
```makefile
make all
```
## Docker Compose

### 1. Create `.env`

Copy the example file to `.env` before running `docker-compose`.

For bash (Linux):
```bash
cp env.example .env
```

For PowerShell (Windows):
```powershell
Copy-Item env.example .env
```

### 2. Fill in `.env`

```env
# Postgres
POSTGRES_USER=myuser
POSTGRES_PASSWORD=change_me
POSTGRES_DB=mydb
POSTGRES_PORT=5432

# Usernames and passwords (lists go in pairs by position)
ADMIN_USERNAMES=admin
ADMIN_PASSWORDS=change_me
USER_USERNAMES=user1
USER_PASSWORDS=change_me

# Physical PCs to monitor, format: jobName:host
EXPORTERS=pc-home:10.0.0.10,pc-test:10.0.0.8
```

### 3. Start

```bash
docker compose -p mona-prod --env-file .env -f docker-compose.prod.yml up -d --build
```

---

# Full configuration

## Configuration `terraform.tfvars`

### ML settings

```hcl
window          = 500    # max number of points ML takes for one training
min_points      = 30     # min number of points needed to start training
contamination   = 0.05   # share of points ML treats as anomalies in one training (0.05 = 5%)
score_threshold = -0.05  # filter for false positives (see below)
```

`score_threshold` works like this: -1 is the strongest anomaly, and values close to 0 are the weakest. A point is reported only if its score is below the threshold. Move the value closer to -1 to get fewer alerts. Move it closer to 0 to get more alerts, including weak ones.

### Limiter settings

The limiter uses Redis to count failed login attempts.

```hcl
max_attempts    = 5      # max failed login attempts
lockout_seconds = 300    # how long the user is blocked after too many attempts (300 s = 5 min)
session_ttl     = 43200  # how long a login session lives (43200 s = 12 hours)
```

### Telegram alerts

```hcl
telegram_bot_token = ""  # token of your bot, you can get it from @BotFather
telegram_chat_id   = ""  # ID of the chat where the bot sends alerts
```

If both fields are empty, Telegram alerts are disabled.

### Usernames and passwords

```hcl
admin_username = ["admin", "admin2"]
admin_password = ["admin123", "test_123"]
user_username  = ["user1"]
user_password  = ["userpass1"]
```

Admins and users are separate lists. The username and password lists go in pairs by position: the first username gets the first password, and so on. Both lists must have the same length.

### Exporters

Comma-separated `jobName:host` pairs for physical PCs.

```hcl
exporters = "pc-home:10.0.0.10,pc-test:10.0.0.8,pc-test2:10.0.1.1"
```

### Postgres

The Postgres password is generated automatically during `terraform apply`, so you don't set it here.

```hcl
postgres_user = "myuser"
postgres_db   = "mydb"
postgres_port = 5432
```

### Grafana

```hcl
grafana_admin_password = "admin123"
```

### Log level

Possible values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. The default is `INFO`.

```hcl
LOG_LEVEL_FASTAPI       = ""
LOG_LEVEL_CELERY_BEAT   = ""
LOG_LEVEL_CELERY_WORKER = ""
```

### Postgres and Redis (built-in or external)

By default, MONA starts its own Postgres and Redis. If you want to use an external service, set the matching flag to `false` and fill in the URL. For external Postgres (Supabase, etc.) you need an IPv4 address.

```hcl
postgres_enabled      = true
external_postgres_url = ""
migration_enabled     = true
redis_enabled         = true
external_redis_url    = ""
```

- `postgres_enabled` and `redis_enabled`: `true` starts the built-in service, `false` uses the external URL.
- `external_postgres_url` and `external_redis_url`: connection strings for your own services. Used only when the flag above is `false`.
- `migration_enabled`: if `false`, Alembic migrations are not run when the infrastructure starts. This option works only in Terraform.

## Configuration `.env` for Docker Compose

The ML and limiter options work the same way as in `terraform.tfvars`, see the sections above.

### Log level

Possible values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. The default is `INFO`.

```env
LOG_LEVEL=INFO
```

### Postgres

Unlike Terraform, here you set the password yourself. Do not leave `changeme`.

```env
POSTGRES_USER=myuser
POSTGRES_PASSWORD=changeme
POSTGRES_DB=mydb
POSTGRES_PORT=5432
```

### ML settings

```env
window=500
min_points=30
contamination=0.05
score_threshold=-0.05
```

### Limiter settings

```env
max_attempts=5
lockout_seconds=300
session_ttl=43200
```

### External Postgres and Redis

By default, MONA uses the built-in Postgres and Redis. To use external services, uncomment these lines and fill in the URLs. For external Postgres (Supabase, etc.) you need an IPv4 address.

```env
#database_url=
#redis_url=
```

### Usernames and passwords

Separate several values with commas, for example `admin,admin2`. As in Terraform, the lists go in pairs by position.

```env
ADMIN_USERNAMES=admin
ADMIN_PASSWORDS=admin123
USER_USERNAMES=
USER_PASSWORDS=
```

### CORS

The list of addresses that are allowed to send requests to the API from a browser. Put the address of your frontend here.

```env
CORS_ORIGINS=["http://localhost:30081"]
```

### Exporters

Comma-separated `jobName:host` pairs for physical PCs.

```env
EXPORTERS=pc-office:10.0.0.8,pc-lab:10.0.0.9
```

---

# Security notes

- Change all default passwords (admins, users, Grafana, Postgres) before you deploy.
- Do not commit `terraform.tfvars` or `.env` to git. They contain secrets.