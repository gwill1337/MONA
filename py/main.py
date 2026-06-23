import pickle
from datetime import UTC, datetime, timedelta

import numpy as np
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

import plotly.graph_objects as go
from py.db import SessionLocal, Metric,  Anomaly, Base, TrainedModel, engine

from prometheus_fastapi_instrumentator import Instrumentator


Base.metadata.create_all(engine)

app = FastAPI()

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ─── helpers ────────────────────────────────────────────────────────────────
 
def _build_features(rows):
    cpu = np.array([r.cpu for r in rows], dtype=float)
    ram = np.array([r.ram for r in rows], dtype=float)
    cpu_d1 = np.concatenate([[0], np.diff(cpu)])
    ram_d1 = np.concatenate([[0], np.diff(ram)])
    cpu_d5 = np.concatenate([[0]*5, cpu[5:] - cpu[:-5]])
    ram_d5 = np.concatenate([[0]*5, ram[5:] - ram[:-5]])
    return np.column_stack([cpu, ram, cpu_d1, ram_d1, cpu_d5, ram_d5])


# ─── API endpoints ──────────────────────────────────────────────────────────
@app.get("/db-metrics")
def get_metrics():
    db = SessionLocal()
    data = db.query(Metric).all()
    db.close()
    return data


@app.get("/anomalies")
def get_anomalies(hours: int = 24):
    db = SessionLocal()
    try:
        q = db.query(Anomaly)
        if hours > 0:
            q = q.filter(Anomaly.timestamp >= datetime.now(UTC) - timedelta(hours=hours))
        return [
            {"id": a.id, "metric_id": a.metric_id, "cpu": a.cpu, "ram": a.ram,
             "timestamp": a.timestamp, "reason": a.reason, "score": a.score,
             "detected_at": a.detected_at}
            for a in q.order_by(Anomaly.timestamp.desc()).all()
        ]
    finally:
        db.close()


@app.get("/model-info")
def model_info():
    db = SessionLocal()
    try:
        record = (
            db.query(TrainedModel)
            .filter(TrainedModel.trained_by == "user")
            .order_by(TrainedModel.trained_at.desc())
            .first()
        )
        if record is None:
            return {"status": "no_model", "message": "Model is not manually trained yet. Using auto-mode."}
        return {
            "status": "ok",
            "model": {
                "trained_at": record.trained_at,
                "trained_by": record.trained_by,
                "points_count": record.points_count,
                "period_from": record.period_from,
                "period_to": record.period_to,
                "note": record.note,
            },
        }
    finally:
        db.close()


@app.post("/train")
def train_model(
    hours: float = Query(default=1.0, description="Hours of recent data to use for training"),
    note: str = Query(default="",description="Comment (optional)"),
    ):
    """
    Trains the model on data from the last N hours.
    This data is considered the "norm" — later the model will look for deviations from it.
    """
    db = SessionLocal()
    try:
        since = datetime.now(UTC) - timedelta(hours=hours)
        rows = (
            db.query(Metric)
            .filter(Metric.cpu > 0.1)
            .filter(Metric.timestamp >= since)
            .order_by(Metric.timestamp)
            .all()
        )

        if len(rows) < 30:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": f"Not enough data for training (found {len(rows)}, minimum 30 required)"},
            )
        
        X_raw = _build_features(rows)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)

        model = IsolationForest(
            n_estimators=200,
            contamination=0.03,
            random_state=42,
        )
        model.fit(X_scaled)

        model_bytes = pickle.dumps((model, scaler))

        record = TrainedModel(
            model_data=model_bytes,
            trained_by="user",
            points_count=len(rows),
            period_from=rows[0].timestamp,
            period_to=rows[-1].timestamp,
            note=note.strip() or None,
        )
        db.add(record)
        db.commit()

        return {
            "status": "ok",
            "message": f"Model trained on {len(rows)} points over the last {hours} h.",
            "period_from": rows[0].timestamp,
            "period_to": rows[-1].timestamp,
            "points_count": len(rows),
        }
    
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        db.close()


@app.delete("/model")
def delete_model():
    """Deletes the custom model — Celery will return to auto-mode."""
    db = SessionLocal()
    try:
        deleted = db.query(TrainedModel).filter(TrainedModel.trained_by == "user").delete()
        db.commit()
        return {"status": "ok", "deleted": deleted, "message": "Model deleted. Celery switched to auto-mode."}
    finally:
        db.close()


# ─── Dashboard ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(hours: int = 1):
    db = SessionLocal()
    try:
        since = datetime.now(UTC) - timedelta(hours=hours) if hours > 0 else None
        q_m = db.query(Metric)
        q_a = db.query(Anomaly)
        if since:
            q_m = q_m.filter(Metric.timestamp >= since)
            q_a = q_a.filter(Anomaly.timestamp >= since)
        metrics   = q_m.order_by(Metric.timestamp).all()
        anomalies = q_a.order_by(Anomaly.timestamp).all()
 
        # Model info
        model_record = (
            db.query(TrainedModel)
            .filter(TrainedModel.trained_by == "user")
            .order_by(TrainedModel.trained_at.desc())
            .first()
        )
    finally:
        db.close()
 
    if not metrics:
        return "<h1>No data available</h1>"
 
    times      = [m.timestamp.strftime("%H:%M:%S") for m in metrics]
    cpu_values = [m.cpu for m in metrics]
    ram_values = [m.ram for m in metrics]
    a_times    = [a.timestamp.strftime("%H:%M:%S") for a in anomalies]
    a_cpu      = [a.cpu for a in anomalies]
    a_ram      = [a.ram for a in anomalies]
    a_text     = [f"⚠️ {a.reason}<br>score: {a.score}" for a in anomalies]
 
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=cpu_values, mode='lines', name='CPU %',
                             line=dict(color='#e74c3c', width=1.5)))
    fig.add_trace(go.Scatter(x=times, y=ram_values, mode='lines', name='RAM %',
                             line=dict(color='#3498db', width=1.5)))
    if anomalies:
        fig.add_trace(go.Scatter(x=a_times, y=a_cpu, mode='markers', name='⚠️ Anomaly (CPU)',
            marker=dict(color='red', size=10, symbol='x', line=dict(width=2, color='darkred')),
            text=a_text, hovertemplate='%{text}<extra></extra>'))
        fig.add_trace(go.Scatter(x=a_times, y=a_ram, mode='markers', name='⚠️ Anomaly (RAM)',
            marker=dict(color='orange', size=10, symbol='x', line=dict(width=2, color='darkorange')),
            text=a_text, hovertemplate='%{text}<extra></extra>'))
 
    label = f"last {hours} h." if hours > 0 else "all time"
    fig.update_layout(
        title=f'CPU & RAM — {label}  |  anomalies: {len(anomalies)}',
        xaxis_title='Time', yaxis_title='Usage (%)',
        yaxis=dict(range=[0, 105]), template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
 
    # ── Model block ──
    if model_record:
        trained_str = model_record.trained_at.strftime("%d.%m.%Y %H:%M")
        pfrom = model_record.period_from.strftime("%H:%M:%S") if model_record.period_from else "—"
        pto   = model_record.period_to.strftime("%H:%M:%S") if model_record.period_to else "—"
        note_str = f"<br><small>📝 {model_record.note}</small>" if model_record.note else ""
        model_block = f"""
        <div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:6px;padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:20px;flex-wrap:wrap">
            <span>🧠 <b>Model:</b> manually trained {trained_str} &nbsp;·&nbsp;
            {model_record.points_count} points &nbsp;·&nbsp; period {pfrom} → {pto}
            {note_str}</span>
            <button onclick="deleteModel()" style="margin-left:auto;background:#ef5350;color:white;border:none;padding:6px 14px;border-radius:4px;cursor:pointer">
                Reset model
            </button>
        </div>"""
    else:
        model_block = """
        <div style="background:#fff3e0;border:1px solid #ffcc80;border-radius:6px;padding:12px 16px;margin-bottom:16px">
            <b>Auto-mode:</b> model trains on the fly. Train manually on a "clean" period for best results.
        </div>"""
 
    # ── Anomalies table ──
    anomaly_rows = ""
    for a in reversed(anomalies[-20:]):
        ts = a.timestamp.strftime("%d.%m %H:%M:%S")
        color = 'red' if a.score < -0.1 else 'orange'
        anomaly_rows += (f"<tr><td>{ts}</td><td>{a.cpu:.1f}%</td><td>{a.ram:.1f}%</td>"
                         f"<td>{a.reason}</td><td style='color:{color}'>{a.score:.4f}</td></tr>")
 
    anomaly_section = ""
    if anomaly_rows:
        anomaly_section = f"""
        <h2 style="margin-top:30px">⚠️ Latest anomalies</h2>
        <table border="1" cellpadding="6" cellspacing="0"
               style="border-collapse:collapse;font-family:monospace;font-size:13px">
            <thead style="background:#f0f0f0">
                <tr><th>Time</th><th>CPU</th><th>RAM</th><th>Reason</th><th>Score</th></tr>
            </thead>
            <tbody>{anomaly_rows}</tbody>
        </table>
        <p style="font-size:12px;color:#888">Score: the lower, the stronger the anomaly</p>"""
    else:
        anomaly_section = "<p style='color:green'>✅ No anomalies detected for the selected period</p>"
 
    return f"""
    <html>
    <head>
        <title>Monitoring Dashboard</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            .train-form {{ background:#f5f5f5; border:1px solid #ddd; border-radius:6px; padding:14px 18px; margin-bottom:16px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
            .train-form label {{ font-weight:600; }}
            .train-form input {{ padding:5px 8px; border:1px solid #ccc; border-radius:4px; width:70px; }}
            .train-form input[type=text] {{ width:200px; }}
            .train-btn {{ background:#1976d2; color:white; border:none; padding:7px 18px; border-radius:4px; cursor:pointer; font-size:14px; }}
            .train-btn:hover {{ background:#1565c0; }}
            #train-result {{ margin-top:8px; font-size:13px; }}
        </style>
    </head>
    <body>
        <h1>📊 Dashboard</h1>
 
        {model_block}
 
        <!-- Training form -->
        <div class="train-form">
            <label>Train model on a "clean" period:</label>
            <label>Hours: <input type="number" id="train-hours" value="1" min="0.1" step="0.5"></label>
            <label>Note: <input type="text" id="train-note" placeholder="e.g.: low load"></label>
            <button class="train-btn" onclick="trainModel()">Train</button>
            <div id="train-result"></div>
        </div>
 
        <!-- Display period -->
        <label>Period:&nbsp;
        <select onchange="location.href='/?hours=' + this.value">
            <option value="1"   {'selected' if hours==1   else ''}>Last hour</option>
            <option value="24"  {'selected' if hours==24  else ''}>Last 24 hours</option>
            <option value="168" {'selected' if hours==168 else ''}>7 days</option>
            <option value="0"   {'selected' if hours==0   else ''}>All time</option>
        </select>
        </label>
 
        {fig.to_html(include_plotlyjs='cdn', full_html=False)}
        {anomaly_section}
 
        <script>
        async function trainModel() {{
            const hours = document.getElementById('train-hours').value;
            const note  = document.getElementById('train-note').value;
            const div   = document.getElementById('train-result');
            div.textContent = '⏳ Training...';
            try {{
                const r = await fetch(`/train?hours=${{hours}}&note=${{encodeURIComponent(note)}}`, {{method:'POST'}});
                const d = await r.json();
                if (d.status === 'ok') {{
                    div.style.color = 'green';
                    div.textContent = `✅ ${{d.message}}`;
                    setTimeout(() => location.reload(), 1500);
                }} else {{
                    div.style.color = 'red';
                    div.textContent = `❌ ${{d.message}}`;
                }}
            }} catch(e) {{
                div.style.color = 'red';
                div.textContent = '❌ Connection error';
            }}
        }}
 
        async function deleteModel() {{
            if (!confirm('Reset model and return to auto-mode?')) return;
            const r = await fetch('/model', {{method:'DELETE'}});
            const d = await r.json();
            alert(d.message);
            location.reload();
        }}
        </script>
    </body>
    </html>
    """