import axios, { type AxiosRequestConfig, AxiosError } from "axios";
import { API, API_VERSION } from "./config/config";

export class ApiError extends Error {
    public status?: number;

    constructor(message: string, status?: number) {
        super(message);
        this.status = status;
    }
}

function extractErrorMessage(error: AxiosError<any>): string {
    const data = error.response?.data;

    if (typeof data?.detail === "string") return data.detail;
    if (typeof data?.detail?.message === "string") return data.detail.message;
    if (typeof data?.message === "string") return data.message;

    if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
        return data.detail[0].msg;
    }

    return error.response
        ? `HTTP ${error.response.status}`
        : error.message ?? "Network error";
}

export async function apiFetch<T = unknown>(
    endpoint: string,
    options: AxiosRequestConfig = {}
): Promise<T> {
    try {
        const response = await axios(API + API_VERSION + endpoint, {
            withCredentials: true,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers ?? {}),
            },
            ...options,
        });

        return response.data as T;
    } catch (err) {
        const error = err as AxiosError<any>;

        const isLoginRequest = endpoint.includes("/auth/login");

        if (error.response?.status === 401 && !isLoginRequest) {
            window.location.href = "/login";
            throw new Error("Unauthorized");
        }

        // throw new Error(extractErrorMessage(error));

        throw new ApiError(
            extractErrorMessage(error), 
            error.response?.status
        );
    }
}