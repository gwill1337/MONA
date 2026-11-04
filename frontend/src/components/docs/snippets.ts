// All snippets use String.raw so backslashes (PowerShell, line continuations)
// survive. Shell variables are written as $VER, never with braces, because
// "${" would start a template substitution.

export const snippets = {
  // ─── Deployment ───────────────────────────────────────────────────────────
  clone: String.raw`git clone https://github.com/gwill1337/MONA.git
cd MONA`,

  deployWindows: String.raw`.\deploy.ps1 -All       # build images and deploy
.\deploy.ps1 -Build     # images only
.\deploy.ps1 -Deploy    # Terraform only`,

  deployUnix: String.raw`make all       # build images and deploy
make build     # images only
make deploy    # Terraform only`,

  composeUp: String.raw`cp .env.example .env
docker compose -p mona-prod --env-file .env -f docker-compose.prod.yml up -d --build`,

  composeDown: String.raw`docker compose -p mona-prod -f docker-compose.prod.yml down       # keep data
docker compose -p mona-prod -f docker-compose.prod.yml down -v    # also delete volumes`,

  // ─── Node exporter ────────────────────────────────────────────────────────
  nodeLinuxApt: String.raw`sudo apt update && sudo apt install -y prometheus-node-exporter
sudo systemctl enable --now prometheus-node-exporter`,

  nodeLinuxBinary: String.raw`VER=1.12.0     # latest: github.com/prometheus/node_exporter/releases
ARCH=amd64     # arm64 for ARM servers and 64-bit Raspberry Pi OS
curl -LO https://github.com/prometheus/node_exporter/releases/download/v$VER/node_exporter-$VER.linux-$ARCH.tar.gz
tar xzf node_exporter-$VER.linux-$ARCH.tar.gz
sudo install -m 0755 node_exporter-$VER.linux-$ARCH/node_exporter /usr/local/bin/
sudo useradd --system --no-create-home --shell /usr/sbin/nologin node_exporter`,

  nodeLinuxUnit: String.raw`[Unit]
Description=Prometheus node exporter
After=network-online.target
Wants=network-online.target

[Service]
User=node_exporter
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target`,

  nodeLinuxEnable: String.raw`sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter`,

  nodeWindows: String.raw`# PowerShell as Administrator, in the folder with the downloaded MSI
msiexec /i .\windows_exporter-amd64.msi /qn --% LISTEN_PORT=9100 ENABLED_COLLECTORS=cpu,memory,logical_disk,net,os,system`,

  nodeWindowsFirewall: String.raw`New-NetFirewallRule -DisplayName "Exporter 9100" -Direction Inbound -Protocol TCP -LocalPort 9100 -Action Allow -RemoteAddress <allowed-cidr>`,

  nodeWindowsVerify: String.raw`curl.exe -s http://localhost:9100/metrics | Select-Object -First 5`,

  nodeMac: String.raw`brew install node_exporter
brew services start node_exporter`,

  nodeMacListen: String.raw`echo "--web.listen-address=:9100" > "$(brew --prefix)/etc/node_exporter.args"
brew services restart node_exporter`,

  nodeDocker: String.raw`docker run -d --name node-exporter --restart unless-stopped \
  --net host --pid host \
  -v /:/host:ro,rslave \
  quay.io/prometheus/node-exporter:latest \
  --path.rootfs=/host`,

  verifyMetrics: String.raw`curl -s http://<device-ip>:9100/metrics | head -n 5`,

  firewallLinux: String.raw`# ufw
sudo ufw allow from <allowed-cidr> to any port 9100 proto tcp

# firewalld
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="<allowed-cidr>" port port="9100" protocol="tcp" accept'
sudo firewall-cmd --reload`,

  // ─── Other exporters ──────────────────────────────────────────────────────
  snmpRun: String.raw`docker run -d --name snmp-exporter --restart unless-stopped \
  -p 9116:9116 prom/snmp-exporter:latest`,

  snmpJob: String.raw`- job_name: snmp-switch
  metrics_path: /snmp
  params:
    module: [if_mib]
    auth: [public_v2]
  static_configs:
    - targets: ["192.168.1.1"]       # the device itself
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: "<exporter-host>:9116"`,

  prometheusReload: String.raw`curl -X POST http://localhost:30391/-/reload`,

  // ─── Connect a device ─────────────────────────────────────────────────────
  valuesYaml: String.raw`global:
  externalPcExporters:
    - host: "10.0.0.8"
      port: 9100
      jobName: "pc-test"
    - host: "10.0.0.9"
      port: 9182          # windows_exporter default
      jobName: "pc-windows"`,

  exportersEnv: String.raw`EXPORTERS=pc-test:10.0.0.8,pc-2:10.0.0.9`,

  checkTargets: String.raw`curl -s http://localhost:30080/api/prometheus/targets`,

  // ─── Troubleshooting ──────────────────────────────────────────────────────
  opsKubernetes: String.raw`kubectl get pods -n mona
kubectl logs deploy/mona-fastapi -n mona --tail=100
kubectl logs deploy/celery-worker -n mona --tail=100
kubectl logs deploy/celery-beat -n mona --tail=100
kubectl rollout restart deploy/mona-fastapi -n mona

# PostgreSQL shell (use your postgres_user and postgres_db)
kubectl exec -it statefulset/postgres-statefulset -n mona -- psql -U myuser -d mydb

# Remove the whole cluster
terraform -chdir=terraform destroy`,

  opsCompose: String.raw`docker ps
docker logs -f mona-fastapi --tail 100
docker logs -f mona-celery-worker --tail 100
docker logs -f mona-celery-beat --tail 100
docker restart mona-fastapi

# PostgreSQL shell (use POSTGRES_USER and POSTGRES_DB from .env)
docker exec -it mona-postgres psql -U <POSTGRES_USER> -d <POSTGRES_DB>`,
} as const;