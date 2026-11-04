import React, { useState } from "react";
import { apiFetch, ApiError } from "../api";
import { AlertCircle, Plus } from "lucide-react";
import { McpDocs } from "../components/McpDocs";
import { Callout, CodeBlock } from "../components/docs/ui";

interface CreateKeyResponse {
    id: number;
    apiKey: string;
    name: string;
    createdAt?: string;
}

const focusRing =
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";

export const MCP: React.FC = () => {
    const [keyName, setKeyName] = useState<string>("Claude Desktop Key");
    const [apiKey, setApiKey] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const handleGenerateKey = async () => {
        setLoading(true);
        setError(null);
        setApiKey(null);
        try {
            const data = await apiFetch<CreateKeyResponse>("/mcp", {
                method: "POST",
                data: { name: keyName },
            });

            setApiKey(data.apiKey);
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError("An unknown error occurred");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-black text-white font-sans flex flex-col md:flex-row relative">

            <main className="flex-1 min-w-0 px-6 py-10 w-full">
                <div className="max-w-3xl mx-auto mt-5">
                    {/* ── Header ── */}
                    <header className="mb-10 w-full mt-2">
                        <h1 className="text-3xl font-bold tracking-tight text-neutral-50">
                            MCP API keys
                        </h1>
                        <p className="text-neutral-400 text-sm mt-1">
                            Generate and manage secure authentication keys for Claude and MCP integrations
                        </p>
                    </header>

                    {/* ── Generator ── */}
                    <div className="rounded-xl border border-white/10 bg-neutral-900/30 p-5 sm:p-6">
                        <label
                            htmlFor="mcp-key-name"
                            className="block text-sm font-medium text-neutral-300 mb-2"
                        >
                            Key name
                        </label>
                        <input
                            id="mcp-key-name"
                            type="text"
                            value={keyName}
                            onChange={(e) => setKeyName(e.target.value)}
                            placeholder="e.g. Claude Desktop"
                            className={`h-11 w-full rounded-xl border border-white/10 bg-neutral-900/60 px-4 text-sm text-neutral-100 placeholder:text-neutral-500 transition-colors focus:border-neutral-500 ${focusRing}`}
                        />
                        <p className="text-xs text-neutral-400 mt-2">
                            Provide a descriptive name to identify this key’s purpose in the system
                        </p>

                        <button
                            type="button"
                            onClick={handleGenerateKey}
                            disabled={loading || !keyName.trim()}
                            className={`mt-6 flex h-11 w-full sm:w-auto items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-neutral-950 transition-colors hover:bg-neutral-200 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 ${focusRing}`}
                        >
                            {loading ? (
                                <>
                                    <div className="size-4 animate-spin rounded-full border-2 border-neutral-950/30 border-t-neutral-950" />
                                    Generating…
                                </>
                            ) : (
                                <>
                                    <Plus size={16} strokeWidth={1.5} aria-hidden="true" />
                                    Generate API key
                                </>
                            )}
                        </button>

                        {/* Error */}
                        {error && (
                            <div
                                role="alert"
                                className="mt-6 flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-4"
                            >
                                <AlertCircle
                                    className="mt-0.5 shrink-0 text-red-400"
                                    size={16}
                                    strokeWidth={1.5}
                                    aria-hidden="true"
                                />
                                <div>
                                    <p className="text-sm font-medium text-red-400">Generation error</p>
                                    <p className="mt-0.5 text-xs text-neutral-400">{error}</p>
                                </div>
                            </div>
                        )}

                        {/* Generated key */}
                        {apiKey && (
                            <div className="mt-6 flex flex-col gap-4">
                                <Callout kind="warn" title="Your API key has been created">
                                    Copy it now. You won’t be able to see it again.
                                </Callout>
                                <CodeBlock lang="api key" title="API key" code={apiKey} />
                            </div>
                        )}
                    </div>

                    {/* ── Connection docs ── */}
                    <McpDocs apiKey={apiKey} />
                </div>
            </main>
        </div>
    );
};