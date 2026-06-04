# MONA - Monitor & Analytics Tool

## About
This tool offers - K8s cluster with helm that monitor and analytic metrics.    
Besides that its work on Python and uses Celery with Redis as broker for tasks like collect metrics or ML. Fast API as endpoints. Plotly for graphics in WEB and PostgreSQL as DataBase for metrics.

## About cluster & pods
Cluster uses 6 pods:
* Control-plane
* PostgreSQL
* Redis
* Fast API
* Celery/ ML
* Prometheus

Postgres is a `Statefulset` that provides stable pod identifiers, persistent storage linked to specific pods, and ordered deployment for stateful applications.   

Cluster use **Helm** for templates that provides flexible and fast setup, and can be configured in [values](), and [values-prod]().
 
## Set Up

`Set up node-exporter on device that needs in monitoring.`   

Download [Docker Desktop.](https://www.docker.com/products/docker-desktop/)   
Download [kind.](https://github.com/kubernetes-sigs/kind)   
Download [helm.](https://helm.sh/)   
Clone repo.


### Seting Up cluster:
Configure all info in "mona-chart/[values]()" and "mona-chart/[values-prod]()"


Create and set up cluster:
```bash
kind create cluster

helm upgrade --install mona .\mona-chart -n mona --create-namespace -f .\mona-chart\values.yaml -f .\mona-chart\values-prod.yaml

kubectl config set-context --current --namespace=mona
kubectl get pods

```

