import React from "react";
import {
    Callout,
    Code,
    CodeBlock,
    P,
    Procedure,
    Section,
    Tabs,
} from "./docs/ui";

// Public URL of the MONA MCP server (SSE endpoint). Change it to match your deployment.
const MCP_SERVER_URL = "http://localhost:30082/sse";
const KEY_PLACEHOLDER = "mona_api_YOUR_KEY";

/* ── Docs section ── */

interface McpDocsProps {
    /** Freshly generated API key. When null, a placeholder is shown in the snippets. */
    apiKey: string | null;
}

export const McpDocs: React.FC<McpDocsProps> = ({ apiKey }) => {
    const key = apiKey ?? KEY_PLACEHOLDER;

    const claudeCodeCmd = `claude mcp add --transport sse mona ${MCP_SERVER_URL} --header "Authorization: Bearer ${key}"`;

    const claudeDesktopConfig = JSON.stringify(
        {
            mcpServers: {
                mona: {
                    command: "npx",
                    args: [
                        "-y",
                        "mcp-remote",
                        MCP_SERVER_URL,
                        "--transport",
                        "sse-only",
                        "--allow-http",
                        "--header",
                        "Authorization:${MONA_AUTH}",
                    ],
                    env: {
                        MONA_AUTH: `Bearer ${key}`,
                    },
                },
            },
        },
        null,
        2,
    );

    // Codex has no SSE transport, so it talks to MONA through the mcp-remote bridge (stdio).
    const codexConfig = `[mcp_servers.mona]
command = "npx"
args = [
  "-y",
  "mcp-remote",
  "${MCP_SERVER_URL}",
  "--transport",
  "sse-only",
  "--allow-http",
  "--header",
  "Authorization:\${MONA_AUTH}",
]

[mcp_servers.mona.env]
MONA_AUTH = "Bearer ${key}"`;

    const cursorConfig = JSON.stringify(
        {
            mcpServers: {
                mona: {
                    url: MCP_SERVER_URL,
                    headers: {
                        Authorization: `Bearer ${key}`,
                    },
                },
            },
        },
        null,
        2,
    );

    const ollamaConfig = JSON.stringify(
        {
            mcpServers: {
                mona: {
                    type: "sse",
                    url: MCP_SERVER_URL,
                    headers: {
                        Authorization: `Bearer ${key}`,
                    },
                },
            },
        },
        null,
        2,
    );

    return (
        <div className="mt-12">
            <Section
                id="connect"
                title="Connect to the MCP server"
                lead={
                    <>
                        Choose your client and follow the steps below.
                        {apiKey
                            ? " Your new key is already inserted into every snippet."
                            : " Generate a key above and it will be inserted into the snippets automatically."}
                    </>
                }
            >
                {/* Server info */}
                <div className="flex flex-col gap-3">
                    <CodeBlock lang="url" title="Server URL (SSE)" code={MCP_SERVER_URL} />
                    <P>
                        Authentication: <Code>Authorization: Bearer {"<your key>"}</Code>{" "}
                        header.
                    </P>
                </div>

                <Tabs
                    label="MCP client"
                    items={[
                        {
                            id: "claude-code",
                            label: "Claude Code",
                            content: (
                                <Procedure
                                    steps={[
                                        {
                                            title: "Add the server",
                                            body: (
                                                <>
                                                    <p>Run this command in your terminal:</p>
                                                    <CodeBlock lang="bash" code={claudeCodeCmd} />
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Verify the connection",
                                            body: (
                                                <>
                                                    <CodeBlock lang="bash" code="claude mcp list" />
                                                    <p>
                                                        Or start <Code>claude</Code> and type{" "}
                                                        <Code>/mcp</Code>. The <Code>mona</Code> server
                                                        should show as connected.
                                                    </p>
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Use it",
                                            body: (
                                                <>
                                                    <p>
                                                        Ask Claude something like “show MONA devices” or
                                                        “investigate the latest anomaly on device X”. To
                                                        remove the server later:
                                                    </p>
                                                    <CodeBlock lang="bash" code="claude mcp remove mona" />
                                                </>
                                            ),
                                        },
                                    ]}
                                />
                            ),
                        },
                        {
                            id: "claude-desktop",
                            label: "Claude Desktop",
                            content: (
                                <Procedure
                                    steps={[
                                        {
                                            title: "Install Node.js",
                                            body: (
                                                <p>
                                                    Claude Desktop connects to a custom server with an auth
                                                    header through the <Code>mcp-remote</Code> proxy, which
                                                    runs via <Code>npx</Code>. Make sure Node.js 18+ is
                                                    installed.
                                                </p>
                                            ),
                                        },
                                        {
                                            title: "Open the config file",
                                            body: (
                                                <>
                                                    <p>
                                                        In Claude Desktop go to{" "}
                                                        <Code>Settings → Developer → Edit Config</Code>, or
                                                        open the file manually:
                                                    </p>
                                                    <p>
                                                        macOS:{" "}
                                                        <Code>
                                                            ~/Library/Application
                                                            Support/Claude/claude_desktop_config.json
                                                        </Code>
                                                    </p>
                                                    <p>
                                                        Windows:{" "}
                                                        <Code>%APPDATA%\Claude\claude_desktop_config.json</Code>
                                                    </p>
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Add the MONA server",
                                            body: (
                                                <>
                                                    <p>
                                                        Paste this into the file (if{" "}
                                                        <Code>mcpServers</Code> already exists, add only the{" "}
                                                        <Code>mona</Code> block inside it):
                                                    </p>
                                                    <CodeBlock
                                                        lang="json"
                                                        title="claude_desktop_config.json"
                                                        code={claudeDesktopConfig}
                                                    />
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Restart Claude Desktop",
                                            body: (
                                                <p>
                                                    Fully quit the app (including the tray icon) and open it
                                                    again. The MONA tools will appear in the tools menu of
                                                    the chat input.
                                                </p>
                                            ),
                                        },
                                    ]}
                                />
                            ),
                        },
                        {
                            id: "codex",
                            label: "Codex",
                            content: (
                                <Procedure
                                    steps={[
                                        {
                                            title: "Install Node.js",
                                            body: (
                                                <p>
                                                    Codex connects to the MONA server through the{" "}
                                                    <Code>mcp-remote</Code> proxy, which runs via{" "}
                                                    <Code>npx</Code>. Make sure Node.js 18+ is installed.
                                                </p>
                                            ),
                                        },
                                        {
                                            title: "Open the config file",
                                            body: (
                                                <>
                                                    <p>Open the Codex configuration file:</p>
                                                    <p>
                                                        macOS / Linux: <Code>~/.codex/config.toml</Code>
                                                    </p>
                                                    <p>
                                                        Windows: <Code>%USERPROFILE%\.codex\config.toml</Code>
                                                    </p>
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Add the MONA server",
                                            body: (
                                                <>
                                                    <p>
                                                        Paste this into the file (if other servers already
                                                        exist, add only the <Code>mona</Code> block):
                                                    </p>
                                                    <CodeBlock
                                                        lang="toml"
                                                        title="config.toml"
                                                        code={codexConfig}
                                                    />
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Restart Codex",
                                            body: (
                                                <p>
                                                    Fully quit Codex and open it again. The MONA tools will
                                                    appear in the available tools list.
                                                </p>
                                            ),
                                        },
                                    ]}
                                />
                            ),
                        },
                        {
                            id: "cursor",
                            label: "Cursor",
                            content: (
                                <Procedure
                                    steps={[
                                        {
                                            title: "Open the config file",
                                            body: (
                                                <>
                                                    <p>
                                                        In Cursor go to <Code>Settings → MCP</Code>, or open
                                                        the configuration file manually:
                                                    </p>
                                                    <p>
                                                        Global: <Code>~/.cursor/mcp.json</Code>
                                                    </p>
                                                    <p>
                                                        Project: <Code>.cursor/mcp.json</Code>
                                                    </p>
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Add the MONA server",
                                            body: (
                                                <>
                                                    <p>
                                                        Paste this into the file. If{" "}
                                                        <Code>mcpServers</Code> already exists, add only the{" "}
                                                        <Code>mona</Code> block:
                                                    </p>
                                                    <CodeBlock
                                                        lang="json"
                                                        title="mcp.json"
                                                        code={cursorConfig}
                                                    />
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Restart Cursor",
                                            body: (
                                                <p>
                                                    Save the file and restart Cursor. The MONA tools should
                                                    now appear in the MCP settings.
                                                </p>
                                            ),
                                        },
                                    ]}
                                />
                            ),
                        },
                        {
                            id: "ollama",
                            label: "Ollama",
                            content: (
                                <Procedure
                                    steps={[
                                        {
                                            title: "Pick a model with tool support",
                                            body: (
                                                <>
                                                    <p>
                                                        Ollama has no built-in MCP support, so you need an
                                                        MCP client on top of it. The model must support tool
                                                        calling (e.g. Qwen 2.5, Llama 3.1+):
                                                    </p>
                                                    <CodeBlock lang="bash" code="ollama pull qwen2.5:7b" />
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Install the MCP client",
                                            body: (
                                                <>
                                                    <p>
                                                        We use <Code>ollmcp</Code> (MCP Client for Ollama):
                                                    </p>
                                                    <CodeBlock
                                                        lang="bash"
                                                        code="pip install --upgrade ollmcp"
                                                    />
                                                    <p>
                                                        Or run it without installing: <Code>uvx ollmcp</Code>
                                                    </p>
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Create a server config",
                                            body: (
                                                <>
                                                    <p>
                                                        Save this as <Code>mona-servers.json</Code>:
                                                    </p>
                                                    <CodeBlock
                                                        lang="json"
                                                        title="mona-servers.json"
                                                        code={ollamaConfig}
                                                    />
                                                </>
                                            ),
                                        },
                                        {
                                            title: "Run the client",
                                            body: (
                                                <>
                                                    <CodeBlock
                                                        lang="bash"
                                                        code="ollmcp --servers-json mona-servers.json --model qwen2.5:7b"
                                                    />
                                                    <p>
                                                        Type <Code>tools</Code> to see the MONA tools, then
                                                        chat as usual. If Ollama runs on another machine, add{" "}
                                                        <Code>--host http://&lt;ollama-host&gt;:11434</Code>.
                                                    </p>
                                                </>
                                            ),
                                        },
                                    ]}
                                />
                            ),
                        },
                    ]}
                />

                {/* Security note */}
                <Callout kind="warn" title="Keep your API key private">
                    Anyone with the key can call MONA tools, including adding and removing
                    devices and training models. If a key leaks, revoke it and generate a new
                    one.
                </Callout>
            </Section>
        </div>
    );
};