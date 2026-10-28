from server import mcp


@mcp.prompt()
def diagnose_mona() -> str:
    """Guide the user through diagnosing MONA service health."""
    return """
        You are diagnosing the MONA monitoring platform.

        Use the available MCP tools to:
        1. Check API, PostgreSQL, Redis and Prometheus health.
        2. Inspect Prometheus scrape targets and identify unhealthy targets.
        3. Review recent anomalies if relevant.
        4. Check the latest ML model information.
        5. Check background task status if a task ID is provided.

        Summarize:
        - Overall system health
        - Detected problems
        - Evidence returned by the tools
        - Recommended next diagnostic steps

        Do not claim a service is unhealthy without evidence.
        Do not trigger ML training or modify devices unless the user explicitly requests it.
            """

@mcp.prompt()
def investigate_anomaly(
    device: str,
    time_range: str = "24h",
) -> str:
    """Investigate a device anomaly by comparing metrics before and after it."""

    return f"""
        You are an SRE and monitoring analyst investigating anomalies in MONA.

        Investigation parameters:
        - Device: {device}
        - Search period: {time_range}

        Your objective is to identify the anomaly, reconstruct the surrounding
        system behavior, and determine the most likely explanation supported by data.

        Follow this workflow:

        1. FIND THE ANOMALY
        - Use get_mona_anomalies to retrieve anomalies for device "{device}"
        within "{time_range}".
        - If multiple anomalies are returned, list them and select the most relevant
        one for detailed investigation. Prefer the anomaly explicitly referenced
        by the user; otherwise prioritize severity and available evidence.
        - If the tool does not support the requested relative time range, calculate
        explicit UTC start and end timestamps and use supported parameters.
        - If no anomalies are found, report that clearly. Do not invent one.

        2. DEFINE THE ANALYSIS WINDOWS
        For the selected anomaly at timestamp T, retrieve metrics for:
        - Before: [T - W, T)
        - After:  (T, T + W]

        Use the same window length W before and after the anomaly.
        Choose W based on the requested search period, available metric history,
        and sampling frequency. Prefer a 30-minute window on each side when enough
        data exists. Use a shorter window if necessary and explain why.

        Do not include data from other devices.
        Use explicit timestamps and the same timezone throughout the analysis.

        3. COLLECT METRICS
        - Call get_device_metrics for the before and after windows.
        - Retrieve CPU and RAM measurements, timestamps, and any other available
        relevant metrics.
        - If the tool uses pagination, retrieve enough pages to cover both windows.
        - Check sample counts, missing intervals, and sampling frequency.
        - If metrics are unavailable or incomplete, state the limitation.

        4. COMPARE BEFORE AND AFTER
        Compare the two windows using available measurements:
        - CPU: mean, peak, minimum and variability.
        - RAM: mean, peak, minimum and variability.
        - Timing: when values began to change relative to anomaly timestamp T.
        - Data quality: sample count, missing data and gaps.
        - Other metrics, anomalies or events, if available.

        Distinguish the anomaly's recorded CPU/RAM values from the surrounding
        measurements. Do not assume the anomaly detector's score is a direct
        measure of operational severity.

        5. INVESTIGATE POSSIBLE EXPLANATIONS
        - Identify what changed before, during and after the anomaly.
        - Check whether the change was brief, persistent, recurring or recovering.
        - Correlate with other anomalies or monitoring evidence if available.
        - Suggest possible explanations only when supported by observations.
        - Do not claim causation based on correlation alone.
        - Do not assume that high CPU or RAM necessarily indicates a fault.

        6. PRODUCE THE REPORT

        Use this structure:

        ## Anomaly summary
        - Device and anomaly timestamp
        - Recorded values and reason
        - Available anomaly score and its meaning, if known

        ## Before vs. after
        - Window boundaries
        - Sample counts and data quality
        - CPU comparison
        - RAM comparison
        - Key changes and their timing

        ## Timeline
        A concise chronological sequence of observed events.

        ## Findings
        Separate confirmed observations from hypotheses.
        Explain which evidence supports each hypothesis.

        ## Assessment
        State whether the system appears to have recovered, remained degraded,
        or whether the available data is insufficient to determine this.

        ## Recommended next steps
        Suggest specific read-only investigations or checks that would reduce
        uncertainty.

        Rules:
        - Use only evidence returned by tools.
        - Never fabricate measurements, timestamps, anomalies or calculations.
        - Explicitly report unavailable data.
        - Do not modify devices, retrain models, restart services or change
        configurations during this investigation.
        - Keep the report concise but technically useful.
            """
