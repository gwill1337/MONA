# MONA - Monitor & Analytics Tool
<div align="center">

![CI Pipeline](https://img.shields.io/badge/CI_Pipeline-Automated_Checks-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-844FBA?style=for-the-badge&logo=terraform&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

</div>

## About
MONA is a K8s-based monitoring and analytics tool managed with Terraform and Helm. It collects and analyzes system metrics, built on Python with Celery and Redis as a task broker for metrics collection and ML workloads. FastAPI serves as the REST API/backend, React + Tailwind v4 + TypeScript handles web UI frontend, and PostgreSQL stores all metrics data.


## Quick Start:
### Terraform:
1. Ensure [**Docker Desktop**](https://www.docker.com/products/docker-desktop/), [**kind**](https://github.com/kubernetes-sigs/kind), [**helm**](https://helm.sh/) and [**Terraform**](https://developer.hashicorp.com/terraform/install) are installed.
2. Set up node-exporter on the device you want to monitor with port 9100.
3. Clone repo `git clone https://github.com/gwill1337/MONA.git`
4. copy `terraform.tfvars` in terraform folder from `terraform.tfvars.example`.      

**For bash (Linux):**
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

**For PowerShell (Windows):**
```powershell
cd terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```
5. Deploy: Run the automated script:   

**For bash (Linux):**
```makefile
make all
```

**For PowerShell (Windows)::**
```Powershell
.\deploy.ps1 -all # or .\deploy.ps1 -deploy
```
*For manual deployment, use terraform init && terraform apply inside the /terraform folder.*

### Docker-compose (without grafana and alerting):
1. Ensure [**Docker Desktop**](https://www.docker.com/products/docker-desktop/) are installed.
2. Set up node-exporter on the device you want to monitor with port 9100.
3. Clone repo `git clone https://github.com/gwill1337/MONA.git`
4. Copy `.env.example` to `.env`    

**For bash (Linux):**
```bash
cp env.example .env
```

**For PowerShell (Windows):**
```powershell
Copy-Item env.example .env
```
1. Run the `docker-compose.prod.yml`:
```bash
docker compose -p mona-prod --env-file .env -f docker-compose.prod.yml up -d --build
```
*The Docker Compose version comes without Grafana, Prometheus (for the cluster), and Alertmanager.*

## Usage
**Links below are available after setup.**
### Main links:
* **Admin panel:** `localhost:30081/` *Default username: admin, password: see the config file (terraform.tfvars or .env)*
* **Dashboards:** `localhost:30081/dashboard`
* **Userboard:** `localhost:30081/userboard`
* **MCP:** `localhost:30081/mcp`
* **Docs:** `localhost:30081/docs`
* **Grafana:** `localhost:30300/` *Default username: admin, password: see the config file (terraform.tfvars)*
* **Prometheus(Monitoring devices):** `localhost:30391/`
* **Prometheus(Cluster):** `localhost:30091/`

<details>
<summary><b>Click to view detailed API endpoints</b></summary>

### API:
*P.S. All endpoint require authentification except prometheus and probes.*
* Swagger: `localhost:30080/docs`

#### Users:
* Users[Get]: `localhost:30080/api/v1/users`
* User[Post]: `localhost:30080/api/v1/user`
* User[Delete]: `localhost:30080/api/v1/user/{user_id}`
* UserChangePassword[Patch]: `localhost:30080/api/v1/user/change-password`
* UserChangeRole[Patch]: `localhost:30080/api/v1/user/{user_id}/role`

#### Devices:
* Devices[Get]: `localhost:30080/api/v1/devices`
* Devices[Post]: `localhost:30080/api/v1/devices`
* Devices[Delete]: `localhost:30080/api/v1/devices/{device_id}`

#### Model:
* Model-info[Get]: `localhost:30080/api/v1/model-info`
* Train[Post]: `localhost:30080/api/v1/train`
* Model[Delete]: `localhost:30080/api/v1/model`

#### Monitoring:
* Dashboard[Get]: `localhost:30080/api/v1/dashboard`
* TaskStatus[Get]: `localhost:30080/api/v1/task-status/{task_id}`
* Anomalies[Get]: `localhost:30080/api/v1/anomalies`
* Metrics[Get]: `localhost:30080/api/v1/db-metrics`

#### Authentication:
* Login[Post]: `localhost:30080/api/v1/auth/login`
* Logout[Post]: `localhost:30080/api/v1/auth/logout`
* Check auth[Get]: `localhost:30080/api/v1/auth/me`

#### Probes:
* Liveness[Get]: `localhost:30080/health/live`
* Readiness[Get]: `localhost:30080/health/ready`

#### Prometheus Endpoints:
* Metrics[Get]: `localhost:30080/metrics`
* Targets[Get]: `localhost:30080/api/prometheus/targets`
  
#### MCP:
* Create MCP Key[Post]: `localhost:30080/api/v1/mcp`
* MCP SSE: `localhost:30082/sse`

</details>

![admin panel](https://github.com/gwill1337/Images/blob/main/MONA/MONA_admin.gif)

## About cluster & pods
The infrastructure is managed using Terraform and Helm. The Kubernetes cluster consists of a control-plane node running the following core workloads.    
Helm templates for flexible and fast setup can be configured in [values](https://github.com/gwill1337/MONA/blob/main/mona-chart/values.yaml) and in terraform.tfvars.

* **API Engine:** FastAPI endpoints for handling client requests.   
* **MCP:** FastMCP provide access to anomalies, metrics, devices and models directly via the database for LLMs and Agents.
* **Task Queue:** Celery workers with a Redis broker for background metrics collection and ML tasks.   
* **PostgreSQL:** For storing metrics and analytics data.  
* **Redis:** As a broker for celery and as a storage for sessions and limiter. 
* **Monitoring Stack:** **Prometheus** for data scraping, **Grafana** for visualization (Recharts is also used in the web UI), Alertmanager for pod alert notifications, and **Loki** with **Promtail** for pod logs.   

![dashboard](https://github.com/gwill1337/Images/blob/main/MONA/MONA_dashboard.gif)

## ML
* **ML:** Mona uses Scikit-learn for anomaly detection.
* **Training:** The model uses **Isolation Forest** and builds features with deltas for more accurate anomaly detection.
* **Features:** Every point is described by 6 features: CPU and RAM values, their change from the previous sample (`d1`) and their change over the last 5 samples (`d5`, about 2.5 minutes with the default 30-second collector).
* **Gaps & offline periods:** Deltas are never calculated across a time gap longer than 90 seconds or across a switch between offline and online. Because of this, the first points after a device comes back are not treated as a sudden jump.
* **Zeros:** If Prometheus has no data for a device (for example, the device is offline), MONA stores `0.0` instead of skipping the point. Zeros stay in the database and on the charts, but a point where both CPU and RAM are zero is never reported as an anomaly.


### Model has 2 modes
1. **Auto:** Runs every 30 seconds and works per device. It takes the most recent `WINDOW` points (500 by default, at least `MIN_POINTS` = 30 clean points are required) and trains the model on the fly. The model is not stored in the database and retrains before each detection. Two kinds of points are never used for training:
   * the points being checked (the last 5 minutes);
   * the area around already detected anomalies: 5 minutes before and after each one, extended through the whole period while CPU or RAM stays above 80%.

2. **Manual:** Uses a time range specified by the user. The model is trained on all devices at once with the same cleaning of known anomalies as in Auto, and is stored in the database together with its scaler. At least 30 clean points are required. MONA keeps the 10 newest models (the active one is never removed). A trained model can be activated right away or later; while a model is active, detection uses it instead of Auto. If the stored model can't be loaded, detection falls back to Auto.

## PostgreSQL
Postgres runs as a `StatefulSet`, which provides stable pod identifiers, persistent storage linked to specific pods, and ordered deployment for stateful applications.   
For detailed information about the tables, see [db.py](https://github.com/gwill1337/MONA/blob/main/mona_core/db.py).

### Postgres has 5 tables:
* **devices:** stores devices.
* **metrics:** stores collected metrics from the monitored device.
* **anomalies:** stores detected anomalies.
* **trained_models:** stores trained models.
* **users:** stores users.
* **api_keys:** stores api keys for MCP authentication.

and can be opened via psql:
```bash
kubectl exec -it statefulset/postgres-statefulset -n mona -- psql -U myuser -d mydb
#              ⬆ pod name                          ⬆ namespace    ⬆ Username ⬆ DB name
```

![MCP](https://github.com/gwill1337/Images/blob/main/MONA/MONA_mcp.gif)

## MCP
MONA has an MCP server built with [FastMCP](https://github.com/jlowin/fastmcp). LLMs and agents can use it to read devices, metrics and anomalies, check the health of MONA, and start model training. The server works directly with the database, so it does not need the web UI.

The MCP server starts together with the rest of MONA, both in Terraform and in Docker Compose. You don't need to enable it.

### Connection
* **Transport:** SSE
* **URL:** `http://localhost:30082/sse`
* **Authentication:** API key, sent as a bearer token in the `Authorization` header.

API keys are stored in the `api_keys` table. A FastMCP middleware reads the bearer token from each request and checks it against this table. Requests without a valid key are rejected.

### Create API token
You can create an API key on the MCP page in MONA, or send a request directly to the endpoint `localhost:30080/api/v1/mcp`.

Example for Claude Code:
```bash
claude mcp add --transport sse mona http://localhost:30082/sse \
  --header "Authorization: Bearer <YOUR_API_KEY>"
```

Other MCP clients use a similar setup: give them the SSE URL and the `Authorization` header. The exact config format depends on the client.

### Configuration
The MCP server has no separate options in `terraform.tfvars`. In Docker Compose it takes the Postgres and Redis settings from `.env`, the same as the API. `LOG_LEVEL` sets its log level.

It also needs two internal addresses (already set in `docker-compose.prod.yml` and in the Helm chart):

* `MONA_API_URL` — address of the MONA API, used for the health check and for `get_prometheus_targets`.
* `PROMETHEUS_URL` — address of Prometheus that scrapes the monitored devices.

### Main Tools & Capabilities
* **get_mona_health:** Checks availability and health status of MONA API, PostgreSQL, Redis, and Prometheus services.
* **get_device_metrics:** Retrieves paginated CPU and RAM telemetry metrics for a specified device from PostgreSQL
* **get_mona_anomalies:** Fetches detected ML anomaly records with time range, device, and score filters from PostgreSQL.
* **train_anomaly_model:** Submits an asynchronous background task via Celery to train an Isolation Forest anomaly model.

<details>

<summary><b>Click to view Additional Tools</b></summary>

### Additional Tools

#### Tools

* **get_mona_devices:** Fetches the list of all monitored devices from the PostgreSQL database.
* **add_mona_device:** Registers a new device in the PostgreSQL database with duplicate checks.
* **remove_mona_device:** Deletes a device record from the PostgreSQL database by its IP address.
* **get_task_status:** Queries Celery/Redis for the current status of an asynchronous background task.
* **get_model_info:** Retrieves metadata for the active ML model and total count of stored models from PostgreSQL.
* **list_models:** Lists all saved, manually trained ML models from the PostgreSQL database.
* **activate_model:** Sets a specific stored model as active in the PostgreSQL database for anomaly detection.
* **deactivate_model:** Switches anomaly detection back to auto-mode by deactivating custom models in PostgreSQL.
* **get_prometheus_targets:** Fetches configured Prometheus scrape targets via MONA HTTP API.

#### Prompts
* **diagnose_mona:** Guides the AI through a full system health assessment using MCP tools.
* **investigate_anomaly:** Provides a step-by-step SRE workflow to investigate device anomalies using before/after metrics.

#### Resources
* **mona://docs/overview:** Provides architecture, component structure, and operational documentation.
* **mona://docs/metrics:** Contains detailed documentation on metric schemas, ML parameters, and anomaly rules.

</details>

![userboard](https://github.com/gwill1337/Images/blob/main/MONA/MONA_userboard.gif)
## Authentication & Authorization
MONA uses a stateful, cookie-based authentication system backed by Redis to secure the admin panel and core API endpoints.

### MCP Authentication:
MCP Authentication uses a middlewire in FastMCP to catch bearer token.

### Admin Setup
During deployment, the `seed_admin` function runs automatically on startup. It reads the **ADMIN_USERNAMES**,**ADMIN_PASSWORDS** and **USER_USERNAMES**,**USER_PASSWORDS** environment variables (configured via your terraform.tfvars or .env files) and provisions the initial user and admin accounts in the PostgreSQL database if it does not already exist.

* **Session Management:** Upon a successful POST request to `/api/auth/login`, FastAPI generates a cryptographically secure 32-byte session token.
* **Redis Storage:** This token is stored in the Redis broker with a 12-hour expiration time (`ex=43200`), linking the session to the user's ID.
* **Cookies:** The token is returned to the frontend as an `HttpOnly`, `Lax` cookie named `user_session`. This ensures the token is automatically sent with subsequent requests while remaining protected from cross-site scripting (XSS) attacks.
* **Access Control:** All protected endpoints — except health checks (`/health/live`, `/health/ready`) and Prometheus metrics (`/api/prometheus/targets`) — are routed through role-aware `user_router` / `admin_router` dependencies that validate the session token against Redis. **Users** are restricted to **GET** requests only, giving them read-only access to dashboards and device data, while **admins** have full access to all methods — `GET`, `POST`, `PUT`, `DELETE` — including device management and ML training endpoints. If the session is missing or expired, the API returns `401 Unauthorized`; if the session is valid but the account's role doesn't permit the requested method, it returns `403 Forbidden`.
* **Logout:** Endpoint `/api/auth/logout` deletes the session key from Redis and clears the client's cookie.

P.S. Endpoints like `/health/live`, `/health/ready`, and Prometheus target metrics (`/api/prometheus/targets`) are intentionally excluded from authentication to allow seamless cluster monitoring.

## CI
Automated checks and docker build & push run on every push and pull request:

* **Gitleaks:** — leaks scan
* **Checkov:** — IaC scan
* **Terraform** — format and validation checks
* **Helm** — lint for helm charts
* **YAML** — lint for values and chart files
* **Python** — ruff (lint and format checks), MyPy (type checks), Pytest (Api tests)
* **Docker** — scan images via Trivy

## Architecture
Here more about architecture and how **MONA** works.

### ML
MONA's [**ML model**](https://github.com/gwill1337/MONA/blob/main/mona_core/ml.py) has `CONTAMINATION = 0.05` which means up to 5% of data points might be classified as anomalies, even if there are none.
To reduce false positive detections, the model is equipped with a limiter `SCORE_THRESHOLD = -0.05`.   
In other words, it discards anomalies that the model estimates at less than a 5% confidence threshold. To definitively rule out false positives, the model also ignores "combined anomalies" if CPU and RAM usage are below 80%.

#### How detection works:
1. **Collect:** Every 30 seconds Celery queries Prometheus for CPU and RAM of every active device and saves a new metric point.
2. **Check:** Every 30 seconds the detector looks only at points from the last 5 minutes. Older points of the same device are the training history (Auto mode) or are ignored (Manual mode).
3. **Filter:** A point becomes an anomaly only if all of these are true:
   * the model marks it as an outlier and its score is below `SCORE_THRESHOLD`;
   * CPU and RAM are not both zero;
   * it is not a weak "combined anomaly" (both CPU and RAM below 80%);
   * it was not saved before (one anomaly per metric point).
4. **Explain:** Every anomaly is saved with its score and a reason: high usage (CPU or RAM above 85%), a sudden change between two samples (CPU more than 20% or RAM more than 15%), a change over 5 samples (CPU more than 30% or RAM more than 20%), or a combined anomaly if no single factor stands out.


### Dashboard
When a time range is selected (`hours` or `start` and `end`), the dashboard endpoint (`/api/v1/dashboard`) groups the metrics into time buckets for each device, and CPU and RAM are averaged inside every bucket. This keeps charts fast and readable on long ranges. The bucket size depends on the length of the range:
 
* up to 12 hours — 1 minute buckets
* more than 12 hours and less than 7 days — 10 minute buckets
* 7 days and more — 1 hour buckets
The number of returned metric points is limited by `max_points` (2000 by default, 10000 at most). Anomalies are returned as they are, without bucketing.


### FastAPI
#### Config vs Admin Panel Device Management:
Managing monitored devices in MONA can be done in two ways to ensure flexibility:
1. Values.yaml / terraform.tfvars / .env: Ideal for bulk-adding devices during deployment and preventing accidental deletions. FastAPI reads these configurations and commits them to the database.
2. Admin Panel / API: Allows dynamically adding or removing devices via HTTP POST/DELETE requests.

Prometheus consistently scrapes a dedicated endpoint to fetch the most up-to-date list of devices from the database, seamlessly merging both approaches.

#### FastAPI & Celery:
To maintain a responsive REST API, heavy ML model training tasks are offloaded to Celery. Because these tasks are asynchronous, FastAPI implements a dedicated task-tracking endpoint using Redis to reliably monitor task status and return responses.

### deploy & liveness:
* **Init Containers:** FastAPI and Celery deployments use `busybox` init scripts to wait for the database to be fully operational before starting the pods.
* **Probes:** FastAPI includes two health-check endpoints for Kubernetes: one for Liveness (API health) and one for Readiness (Database connectivity).
