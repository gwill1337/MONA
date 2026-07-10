const API = "http://localhost:30080";

export async function apiFetch(
    endpoint: string,
    options: RequestInit = {}
) {
    const response = await fetch(API + endpoint, {
        credentials: "include",
        headers: {
            "Content-Type": "application/json",
            ...(options.headers ?? {}),
        },
        ...options,
    });

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Unauthorized");
    }

    if (!response.ok) {
        let message = `HTTP ${response.status}`;

        try {
            const data = await response.json();
            message = data.detail ?? data.message ?? message;
        } catch {}

        throw new Error(message);
    }

    return response;
}