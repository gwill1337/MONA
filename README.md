# MONA - Monitor & Analytics Tool

## About
MONA is a K8s-based monitoring and analytics tool managed with Terraform and Helm. It collects and analyzes system metrics, built on Python with Celery and Redis as a task broker for metrics collection and ML workloads. FastAPI serves as the REST API/backend, React + Tailwind v4 + TypeScript handles web UI frontend, and PostgreSQL stores all metrics data.


## Quick Start:
1. Ensure [**Docker Desktop**](https://www.docker.com/products/docker-desktop/), [**kind**](https://github.com/kubernetes-sigs/kind), [**helm**](https://helm.sh/) and [**Terraform**](https://developer.hashicorp.com/terraform/install) are installed.
2. Set up node-exporter on the device you want to monitor.
3. Clone repo `git clone https://github.com/gwill1337/MONA.git`
4. Configure the necessary values in "mona-chart/[values](https://github.com/gwill1337/MONA/blob/main/mona-chart/values.yaml)" and "mona-chart/[values-prod](https://github.com/gwill1337/MONA/blob/main/mona-chart/values-prod.yaml)". *such as PC's IP & name or just add them via **Admin panel***
5. Create `terraform.tfvars` in terraform folder and paste variables or paste them directly after `terraform apply`:
```tfvars
telegram_bot_token = "your_bot_token"
telegram_chat_id   = your_id
admin_username     = "your_username"
admin_password     = "your_password"
```
6. Deploy: Run the automated script *requires [**kubeconform**](https://github.com/yannh/kubeconform#Installation)*:
```bash
   # From the /scripts folder
   ./setup_bash.sh # or setup_ps.ps1
```
*For manual deployment, use terraform init && terraform apply inside the /terraform folder.*

## Usage
**Links below are available after setup.**
### Main links:
* **Admin panel:** `localhost:30081/admin` *Default username: admin, password: admin123*
* **Dashboards:** `localhost:30081/admin/dashboard`
* **Grafana:** `localhost:30300/` *Default username: admin, password: admin123*
* **Prometheus:** `localhost:30091/`

<details>
<summary><b>Click to view detailed API endpoints</b></summary>

### API:
*P.S. All endpoint require authentification except prometheus and probes.*
* Swagger: `localhost:30080/docs`
* Main-metrics[Get]: `localhost:30080/db-metrics`
* Prometheus targets[Get]: `localhost:30080/api/prometheus/targets`
* Anomalies[Get]: `localhost:30080/anomalies`
* Model-info[Get]: `localhost:30080/model-info`
* Devices[Get]: `localhost:30080/devices`
* Devices[Post]: `localhost:30080/devices` *available via curl*
* Devices[Delete]: `localhost:30080/devices/{device_id}` *available via curl*
* Train[Post]: `localhost:30080/train` *available via curl*
* Model[Delete]: `localhost:30080/model` *available via curl*
* Dashboard[Get]: `localhost:30080/api/dashboard`
#### Probes:
* Liveness[Get]: `localhost:30080/health/live`
* Readiness[Get]: `localhost:30080/health/ready`

#### Authentication:
* Login[Post]: `localhost:30080/api/auth/login`
* Logout[Post]: `localhost:30080/api/auth/logout`
* Check auth[Get]: `localhost:30080/api/auth/me`

</details>

![admin panel](https://github.com/gwill1337/Images/blob/main/MONA/admin.gif)

## About cluster & pods
The infrastructure is managed using Terraform and Helm. The Kubernetes cluster consists of a control-plane node running the following core workloads.    
Helm templates for flexible and fast setup can be configured in [values](https://github.com/gwill1337/MONA/blob/main/mona-chart/values.yaml), and [values-prod](https://github.com/gwill1337/MONA/blob/main/mona-chart/values-prod.yaml).

* **API Engine:** FastAPI endpoints for handling client requests.   
* **Task Queue:** Celery workers with a Redis broker for background metrics collection and ML tasks.   
* **Database:** PostgreSQL for storing metrics and analytics data.   
* **Monitoring Stack:** **Prometheus** for data scraping, **Grafana** for visualization (Recharts is also used in the web UI), Alertmanager for pod alert notifications, and **Loki** with **Promtail** for pod logs.   

![dashboard](https://github.com/gwill1337/Images/blob/main/MONA/dashboard.gif)

## ML
* **ML:** Mona uses Scikit-learn for anomaly detection.
* **Training:** The model uses **Isolation Forest** and builds features with deltas for more accurate anomaly detection.

### Model has 2 modes
1. **Auto:** Takes between 50 and 500 of the most recent data points and trains the model on the fly. The model is not stored in the database and retrains before each detection (every 60 seconds by default).
2. **Manual:** Uses a time range specified by the user. The trained model is stored in the database.


## PostgreSQL
Postgres runs as a `StatefulSet`, which provides stable pod identifiers, persistent storage linked to specific pods, and ordered deployment for stateful applications.   
For detailed information about the tables, see [db.py](https://github.com/gwill1337/MONA/blob/main/mona_core/db.py).

### Postgres has 5 tables:
* **devices:** stores devices.
* **metrics:** stores collected metrics from the monitored device.
* **anomalies:** stores detected anomalies.
* **trained_models:** stores trained models.
* **admin_users:** stores admin users.

and can be opened via psql:
```bash
kubectl exec -it statefulset/postgres-statefulset -n mona -- psql -U myuser -d mydb
#              ⬆ pod name                          ⬆ namespace    ⬆ Username ⬆ DB name
```

## Authentication
MONA uses a stateful, cookie-based authentication system backed by Redis to secure the admin panel and core API endpoints.

### Admin Setup
During deployment, the `seed_admin` function runs automatically on startup. It reads the **ADMIN_USERNAME** and **ADMIN_PASSWORD** environment variables (configured via your terraform.tfvars or Helm values) and provisions the initial admin account in the PostgreSQL database if it does not already exist.

### How It Works
* **Session Management:** Upon a successful POST request to `/api/auth/login`, FastAPI generates a cryptographically secure 32-byte session token.
* **Redis Storage:** This token is stored in the Redis broker with a 12-hour expiration time (`ex=43200`), linking the session to the admin's user ID.
* **Cookies:** The token is returned to the frontend as an `HttpOnly`, `Lax` cookie named `admin_session`. This ensures the token is automatically sent with subsequent requests while remaining protected from cross-site scripting (XSS) attacks.
* **Access Control:** Protected endpoints (such as dashboard data, device management, and ML training) are routed through an `admin_router` dependency. This checks Redis for a valid session matching the user's cookie. If the session is missing or expired, the API returns a `401 Unauthorized` error.
* **Logout:** Endpoint `/api/auth/logout` deletes the session key from Redis and clears the client's cookie.

P.S. Endpoints like `/health/live`, `/health/ready`, and Prometheus target metrics (`/api/prometheus/targets`) are intentionally excluded from authentication to allow seamless cluster monitoring.

## CI
Automated checks and docker build & push run on every push and pull request:

* **Terraform** — format and validation checks
* **Helm** — lint and Kubernetes schema validation via kubeconform
* **YAML** — lint for values and chart files
* **Python** — ruff (lint and format checks), MyPy (type checks), Pytest (Api tests)
* **Docker** - Docker build & Docker push using repo secrets

## Architecture
Here more about architecture and how mona works.

### ML
MONA's [**ML model**](https://github.com/gwill1337/MONA/blob/main/mona_core/ml.py) has `CONTAMINATION = 0.05` which means up to 5% of data points might be classified as anomalies, even if there are none.
To reduce false positive detections, the model is equipped with a limiter `SCORE_THRESHOLD = -0.05`.   
In other words, it discards anomalies that the model estimates at less than a 5% confidence threshold. To definitively rule out false positives, the model also ignores "combined anomalies" if CPU and RAM usage are below 80%.

### FastAPI
#### Config vs Admin Panel Device Management:
Managing monitored devices in MONA can be done in two ways to ensure flexibility:
1. Values.yaml: Ideal for bulk-adding devices during deployment and preventing accidental deletions. FastAPI reads these configurations and commits them to the database.
2. Admin Panel / API: Allows dynamically adding or removing devices on the fly via HTTP POST/DELETE requests.

Prometheus consistently scrapes a dedicated endpoint to fetch the most up-to-date list of devices from the database, seamlessly merging both approaches.

#### FastAPI & Celery:
To maintain a responsive REST API, heavy ML model training tasks are offloaded to Celery. Because these tasks are asynchronous, FastAPI implements a dedicated task-tracking endpoint using Redis to reliably monitor task status and return responses.

### deploy & liveness:
* **Init Containers:** FastAPI and Celery deployments use `busybox` init scripts to wait for the database to be fully operational before starting the pods.
* **Probes:** FastAPI includes two health-check endpoints for Kubernetes: one for Liveness (API health) and one for Readiness (Database connectivity).