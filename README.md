# MONA - Monitor & Analytics Tool

## About
MONA is a K8s-based monitoring and analytics tool managed with Terraform and Helm. It collects and analyzes system metrics, built on Python with Celery and Redis as a task broker for metrics collection and ML workloads. FastAPI serves as the backend, Plotly handles web UI charts, and PostgreSQL stores all metrics data.



## About cluster & pods
The infrastructure is managed using Terraform and Helm. The Kubernetes cluster consists of a control-plane node running the following core workloads (12 pods in total).    
Helm templates for flexible and fast setup can be configured in [values](https://github.com/gwill1337/MONA/blob/main/mona-chart/values.yaml), and [values-prod](https://github.com/gwill1337/MONA/blob/main/mona-chart/values-prod.yaml).

* **API Engine:** FastAPI endpoints for handling client requests.   
* **Task Queue:** Celery workers with a Redis broker for background metrics collection and ML tasks.   
* **Database:** PostgreSQL for storing metrics and analytics data.   
* **Monitoring Stack:** **Prometheus** for data scraping, **Grafana** for visualization (Plotly is also used in the web UI), Alertmanager for notifications, and **Loki** with **Promtail** for pod logs.   

## ML
* **ML:** Mona uses Scikit-learn for anomaly detection.
* **Training:** The model uses **Isolation Forest** and builds features with deltas for more accurate anomaly detection.

### Model has 2 modes
1. **Auto:** Takes between 50 and 500 of the most recent data points and trains the model on the fly. The model is not stored in the database and retrains before each detection (every 60 seconds by default).
2. **Manual:** Uses a time range specified by the user. The trained model is stored in the database.


## PostgreSQL
Postgres runs as a `StatefulSet`, which provides stable pod identifiers, persistent storage linked to specific pods, and ordered deployment for stateful applications.   
For detailed information about the tables, see [db.py](https://github.com/gwill1337/MONA/blob/main/py/db.py).

### Postgres has 3 tables:
* **Metrics:** stores collected metrics from the monitored device.
* **Anomaly:** stores detected anomalies.
* **TrainedModel:** stores trained models.

 
## Set Up

`Set up node-exporter on the device you want to monitor.`   

Download [**Docker Desktop**](https://www.docker.com/products/docker-desktop/)   
Download [**kind**](https://github.com/kubernetes-sigs/kind)   
Download [**helm**](https://helm.sh/)   
Download [**Terraform**](https://developer.hashicorp.com/terraform/install)   
Clone the repo `git clone https://github.com/gwill1337/MONA.git`


### Setting Up:
Configure the necessary values in "mona-chart/[values](https://github.com/gwill1337/MONA/blob/main/mona-chart/values.yaml)" and "mona-chart/[values-prod](https://github.com/gwill1337/MONA/blob/main/mona-chart/values-prod.yaml)" if needed.


#### Setting Up with Script and Tests
1. Create `terraform.tfvars` in yaml folder and paste variables or paste them directly after `terraform apply`:
```tfvars
    telegram_bot_token = "your_bot_token"
    telegram_chat_id = your_id
```
2. Download [**kubeconform**](https://github.com/yannh/kubeconform#Installation)
3. Run `setup_bash.sh` or `setup_ps.ps1` from the [**scripts**](https://github.com/gwill1337/MONA/tree/main/scripts) folder


#### Setting UP manually:
1. Go to the [yaml](https://github.com/gwill1337/MONA/tree/main/yaml) folder
2. Create `terraform.tfvars` in yaml folder and paste variables or paste them directly after `terraform apply`:
```tfvars
    telegram_bot_token = "your_bot_token"
    telegram_chat_id = your_id
```
3. Run
```bash
    terraform init
    terraform apply
```

## Usage
After setup, the following are available:
* **FastApi endpoints:** `localhost:30080/docs`
* **Main DashBoard:** `localhost:30080/`
* **Grafana:** `localhost:30300/` (Default username: `admin`, password `admin123`)
* **Prometheus:** `localhost:30091/`
