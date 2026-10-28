from server import mcp


@mcp.resource("mona://docs/overview")
def get_mona_overview_documentation() -> str:
    """Provide architecture and operational context for MONA."""

    return """
        # MONA — Monitoring & Analytics

        ## Purpose
        MONA collects infrastructure metrics, monitors device health,
        visualizes telemetry and detects potentially anomalous behavior.

        ## Architecture
        - FastAPI: application API and backend logic.
        - PostgreSQL: persistent storage for devices, metrics,
        detected anomalies and trained models.
        - Redis: message broker and supporting task infrastructure.
        - Celery: asynchronous metric processing and ML tasks.
        - Prometheus: time-series monitoring and metric collection.
        - Grafana: dashboards and visualization.
        - Loki: log aggregation.
        - ML: Isolation Forest-based anomaly detection.
        - React: web interface.

        ## Data entities
        - Device: monitored device metadata.
        - Metric: CPU/RAM observations with device and timestamp.
        - Anomaly: detected event with metric values, reason and score.
        - TrainedModel: stored model and training metadata.

        ## Investigation principles
        - Use tools to retrieve current data instead of assuming it.
        - Compare measurements over explicit time windows.
        - Check timestamps, sample counts and missing data.
        - Distinguish observations from hypotheses.
        - Correlation does not prove causation.
        - Never invent missing measurements or claim a device is healthy
        based only on the absence of recorded anomalies.
            """


@mcp.resource("mona://docs/metrics")
def get_metrics_documentation() -> str:
    """Explain MONA metrics, anomaly detection and interpretation rules."""

    return """
        # MONA — Metrics & Anomaly Detection Documentation

        ## 1. Overview

        MONA collects infrastructure metrics and uses them for monitoring,
        visualization and anomaly detection.

        Metrics are stored in PostgreSQL and associated with monitored devices.
        Prometheus is used for metric collection and monitoring infrastructure.

        The primary application metrics currently used by the ML anomaly
        detection pipeline are CPU and RAM utilization.

        ## 2. Metric Schema

        ### Metric

        Each metric record contains:

        - id: Unique identifier of the metric record.
        - cpu: Recorded CPU utilization value.
        - ram: Recorded RAM utilization value.
        - device: Identifier or name of the monitored device.
        - timestamp: Time when the metric was recorded.

        Metrics are time-series observations. Always use timestamps to establish
        the order of events and select the relevant analysis window.

        ### Anomaly

        Each anomaly record contains:

        - id: Unique identifier of the anomaly.
        - metric_id: ID of the metric associated with the anomaly.
        - cpu: CPU value recorded for the anomalous observation.
        - ram: RAM value recorded for the anomalous observation.
        - timestamp: Timestamp of the anomalous observation.
        - reason: Description of the detected anomaly.
        - score: Anomaly detector score.
        - device: Device associated with the anomaly.
        - detected_at: Time when the anomaly record was created.

        The metric timestamp and detected_at timestamp have different meanings.
        Use timestamp to analyze the observed event and detected_at to understand
        when the system recorded the detection.

        ## 3. CPU and RAM Interpretation

        CPU utilization indicates processor usage.
        RAM utilization indicates memory usage.

        Before interpreting values, verify the units and scale returned by the
        relevant tool. Do not assume that values are percentages unless the
        metric collection pipeline confirms this.

        For each analysis window, consider:

        - Mean: Typical utilization during the window.
        - Minimum and maximum: Range of observed utilization.
        - Variability: Whether utilization was stable or fluctuating.
        - Trend: Whether utilization was increasing, decreasing or recovering.
        - Timing: When the change started relative to the anomaly timestamp.
        - Data completeness: Number of samples and missing intervals.

        High utilization alone does not prove a fault. Interpret values in
        context, considering the device, historical baseline and other evidence.

        ## 4. Anomaly Detection

        MONA uses an Isolation Forest-based anomaly detection pipeline.

        The current model implementation uses CPU and RAM values together
        with their changes over time, including delta features.

        Configured model parameters include:

        - WINDOW = 500
        - MIN_POINTS = 30
        - contamination = 0.05
        - threshold = -0.05

        These are implementation parameters, not universal operational
        thresholds. Verify the active model configuration before relying
        on them in an investigation.

        The anomaly score is a model-specific value. Do not interpret it
        as a percentage, probability of failure or direct measure of severity
        unless the implementation explicitly defines that meaning.

        An anomaly indicates unusual behavior relative to the model's learned
        patterns. It does not necessarily indicate a real incident or failure.

        ## 5. Investigating an Anomaly

        When investigating an anomaly at timestamp T:

        1. Retrieve the anomaly record and confirm its device and timestamp.
        2. Retrieve metric samples from before and after T.
        3. Use comparable windows and consistent timezone handling.
        4. Compare CPU and RAM statistics across both windows.
        5. Identify when the change started and whether it persisted.
        6. Check for missing samples and irregular collection intervals.
        7. Look for related anomalies or additional monitoring evidence.
        8. Determine whether the system recovered, remained degraded,
        or whether the available data is insufficient.

        Unless the user specifies otherwise, a 30-minute window before
        and a 30-minute window after the anomaly can be used as an initial
        investigation window, provided sufficient data exists.

        Use the anomaly timestamp as the reference point, not detected_at,
        unless the investigation specifically concerns detection latency.

        ## 6. Data Quality

        Before drawing conclusions, check:

        - Whether the requested time range contains any samples.
        - Whether timestamps are ordered and correctly interpreted.
        - Whether the before and after windows contain enough observations.
        - Whether there are large gaps between consecutive samples.
        - Whether both windows have comparable sample counts and coverage.
        - Whether the data belongs to the requested device.

        Do not treat missing data as zero utilization.
        Do not assume that no recorded anomaly means the device was healthy.
        Distinguish missing telemetry from normal telemetry.

        If the available samples are insufficient, explicitly state this
        and avoid unsupported conclusions.

        ## 7. Interpretation Rules

        When producing an analysis:

        - Separate confirmed observations from hypotheses.
        - Support claims with actual measurements and timestamps.
        - Do not fabricate metrics, events or missing values.
        - Do not infer causation from correlation alone.
        - Do not assume that CPU or RAM spikes explain every anomaly.
        - Do not treat the anomaly score as operational severity.
        - Do not compare values from different devices as if they were
        directly equivalent without considering their baselines.
        - State the analyzed time range and the limitations of the data.

        ## 8. Recommended Report Structure

        An anomaly investigation should contain:

        1. Anomaly summary: device, timestamp, reason and recorded values.
        2. Analysis windows: exact start and end timestamps.
        3. Data quality: sample counts, gaps and coverage.
        4. Before-versus-after comparison: CPU and RAM statistics.
        5. Timeline: important changes and their timing.
        6. Findings: confirmed observations and evidence-supported hypotheses.
        7. Assessment: recovery, persistent degradation or insufficient evidence.
        8. Next steps: specific read-only checks that could reduce uncertainty.

        ## 9. Tool Usage

        Use MONA tools to retrieve current metrics and anomaly records.
        Use explicit time boundaries when possible.

        If results are paginated, retrieve all relevant pages or clearly state
        which portion of the requested window was analyzed.

        Do not modify devices, restart services, change configurations or retrain
        models during a read-only investigation unless the user explicitly
        requests an authorized operational action.
            """
