"""
ml.py — обнаружение аномалий через Isolation Forest.
 
Два режима:
  1. Есть обученная модель в БД (trained_by="user") → используем её.
     Модель знает что такое "норма" — точность выше.
  2. Нет модели → обучаемся на лету на последних WINDOW точках (fallback).
 
Признаки (6 штук):
  cpu, ram                — абсолютные значения
  cpu_d1, ram_d1          — изменение к предыдущей точке
  cpu_d5, ram_d5          — изменение за 5 точек (~25 сек)
"""

import io
import pickle
from datetime import UTC, datetime, timedelta

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


from py.celery_conf import app
from py.db import SessionLocal, Metric, Anomaly, TrainedModel


WINDOW = 500
MIN_POINTS = 30
CONTAMINATION = 0.05


# -------- helpers -------- 

def _build_features(rows):
    """
    Строит матрицу признаков с дельтами.
    Возвращает np.array формы (N, 6).
    """
    cpu = np.array([r.cpu for r in rows], dtype=float)
    ram = np.array([r.ram for r in rows], dtype=float)
 
    # Дельта к предыдущей точке (i-1)
    cpu_d1 = np.concatenate([[0], np.diff(cpu)])
    ram_d1 = np.concatenate([[0], np.diff(ram)])
 
    # Дельта за 5 точек назад
    cpu_d5 = np.concatenate([[0]*5, cpu[5:] - cpu[:-5]])
    ram_d5 = np.concatenate([[0]*5, ram[5:] - ram[:-5]])
 
    return np.column_stack([cpu, ram, cpu_d1, ram_d1, cpu_d5, ram_d5])


def _describe_reason(row, cpu_d1, ram_d1, cpu_d5, ram_d5):
    """Человекочитаемое описание почему точка аномальна."""
    parts = []
 
    if row.cpu > 85:
        parts.append(f"высокий cpu={row.cpu:.1f}%")
    if row.ram > 85:
        parts.append(f"высокий ram={row.ram:.1f}%")
 
    if abs(cpu_d1) > 20:
        sign = "▲" if cpu_d1 > 0 else "▼"
        parts.append(f"резкий скачок cpu {sign}{abs(cpu_d1):.1f}%")
    if abs(ram_d1) > 15:
        sign = "▲" if ram_d1 > 0 else "▼"
        parts.append(f"резкий скачок ram {sign}{abs(ram_d1):.1f}%")
 
    if abs(cpu_d5) > 30:
        parts.append(f"cpu вырос на {cpu_d5:.1f}% за 25 сек")
    if abs(ram_d5) > 20:
        parts.append(f"ram вырос на {ram_d5:.1f}% за 25 сек")
 
    if not parts:
        parts.append(f"комбинированная аномалия (cpu={row.cpu:.1f}%, ram={row.ram:.1f}%)")
 
    return ", ".join(parts)


def _load_user_model(db):
    """Загружает последнюю модель обученную пользователем. None если нет."""
    record = (
        db.query(TrainedModel)
        .filter(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .first()
    )
    if record is None:
        return None, None
    model, scaler = pickle.loads(record.model_data)
    return model, scaler


# -------- celery task -------- 

@app.task
def detect_anomalies():
    """Обнаруживает аномалии в последних WINDOW точках метрик."""
    db = SessionLocal()
    try:

        cutoff_new = datetime.now(UTC) - timedelta(minutes=2)
        
        rows = (
            db.query(Metric)
            .filter(Metric.cpu > 0.1)          # убираем нулевые замеры при старте
            .order_by(Metric.timestamp.desc())
            .limit(WINDOW)
            .all()
        )
 
        if len(rows) < MIN_POINTS:
            return {
                "status": "skipped",
                "reason": f"мало данных ({len(rows)} точек, нужно {MIN_POINTS}+)"
            }
 
        rows = list(reversed(rows))  # хронологический порядок

        user_model, user_scaler = _load_user_model(db)

        if user_model is not None:
            # ── Режим 1: пользовательская модель ──
            X_all = _build_features(rows)
            X_scaled = user_scaler.transform(X_all)
            preds = user_model.predict(X_scaled)
            scores = user_model.decision_function(X_scaled)
            mode ="user_model"
        else:
            # ── Режим 2: обучение на лету (fallback) ──
            X_all = _build_features(rows)
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_all)
            model = IsolationForest(
                n_estimators=200,
                contamination=CONTAMINATION,
                random_state=42,
            )
            preds = model.fit_predict(X_scaled)
            scores = model.decision_function(X_scaled)
            mode = "auto"
 
        # Не дублируем уже сохранённые аномалии
        existing_ids = {
            a.metric_id for a in db.query(Anomaly.metric_id).all()
        }
 
        new_anomalies = []
        for i, row in enumerate(rows):
            if mode == "auto" and row.timestamp < cutoff_new.replace(tzinfo=None):
                continue  # в режиме авто смотрим только новые данные за последние 2 минуты
            if preds[i] != -1 or row.id in existing_ids:
                continue
                
            X_raw = _build_features(rows)

            reason = _describe_reason(
                row,
                cpu_d1=X_raw[i, 2],
                ram_d1=X_raw[i, 3],
                cpu_d5=X_raw[i, 4],
                ram_d5=X_raw[i, 5],
            )
 
            new_anomalies.append(Anomaly(
                metric_id=row.id,
                cpu=row.cpu,
                ram=row.ram,
                timestamp=row.timestamp,
                reason=reason,
                score=round(float(scores[i]), 4),
            ))
 
        if new_anomalies:
            db.bulk_save_objects(new_anomalies)
            db.commit()
 
        return {
            "status": "ok",
            "mode": mode,
            "window": len(rows),
            "anomalies_found": len(new_anomalies),
        }
 
    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

# @app.task
# def detect_anomalies():
#     db = SessionLocal()
#     try:
#         rows = (
#             db.query(Metric)
#             .order_by(Metric.timestamp.desc())
#             .limit(WINDOW)
#             .all()
#         )

#         if len(rows) < 50:
#             return {"status": "skipped", "reason": f"not enough data ({len(rows)} points, need 50+)"}
        
#         rows = list(reversed(rows))

#         X = np.array([[r.cpu, r.ram] for r in rows])

#         model = IsolationForest(
#             n_estimators=100,
#             contamination=CONTAMINATION,
#             random_state=42,
#         )

#         preds = model.fit_predict(X)
#         scores = model.decision_function(X)

#         existing_ids = {
#             a.metric_id
#             for a in db.query(Anomaly.metric_id).all()
#         }

#         new_anomalies = []
#         for i, row in enumerate(rows):
#             if preds[i] == -1 and row.id not in existing_ids:
#                 reasons = []
#                 if row.cpu > 85:
#                     reasons.append(f"cpu={row.cpu:.1f}%")
#                 if row.ram > 85:
#                     reasons.append(f"ram={row.ram:.1f}%")
#                 if not reasons:
#                     reasons.append(f"combined anomaly (cpu={row.cpu:.1f}%, ram={row.ram:.1f}%)")
                
#                 new_anomalies.append(
#                     Anomaly(
#                         metric_id=row.id,
#                         cpu=row.cpu,
#                         ram=row.ram,
#                         timestamp=row.timestamp,
#                         reason=", ".join(reasons),
#                         score=round(float(scores[i]), 4),
#                     )
#                 )

#         if new_anomalies:
#             db.bulk_save_objects(new_anomalies)
#             db.commit()
        
#         return {
#             "status": "ok",
#             "window": len(rows),
#             "anomalies_found": len(new_anomalies),
#         }
    
#     except Exception as e:
#         db.rollback()
#         return {"status": "error", "error": str(e)}
#     finally:
#         db.close()