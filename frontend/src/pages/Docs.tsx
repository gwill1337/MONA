import { useEffect, useState } from "react";
import {
  A,
  Availability,
  Callout,
  Code,
  CodeBlock,
  H3,
  P,
  RowTh,
  Section,
  Steps,
  TableWrap,
  Tabs,
  Td,
  Th,
} from "../components/docs/ui";
import { snippets } from "../components/docs/snippets";

// ─── Table of contents ───────────────────────────────────────────────────────

const SECTIONS = [
  { id: "deployment", label: "Deployment" },
  { id: "node-exporter", label: "Node exporter" },
  { id: "exporters", label: "Other exporters" },
  { id: "connect", label: "Connect a device" },
  { id: "links", label: "Links and ports" },
  { id: "ml", label: "How ML works" },
  { id: "modes", label: "Auto and Manual" },
  { id: "thresholds", label: "Anomaly thresholds" },
  { id: "ops", label: "Troubleshooting" },
] as const;

const SECTION_IDS: readonly string[] = SECTIONS.map((s) => s.id);

function useActiveSection(ids: readonly string[]) {
  const [active, setActive] = useState(ids[0]);

  useEffect(() => {
    const els = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);
    if (els.length === 0 || !("IntersectionObserver" in window)) return;

    const visible = new Set<string>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.add(entry.target.id);
          else visible.delete(entry.target.id);
        }
        const first = ids.find((id) => visible.has(id));
        if (first) setActive(first);
      },
      { rootMargin: "-10% 0px -70% 0px" },
    );

    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [ids]);

  return active;
}

// ─── Links data ──────────────────────────────────────────────────────────────

interface LinkRow {
  name: string;
  note?: string;
  port: number;
  path: string;
  terraform: boolean;
  compose: boolean;
}

const LINKS: LinkRow[] = [
  { name: "Web UI", note: "Admin panel", port: 30081, path: "/", terraform: true, compose: true },
  { name: "Dashboard", note: "Metrics and anomalies", port: 30081, path: "/dashboard", terraform: true, compose: true },
  { name: "Userboard", port: 30081, path: "/userboard", terraform: true, compose: true },
  { name: "Swagger", note: "Interactive API reference", port: 30080, path: "/docs", terraform: true, compose: true },
  { name: "Prometheus, devices", note: "Targets scraped by MONA", port: 30391, path: "/", terraform: true, compose: true },
  { name: "Metrics", note: "FastAPI /metrics", port: 30080, path: "/metrics", terraform: true, compose: true },
  { name: "Grafana", note: "Dashboards and Loki logs", port: 30300, path: "/", terraform: true, compose: false },
  { name: "Prometheus, cluster", note: "Pods and nodes", port: 30091, path: "/", terraform: true, compose: false },
];

// ─── Exporters data ──────────────────────────────────────────────────────────

const EXPORTERS = [
  { target: "Linux, macOS, BSD", name: "node_exporter", href: "https://github.com/prometheus/node_exporter", port: "9100", note: "The default for MONA" },
  { target: "Windows", name: "windows_exporter", href: "https://github.com/prometheus-community/windows_exporter", port: "9182", note: "MSI installer, runs as a service" },
  { target: "Routers, switches, UPS, printers", name: "snmp_exporter", href: "https://github.com/prometheus/snmp_exporter", port: "9116", note: "Anything that speaks SNMP" },
  { target: "Server hardware sensors", name: "ipmi_exporter", href: "https://github.com/prometheus-community/ipmi_exporter", port: "9290", note: "iDRAC, iLO and other BMCs" },
  { target: "Docker containers", name: "cAdvisor", href: "https://github.com/google/cadvisor", port: "8080", note: "CPU and memory per container" },
  { target: "HTTP, TCP and ping checks", name: "blackbox_exporter", href: "https://github.com/prometheus/blackbox_exporter", port: "9115", note: "Probes a target, like SNMP" },
  { target: "NVIDIA GPUs", name: "dcgm-exporter", href: "https://github.com/NVIDIA/dcgm-exporter", port: "9400", note: "" },
  { target: "PostgreSQL", name: "postgres_exporter", href: "https://github.com/prometheus-community/postgres_exporter", port: "9187", note: "" },
  { target: "Redis", name: "redis_exporter", href: "https://github.com/oliver006/redis_exporter", port: "9121", note: "" },
] as const;

// ─── ML data ─────────────────────────────────────────────────────────────────

const POINT_PATH = [
  {
    title: "Collect",
    body: (
      <>
        Celery beat schedules a task. A Celery worker reads CPU and RAM for every
        device from Prometheus and stores them in the <Code>metrics</Code> table.
        Detection runs on a schedule, every 60 seconds by default.
      </>
    ),
  },
  {
    title: "Build features",
    body: (
      <>
        Each point carries CPU, RAM and how much both changed since the previous
        point (deltas). Deltas let the model catch sudden jumps, not only high
        values.
      </>
    ),
  },
  {
    title: "Score",
    body: (
      <>
        Isolation Forest isolates points with random splits. Unusual points need
        fewer splits, so they get a lower score. The model flags about 5% of
        points (<Code>CONTAMINATION = 0.05</Code>), even on a healthy machine.
      </>
    ),
  },
  {
    title: "Filter",
    body: (
      <>
        A flagged point survives only if its score is below{" "}
        <Code>SCORE_THRESHOLD = -0.05</Code>, and a combined CPU and RAM anomaly
        is dropped while both stay under 80%.
      </>
    ),
  },
  {
    title: "Save",
    body: (
      <>
        What is left goes to the <Code>anomalies</Code> table with the device,
        values, reason and score, and is available on the dashboard and through
        the API.
      </>
    ),
  },
];

const MODE_ROWS = [
  {
    label: "Training data",
    auto: "The most recent 50–500 points, a sliding window",
    manual: "A time range you choose",
  },
  {
    label: "Model storage",
    auto: "Not stored, rebuilt in memory",
    manual: "Saved in PostgreSQL with period, point count and a note",
  },
  {
    label: "Retraining",
    auto: "Before every detection, every 60 seconds by default",
    manual: "Only when you run training again",
  },
  {
    label: "Follows load changes",
    auto: "Yes, the window moves with the current load",
    manual: "No, it keeps judging by the period it learned",
  },
  {
    label: "Watch out for",
    auto: "A long problem fills the window and starts to look normal",
    manual: "Needs retraining after workload changes",
  },
  {
    label: "Use it when",
    auto: "You are getting started or the load changes over time",
    manual: "The load is regular and you can point at a healthy period",
  },
];

const THRESHOLDS = [
  {
    key: "CONTAMINATION = 0.05",
    title: "Share of points flagged",
    body: (
      <>
        Isolation Forest is told to expect up to 5% outliers, so it flags that
        share of points even when nothing is wrong. On its own this setting
        produces false alarms. It is the raw output that the next two filters
        clean up.
      </>
    ),
  },
  {
    key: "SCORE_THRESHOLD = -0.05",
    title: "Minimum strength",
    body: (
      <>
        A flagged point must score below −0.05, and lower means more unusual.
        Borderline points that only just crossed the line are discarded. The score
        is internal to the model: it is not a percentage, a probability or a
        severity.
      </>
    ),
  },
  {
    key: "CPU and RAM < 80%",
    title: "Quiet machines",
    body: (
      <>
        The model compares a point with the device’s own history, not with a
        healthy level. On an idle host a jump from 3% to 25% CPU is statistically
        rare but harmless. When both CPU and RAM stay under 80%, a combined
        anomaly is ignored.
      </>
    ),
  },
];

// ─── Page ────────────────────────────────────────────────────────────────────

export default function Docs() {
  const active = useActiveSection(SECTION_IDS);
  const host = window.location.hostname || "localhost";

  return (
    <div className="relative flex min-h-screen flex-col bg-black font-sans text-white md:flex-row">

      <main className="w-full min-w-0 flex-1 px-6 py-10">
        <div className="mx-auto mt-5 max-w-6xl">
          {/* ── Header ── */}
          <header className="mb-10 mt-2">
            <h1 className="text-3xl font-bold tracking-tight text-white">
              Documentation
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Deployment, connecting devices and how anomaly detection works
            </p>
          </header>

          {/* ── Mobile contents ── */}
          <nav
            aria-label="Contents"
            className="-mx-6 mb-10 flex gap-2 overflow-x-auto px-6 pb-1 lg:hidden"
          >
            {SECTIONS.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="inline-flex h-9 shrink-0 items-center rounded-lg border border-slate-700/60 bg-slate-900/60 px-3 text-sm text-slate-300 transition-colors hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-500"
              >
                {s.label}
              </a>
            ))}
          </nav>

          <div className="flex items-start gap-12">
            {/* ── Content ── */}
            <div className="flex min-w-0 max-w-3xl flex-1 flex-col gap-16">
              {/* 1 ─ Deployment */}
              <Section
                id="deployment"
                title="Deployment"
                lead="MONA runs in two ways. Both give you the same API, Celery workers and web UI. They differ in the monitoring stack around them."
              >
                <TableWrap>
                  <thead>
                    <tr>
                      <Th />
                      <Th>Terraform and Helm</Th>
                      <Th>Docker Compose</Th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <RowTh>Best for</RowTh>
                      <Td>Full setup with cluster monitoring and alerts</Td>
                      <Td>A quick local run or a single host</Td>
                    </tr>
                    <tr>
                      <RowTh>Includes</RowTh>
                      <Td>
                        Everything in Compose, plus Grafana, Loki, Alertmanager
                        and the cluster Prometheus
                      </Td>
                      <Td>
                        API, Celery, PostgreSQL, Redis, web UI and the Prometheus
                        for devices
                      </Td>
                    </tr>
                    <tr>
                      <RowTh>Needs</RowTh>
                      <Td>Docker Desktop, kind, helm, Terraform</Td>
                      <Td>Docker Desktop</Td>
                    </tr>
                    <tr>
                      <RowTh>Config</RowTh>
                      <Td>
                        <Code>terraform.tfvars</Code>,{" "}
                        <Code>mona-chart/values.yaml</Code>
                      </Td>
                      <Td>
                        <Code>.env</Code>
                      </Td>
                    </tr>
                  </tbody>
                </TableWrap>

                <Tabs
                  label="Deployment method"
                  items={[
                    {
                      id: "terraform",
                      label: "Terraform",
                      content: (
                        <>
                          <Steps>
                            <li>
                              Install Docker Desktop, kind, helm and Terraform.
                            </li>
                            <li>
                              Run node exporter on every device you want to
                              monitor (see <A href="#node-exporter" external={false}>Node exporter</A>).
                            </li>
                            <li>Clone the repository.</li>
                            <li>
                              Copy <Code>terraform/terraform.tfvars.example</Code>{" "}
                              to <Code>terraform/terraform.tfvars</Code> and fill
                              in the admin and user accounts, PostgreSQL
                              settings, the Grafana password and, for alerts, the
                              Telegram bot token and chat ID.
                            </li>
                            <li>
                              Optional: list devices in{" "}
                              <Code>mona-chart/values.yaml</Code>, or add them
                              later in the Admin panel.
                            </li>
                            <li>
                              Optional: tune ML and rate limiter settings in{" "}
                              <Code>config.py</Code>.
                            </li>
                            <li>Deploy.</li>
                          </Steps>
                          <CodeBlock lang="bash" code={snippets.clone} />
                          <CodeBlock lang="powershell" title="Windows" code={snippets.deployWindows} />
                          <CodeBlock lang="bash" title="Linux and macOS" code={snippets.deployUnix} />
                          <Callout title="After changing code">
                            Images are built locally as <Code>mona-*:local</Code>{" "}
                            and loaded into the kind cluster on every apply. Run
                            build first, then deploy.
                          </Callout>
                        </>
                      ),
                    },
                    {
                      id: "compose",
                      label: "Docker Compose",
                      content: (
                        <>
                          <Steps>
                            <li>Install Docker Desktop.</li>
                            <li>
                              Run node exporter on every device you want to
                              monitor (see <A href="#node-exporter" external={false}>Node exporter</A>).
                            </li>
                            <li>Clone the repository.</li>
                            <li>
                              Copy <Code>.env.example</Code> to <Code>.env</Code>{" "}
                              and set <Code>POSTGRES_USER</Code>,{" "}
                              <Code>POSTGRES_PASSWORD</Code>,{" "}
                              <Code>POSTGRES_DB</Code> and{" "}
                              <Code>ADMIN_PASSWORDS</Code>. Compose refuses to
                              start without them.
                            </li>
                            <li>
                              Start the stack, then open the web UI on port{" "}
                              <Code>30081</Code>.
                            </li>
                          </Steps>
                          <CodeBlock lang="bash" code={snippets.clone} />
                          <CodeBlock lang="bash" title="Start" code={snippets.composeUp} />
                          <CodeBlock lang="bash" title="Stop" code={snippets.composeDown} />
                          <Callout title="No Grafana in Compose">
                            Compose has no Grafana, Loki, Alertmanager or cluster
                            Prometheus. Device monitoring and anomaly detection
                            work the same.
                          </Callout>
                        </>
                      ),
                    },
                  ]}
                />
              </Section>

              {/* 2 ─ Node exporter */}
              <Section
                id="node-exporter"
                title="Node exporter"
                lead="MONA reads CPU and RAM of each device from Prometheus, which scrapes an exporter on port 9100. Install one on every machine you want to monitor."
              >
                <Tabs
                  label="Operating system"
                  items={[
                    {
                      id: "linux",
                      label: "Linux",
                      content: (
                        <>
                          <H3>Package manager (Debian, Ubuntu)</H3>
                          <CodeBlock lang="bash" code={snippets.nodeLinuxApt} />
                          <H3>Binary with systemd (any distro)</H3>
                          <CodeBlock lang="bash" code={snippets.nodeLinuxBinary} />
                          <CodeBlock
                            lang="ini"
                            title="/etc/systemd/system/node_exporter.service"
                            code={snippets.nodeLinuxUnit}
                          />
                          <CodeBlock lang="bash" code={snippets.nodeLinuxEnable} />
                        </>
                      ),
                    },
                    {
                      id: "windows",
                      label: "Windows",
                      content: (
                        <>
                          <P>
                            Download the <Code>.msi</Code> from the{" "}
                            <A href="https://github.com/prometheus-community/windows_exporter/releases">
                              windows_exporter releases
                            </A>
                            . The installer registers a Windows service.
                          </P>
                          <CodeBlock lang="powershell" code={snippets.nodeWindows} />
                          <Callout kind="warn" title="Port 9100 instead of 9182">
                            windows_exporter listens on 9182 by default. The Admin
                            panel stores only a name and an IP, so keep the
                            exporter on 9100 as above. To stay on 9182, register
                            the device in <Code>values.yaml</Code> with that port.
                          </Callout>
                          <H3>Firewall and check</H3>
                          <P>
                            The installer may already open the port. To limit it
                            to your MONA host or subnet, add a scoped rule:
                          </P>
                          <CodeBlock lang="powershell" code={snippets.nodeWindowsFirewall} />
                          <CodeBlock lang="powershell" code={snippets.nodeWindowsVerify} />
                        </>
                      ),
                    },
                    {
                      id: "macos",
                      label: "macOS",
                      content: (
                        <>
                          <CodeBlock lang="bash" code={snippets.nodeMac} />
                          <Callout title="Reachable from other machines">
                            The Homebrew service may bind to{" "}
                            <Code>127.0.0.1</Code> only. Set the listen address
                            explicitly so Prometheus can reach it:
                          </Callout>
                          <CodeBlock lang="bash" code={snippets.nodeMacListen} />
                        </>
                      ),
                    },
                    {
                      id: "docker",
                      label: "Docker",
                      content: (
                        <>
                          <CodeBlock lang="bash" code={snippets.nodeDocker} />
                          <Callout kind="warn" title="Linux hosts only">
                            Docker Desktop on Windows and macOS runs containers in
                            a VM, so this reports the VM, not your machine. Use
                            the native install there.
                          </Callout>
                        </>
                      ),
                    },
                  ]}
                />

                <H3>Check that it works</H3>
                <CodeBlock lang="bash" code={snippets.verifyMetrics} />
                <P>
                  You should see lines starting with <Code># HELP</Code>. If the
                  request hangs, a firewall is in the way.
                </P>

                <H3>Open the port only to MONA</H3>
                <CodeBlock lang="bash" code={snippets.firewallLinux} />
                <Callout kind="warn" title="No authentication">
                  Exporters serve metrics to anyone who can reach them. Never
                  expose port 9100 to the internet, and allow only your MONA host
                  or LAN subnet.
                </Callout>
              </Section>

              {/* 3 ─ Other exporters */}
              <Section
                id="exporters"
                title="Other exporters"
                lead="Prometheus scrapes anything that serves metrics over HTTP. Servers, network gear and services plug in the same way: run an exporter, then register its host and port."
              >
                <TableWrap minWidth="min-w-[640px]">
                  <thead>
                    <tr>
                      <Th>Target</Th>
                      <Th>Exporter</Th>
                      <Th>Port</Th>
                      <Th>Notes</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {EXPORTERS.map((e) => (
                      <tr key={e.name}>
                        <RowTh>{e.target}</RowTh>
                        <Td>
                          <A href={e.href}>{e.name}</A>
                        </Td>
                        <Td>
                          <span className="font-mono tabular-nums">{e.port}</span>
                        </Td>
                        <Td>{e.note}</Td>
                      </tr>
                    ))}
                  </tbody>
                </TableWrap>

                <Callout title="What feeds anomaly detection">
                  Anomaly detection works on CPU and RAM. Data from other
                  exporters is visible in Prometheus and, with the Terraform
                  setup, in Grafana through the <Code>Prometheus-PC</Code> data
                  source.
                </Callout>

                <H3>Example: a network device over SNMP</H3>
                <P>
                  Run snmp_exporter once, then add one scrape job per device. The
                  job passes the device address to the exporter as a parameter.
                </P>
                <CodeBlock lang="bash" code={snippets.snmpRun} />
                <CodeBlock
                  lang="yaml"
                  title="scrape_configs"
                  code={snippets.snmpJob}
                />
                <P>
                  Add the job to <Code>prometheus/prometheus.yml</Code> for Docker
                  Compose, or to <Code>prometheus-configmap.yaml</Code> in the
                  Helm chart, then reload Prometheus without a restart:
                </P>
                <CodeBlock lang="bash" code={snippets.prometheusReload} />
              </Section>

              {/* 4 ─ Connect a device */}
              <Section
                id="connect"
                title="Connect a device"
                lead="Register a device in any of three ways. Each one ends up as a Prometheus target."
              >
                <Tabs
                  label="Registration method"
                  items={[
                    {
                      id: "admin",
                      label: "Admin panel",
                      content: (
                        <>
                          <Steps>
                            <li>Open the Admin panel and choose Add device.</li>
                            <li>Enter a name and the device IP.</li>
                            <li>
                              Wait for Prometheus to pick it up. The Helm setup
                              refreshes the list every 30 seconds.
                            </li>
                          </Steps>
                          <P>
                            Best for adding and removing devices on the fly. The
                            exporter must listen on port 9100.
                          </P>
                        </>
                      ),
                    },
                    {
                      id: "values",
                      label: "values.yaml",
                      content: (
                        <>
                          <P>
                            Best for adding many devices at deploy time and for
                            protecting them from accidental deletion. Each entry
                            has its own port, so it also fits windows_exporter on
                            9182.
                          </P>
                          <CodeBlock
                            lang="yaml"
                            title="mona-chart/values.yaml"
                            code={snippets.valuesYaml}
                          />
                          <P>Run the deploy again to apply it.</P>
                        </>
                      ),
                    },
                    {
                      id: "env",
                      label: "Compose .env",
                      content: (
                        <>
                          <P>
                            Optional list of <Code>jobName:host</Code> pairs
                            separated by commas. Leave it empty if you manage
                            devices in the Admin panel.
                          </P>
                          <CodeBlock lang="bash" title=".env" code={snippets.exportersEnv} />
                        </>
                      ),
                    },
                  ]}
                />

                <Callout kind="warn" title="Reachability">
                  The address must be reachable from the Prometheus pod or
                  container, not only from your laptop. Check routing and
                  firewalls between MONA and the device.
                </Callout>

                <H3>Check that the device is scraped</H3>
                <P>
                  Open Prometheus for devices, then Status and Targets. The
                  device should be <Code>UP</Code>. You can also read the list
                  MONA serves to Prometheus (no login needed):
                </P>
                <CodeBlock lang="bash" code={snippets.checkTargets} />
              </Section>

              {/* 5 ─ Links and ports */}
              <Section
                id="links"
                title="Links and ports"
                lead="Addresses use the host you opened this page from. Ports are the defaults from the Helm chart and the Compose file."
              >
                <TableWrap minWidth="min-w-[640px]">
                  <thead>
                    <tr>
                      <Th>Service</Th>
                      <Th>Address</Th>
                      <Th>Terraform</Th>
                      <Th>Compose</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {LINKS.map((l) => {
                      const label = `${host}:${l.port}${l.path === "/" ? "" : l.path}`;
                      return (
                        <tr key={l.name}>
                          <RowTh>
                            {l.name}
                            {l.note && (
                              <span className="mt-0.5 block text-xs font-normal text-slate-400">
                                {l.note}
                              </span>
                            )}
                          </RowTh>
                          <Td>
                            <A href={`http://${label}`}>
                              <span className="font-mono text-[13px]">{label}</span>
                            </A>
                          </Td>
                          <Td>
                            <Availability yes={l.terraform} />
                          </Td>
                          <Td>
                            <Availability yes={l.compose} />
                          </Td>
                        </tr>
                      );
                    })}
                  </tbody>
                </TableWrap>

                <P>
                  MONA has two Prometheus instances. The one for devices is part
                  of the product: it scrapes your exporters, and MONA reads CPU
                  and RAM from it. The cluster one watches pods and nodes and
                  exists only in the Terraform setup, together with Grafana.
                </P>
                <Callout title="Grafana access">
                  The Grafana admin password is the{" "}
                  <Code>grafana_admin_password</Code> value from{" "}
                  <Code>terraform.tfvars</Code>.
                </Callout>
              </Section>

              {/* 6 ─ How ML works */}
              <Section
                id="ml"
                title="How ML works"
                lead="MONA looks for unusual CPU and RAM behavior with Isolation Forest from scikit-learn. The model does not know what bad looks like. It learns what is usual for your devices and flags points that do not fit."
              >
                <H3>The path of a data point</H3>
                <ol className="relative ml-1 border-l border-slate-700/60">
                  {POINT_PATH.map((step, i) => {
                    const last = i === POINT_PATH.length - 1;
                    return (
                      <li key={step.title} className="relative pb-6 pl-6 last:pb-0">
                        <span
                          aria-hidden="true"
                          className={`absolute top-2 left-[-5.5px] size-2.5 rounded-full border ${
                            last
                              ? "border-cyan-500 bg-cyan-500"
                              : "border-slate-600 bg-black"
                          }`}
                        />
                        <p className="text-[15px] font-medium text-white">
                          <span className="mr-2 font-mono text-sm tabular-nums text-slate-400">
                            {i + 1}
                          </span>
                          {step.title}
                        </p>
                        <p className="mt-1 text-[15px] leading-7 text-slate-400">
                          {step.body}
                        </p>
                      </li>
                    );
                  })}
                </ol>
              </Section>

              {/* 7 ─ Auto and Manual */}
              <Section
                id="modes"
                title="Auto and Manual"
                lead="Auto needs no setup and follows the current load. Manual lets you fix a reference period and keep the model."
              >
                <TableWrap minWidth="min-w-[640px]">
                  <thead>
                    <tr>
                      <Th />
                      <Th>Auto</Th>
                      <Th>Manual</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {MODE_ROWS.map((r) => (
                      <tr key={r.label}>
                        <RowTh>{r.label}</RowTh>
                        <Td>{r.auto}</Td>
                        <Td>{r.manual}</Td>
                      </tr>
                    ))}
                  </tbody>
                </TableWrap>

                <H3>Training a model manually</H3>
                <P>
                  Training is an admin action and runs in Celery, so the API
                  answers right away. It needs at least 30 points in the chosen
                  range. Without a stored model MONA works in Auto mode. The
                  endpoints are listed in Swagger:
                </P>
                <ul className="flex flex-col gap-2 text-[15px] leading-7 text-slate-300">
                  <li>
                    <Code>POST /api/v1/train</Code> starts training for a time
                    range
                  </li>
                  <li>
                    <Code>GET /api/v1/task-status/{"{task_id}"}</Code> shows task
                    progress
                  </li>
                  <li>
                    <Code>GET /api/v1/model-info</Code> shows the stored model
                  </li>
                  <li>
                    <Code>DELETE /api/v1/model</Code> removes it
                  </li>
                </ul>
              </Section>

              {/* 8 ─ Thresholds */}
              <Section
                id="thresholds"
                title="Anomaly thresholds"
                lead="Isolation Forest always flags a fixed share of points, even on a healthy machine. Three rules turn that raw output into something worth looking at."
              >
                <dl className="divide-y divide-slate-800 rounded-xl border border-slate-700/40">
                  {THRESHOLDS.map((t) => (
                    <div
                      key={t.key}
                      className="grid gap-2 p-5 sm:grid-cols-[14rem_1fr] sm:gap-6"
                    >
                      <dt>
                        <code className="font-mono text-[13px] text-white">
                          {t.key}
                        </code>
                        <span className="mt-1 block text-xs text-slate-400">
                          {t.title}
                        </span>
                      </dt>
                      <dd className="text-[15px] leading-7 text-slate-300">
                        {t.body}
                      </dd>
                    </div>
                  ))}
                </dl>

                <H3>What counts as an anomaly</H3>
                <P>
                  A point the model flagged, whose score is below the threshold
                  and which was not dropped by the 80% rule.
                </P>
                <P>
                  Example: a quiet server idles at 3% CPU and 20% RAM. CPU jumps
                  to 25% for a minute. The model finds it unusual, but both values
                  are under 80%, so MONA drops it. If CPU reaches 95% while RAM
                  climbs to 85% and the score is below −0.05, MONA saves it.
                </P>

                <Callout title="Unusual is not broken">
                  An anomaly means the point differs from the learned pattern, not
                  that something failed. The absence of anomalies does not prove a
                  device is healthy either, so check that metrics are arriving.
                  ML settings live in <Code>config.py</Code>; set them before you
                  deploy.
                </Callout>
              </Section>

              {/* 9 ─ Troubleshooting */}
              <Section
                id="ops"
                title="Troubleshooting"
                lead="Common problems first, then the commands you will reach for."
              >
                <TableWrap minWidth="min-w-[640px]">
                  <thead>
                    <tr>
                      <Th>Symptom</Th>
                      <Th>What to check</Th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <RowTh>Target is DOWN in Prometheus</RowTh>
                      <Td>
                        Open <Code>http://&lt;device-ip&gt;:9100/metrics</Code>{" "}
                        from the MONA host. Check the firewall and that the
                        exporter listens on all interfaces, not only{" "}
                        <Code>127.0.0.1</Code>.
                      </Td>
                    </tr>
                    <tr>
                      <RowTh>Device added, no data</RowTh>
                      <Td>
                        Confirm the target is UP, then read the Celery worker and
                        Celery beat logs.
                      </Td>
                    </tr>
                    <tr>
                      <RowTh>Windows device not found</RowTh>
                      <Td>
                        windows_exporter uses port 9182. Reinstall with{" "}
                        <Code>LISTEN_PORT=9100</Code> or register it in{" "}
                        <Code>values.yaml</Code> with port 9182.
                      </Td>
                    </tr>
                    <tr>
                      <RowTh>No anomalies</RowTh>
                      <Td>
                        The model needs enough history. On idle machines the 80%
                        rule filters most spikes, which is expected.
                      </Td>
                    </tr>
                    <tr>
                      <RowTh>401 or 403</RowTh>
                      <Td>
                        401 means the session expired (it lasts 12 hours). 403
                        means the account is a user: users are read-only, and
                        adding devices or training needs an admin.
                      </Td>
                    </tr>
                    <tr>
                      <RowTh>Code changes do not show up</RowTh>
                      <Td>
                        With Terraform, rebuild the images, then deploy again. With
                        Compose, start with <Code>--build</Code>.
                      </Td>
                    </tr>
                  </tbody>
                </TableWrap>

                <Tabs
                  label="Runtime"
                  items={[
                    {
                      id: "k8s",
                      label: "Kubernetes",
                      content: (
                        <CodeBlock lang="bash" code={snippets.opsKubernetes} />
                      ),
                    },
                    {
                      id: "compose-ops",
                      label: "Docker Compose",
                      content: (
                        <CodeBlock lang="bash" code={snippets.opsCompose} />
                      ),
                    },
                  ]}
                />
              </Section>
            </div>

            {/* ── Desktop contents ── */}
            <nav
              aria-label="Contents"
              className="sticky top-10 hidden w-52 shrink-0 self-start lg:block"
            >
              <p className="mb-3 text-xs font-medium text-slate-400">
                On this page
              </p>
              <ul className="flex flex-col border-l border-slate-800">
                {SECTIONS.map((s) => {
                  const isActive = active === s.id;
                  return (
                    <li key={s.id}>
                      <a
                        href={`#${s.id}`}
                        aria-current={isActive ? "location" : undefined}
                        className={`-ml-px block border-l py-1.5 pl-4 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-500 ${
                          isActive
                            ? "border-white text-white"
                            : "border-transparent text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {s.label}
                      </a>
                    </li>
                  );
                })}
              </ul>
            </nav>
          </div>
        </div>
      </main>
    </div>
  );
}