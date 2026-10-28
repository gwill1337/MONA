import React, { useState } from "react";
import { apiFetch, ApiError } from "../api";

interface CreateKeyResponse {
    id: number;
    apiKey: string;
    name: string;
    createdAt?: string;
}

export const ApiKeyTest: React.FC = () => {
    const [keyName, setKeyName] = useState<string>("Claude Desktop Key");
    const [apiKey, setApiKey] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const handleGenerateKey = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await apiFetch<CreateKeyResponse>("/api", {
                method: "POST",
                data: { name: keyName },
            });

            setApiKey(data.apiKey);
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError("Произошла неизвестная ошибка");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: "24px", maxWidth: "500px", fontFamily: "sans-serif" }}>
            <h2>Генерация API ключа MCP</h2>

            {/* Поле для ввода названия ключа */}
            <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", marginBottom: "6px", fontWeight: 500, color: "#334155" }}>
                    Название ключа:
                </label>
                <input
                    type="text"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    placeholder="Например: Claude Desktop"
                    style={{
                        width: "100%",
                        padding: "8px 12px",
                        boxSizing: "border-box",
                        border: "1px solid #cbd5e1",
                        borderRadius: "4px",
                        fontSize: "14px",
                        outline: "none",
                    }}
                />
            </div>

            <button
                onClick={handleGenerateKey}
                disabled={loading || !keyName.trim()}
                style={{
                    padding: "10px 20px",
                    fontSize: "16px",
                    cursor: loading || !keyName.trim() ? "not-allowed" : "pointer",
                    backgroundColor: "#0088FF",
                    color: "#fff",
                    border: "none",
                    borderRadius: "6px",
                    fontWeight: 600,
                }}
            >
                {loading ? "Генерация..." : "Сгенерировать API ключ"}
            </button>

            {error && (
                <div style={{ marginTop: "16px", color: "#e53e3e", fontWeight: 500 }}>
                    Ошибка: {error}
                </div>
            )}

            {apiKey && (
                <div
                    style={{
                        marginTop: "20px",
                        padding: "16px",
                        backgroundColor: "#f0fdf4",
                        border: "1px solid #bbf7d0",
                        borderRadius: "8px",
                    }}
                >
                    <p style={{ margin: "0 0 8px 0", fontWeight: 600, color: "#166534" }}>
                        Ваш API Ключ (сохраните его, он показывается 1 раз):
                    </p>
                    <code
                        style={{
                            display: "block",
                            padding: "8px 12px",
                            backgroundColor: "#fff",
                            border: "1px solid #e2e8f0",
                            borderRadius: "4px",
                            wordBreak: "break-all",
                            fontSize: "14px",
                            color: "#0f172a",
                        }}
                    >
                        {apiKey}
                    </code>
                </div>
            )}
        </div>
    );
};