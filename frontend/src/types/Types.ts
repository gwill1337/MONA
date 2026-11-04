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

export interface User {
    id: number;
    username: string;
    role: string;
}

export interface Login {
    username: string;
    password: string;
}

// The raw model structure itself
export interface ModelInfo {
    id: number;
    trained_at: string;
    trained_by: string;
    points_count: number;
    period_from?: string | null;
    period_to?: string | null;
    note?: string | null;
    is_active?: boolean;
}

export type ModelItem = ModelInfo;

export interface ModelListResponse {
    items: ModelItem[];
}

// The response wrapper returned by the API endpoint
export type ModelInfoResponse =
    | { status: "ok"; model: ModelInfo }
    | { status: "no_model"; message: string };

export type CeleryState = "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY" | "REVOKED" | string;

export interface TaskResultPayload {
    status?: "ok" | "error" | string;
    message?: string;
    [key: string]: any;
}

export interface TaskStatus {
    task_id: string;
    state: CeleryState;
    result?: TaskResultPayload | string | any;
}

export interface TrainResponse {
    status: "accepted" | "ok" | "success" | "error" | string;
    task_id?: string;
    message?: string;
}

export type TrainPhase =
    | { kind: "idle" }
    | { kind: "submitting" }
    | { kind: "polling"; taskId: string; elapsed: number }
    | { kind: "success"; text: string }
    | { kind: "error"; text: string };

export interface DashboardData {
    devices: string[];
    model?: ModelInfo | null;
    metrics: MetricPoint[];
    anomalies: Anomaly[];
}