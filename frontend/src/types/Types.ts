export interface Device {
    id: number;
    ip: string;
    name: string;
    is_active: boolean;
}

export interface MetricPoint {
    timestamp: string;
    cpu: number;
    ram: number;
    device: string;
}

export interface Anomaly {
    id: number;
    timestamp: string;
    cpu: number;
    ram: number;
    reason: string;
    score: number;
    device: string;
}

export interface ModelInfo {
    status: "ok" | "no_model";
    message?: string;
    model?: {
        trained_at: string;
        trained_by: string;
        points_count: number;
        period_from: string;
        period_to: string;
        note: string | null;
    };
}

export interface DashboardData {
    devices: string[];
    metrics: MetricPoint[];
    anomalies: Anomaly[];
}

export type TrainPhase =
    | { kind: "idle" }
    | { kind: "submitting" }
    | { kind: "polling"; taskId: string; elapsed: number }
    | { kind: "success"; text: string }
    | { kind: "error"; text: string };

type CeleryState = "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY" | "REVOKED";

export interface TaskResultPayload {
    status?: "ok" | "error" | string;
    message?: string;
    [key: string]: unknown;
}

export interface TaskStatus {
    task_id?: string;
    state: CeleryState;
    result?: TaskResultPayload | string | unknown;
}

export interface TrainResponse {
    status: "accepted" | "ok" | "success" | "error" | string;
    task_id?: string;
    message?: string;
}

export interface User {
    id: number;
    username: string;
    role: string;
}

export interface Login {
    username: string;
    password: string;
}