# MONA - Monitor & Analytics Tool

## About
This tool offers - K8s cluster with Terraform and helm that monitor and analytic metrics.    
Besides that its work on Python and uses Celery with Redis as broker for tasks like collect metrics or ML. Fast API as endpoints. Plotly for graphics in WEB and PostgreSQL as DataBase for metrics.



## About cluster & pods
The infrastructure is managed using Terraform and Helm. The Kubernetes cluster consists of a Control-plane node running the following core workloads (12 pods in total):

* **API Engine:** FastAPI endpoints for handling client requests.   
* **Task Queue:** Celery workers with a Redis broker for background metrics collection and ML tasks.   
* **Database:** PostgreSQL for storing metrics and analytics data.   
* M**onitoring Stack:** Prometheus for data scraping, Grafana for visualization (Plotly is also used in the web UI), and Alertmanager for notifications.   


Postgres is a `Statefulset` that provides stable pod identifiers, persistent storage linked to specific pods, and ordered deployment for stateful applications.   

Cluster use **Helm** for templates that provides flexible and fast setup, and can be configured in [values](), and [values-prod]().
 
## Set Up

`Set up node-exporter on device that needs in monitoring.`   

Download [**Docker Desktop**](https://www.docker.com/products/docker-desktop/)   
Download [**kind**](https://github.com/kubernetes-sigs/kind)   
Download [**helm**](https://helm.sh/)   
Download [**Terraform**](https://developer.hashicorp.com/terraform/install)   
Clone repo ` `


### Seting Up:
Configure all info in "mona-chart/[values]()" and "mona-chart/[values-prod]()" if needed.


#### Setting Up with Script and Tests:
1. Download [**kubeconform**](https://github.com/yannh/kubeconform#Installation)
2. Run `setup_bash.sh` or `setup_ps.ps1` from folder [**scripts**]()


#### Setting UP manually:
1. Go to the folder [yaml]()
2. Run
```bash
    terraform init
    terraform apply
```

