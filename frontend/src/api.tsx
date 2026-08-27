import axios, { type AxiosRequestConfig, AxiosError } from "axios";
import { API, API_VERSION } from "./config/config";

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

        if (error.response?.status === 401) {
            window.location.href = "/login";
            throw new Error("Unauthorized");
        }

        // const message =
        //     error.response?.data?.detail ??
        //     error.response?.data?.message ??
        //     (error.response ? `HTTP ${error.response.status}` : error.message);

        throw error;
    }
}