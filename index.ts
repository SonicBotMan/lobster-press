/**
 * @sonicbotman/lobster-press — Cognitive Memory System for AI Agents
 *
 * DAG-based conversation summarization with Ebbinghaus forgetting curve,
 * semantic notes, contradiction detection.
 *
 * Phase 1 IPC Refactor (Issue #115):
 * - Ready handshake from Python
 * - Request ID routing for concurrent requests
 * - Clean failure on child process exit
 */
import { spawn, type ChildProcess } from "node:child_process";
import { join } from "node:path";
import { Type } from "@sinclair/typebox";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

// ─── IPC Types ───────────────────────────────────────────────────────────────

type McpEnvelope = {
  type?: string;
  requestId?: string;
  status?: string;
  result?: unknown;
  error?: unknown;
  [key: string]: unknown;
};

// ─── Global State ────────────────────────────────────────────────────────────

let mcpProcess: ChildProcess | null = null;
let mcpReady = false;
let bootPromise: Promise<ChildProcess> | null = null;
let stdoutBuffer = "";

const pendingRequests = new Map<
  string,
  {
    resolve: (value: McpEnvelope) => void;
    reject: (reason: Error) => void;
    timer: NodeJS.Timeout;
  }
>();

// ─── IPC Helpers ─────────────────────────────────────────────────────────────

function generateRequestId(): string {
  return `lobster-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function handleStdoutLine(line: string): void {
  let msg: McpEnvelope;
  try {
    msg = JSON.parse(line);
  } catch {
    return;
  }

  // Ready handshake from Python
  if (msg.type === "lobster-press/ready") {
    mcpReady = true;
    return;
  }

  // Route response by requestId
  const requestId = msg.requestId;
  if (!requestId) return;

  const pending = pendingRequests.get(requestId);
  if (!pending) return;

  clearTimeout(pending.timer);
  pendingRequests.delete(requestId);

  if (msg.status === "error") {
    pending.reject(
      new Error(typeof msg.error === "string" ? msg.error : JSON.stringify(msg.error))
    );
  } else {
    pending.resolve(msg);
  }
}

function attachStdoutDispatcher(proc: ChildProcess): void {
  if (!proc.stdout) return;
  if ((proc.stdout as { __lobsterDispatcherAttached?: boolean }).__lobsterDispatcherAttached) return;

  (proc.stdout as { __lobsterDispatcherAttached?: boolean }).__lobsterDispatcherAttached = true;

  proc.stdout.on("data", (chunk: Buffer) => {
    stdoutBuffer += chunk.toString("utf8");
    const lines = stdoutBuffer.split("\n");
    stdoutBuffer = lines.pop() ?? "";

    for (const raw of lines) {
      const line = raw.trim();
      if (!line) continue;
      handleStdoutLine(line);
    }
  });

  proc.on("exit", (code) => {
    mcpProcess = null;
    mcpReady = false;
    bootPromise = null;

    // Fail all pending requests
    for (const [, pending] of pendingRequests) {
      clearTimeout(pending.timer);
      pending.reject(new Error(`lobster-press MCP exited: code=${code ?? "unknown"}`));
    }
    pendingRequests.clear();
  });
}

async function ensureMcpServer(config: Record<string, unknown>): Promise<ChildProcess> {
  if (mcpProcess && mcpReady) return mcpProcess;
  if (bootPromise) return bootPromise;

  bootPromise = new Promise((resolve, reject) => {
    const dbPath =
      (config.dbPath as string) ||
      join(process.env.HOME ?? "~", ".openclaw/lobster.db");
    const pythonCmd = process.env.LOBSTER_PYTHON ?? "python3";

    const proc = spawn(
      pythonCmd,
      [
        "-m",
        "mcp_server.lobster_mcp_server",
        "--db",
        dbPath,
        "--provider",
        (config.llmProvider as string) || "",
        "--model",
        (config.llmModel as string) || "",
      ],
      {
        env: {
          ...process.env,
          LOBSTER_LLM_API_KEY:
            (config.llmApiKey as string) ||
            process.env.LOBSTER_LLM_API_KEY ||
            "",
        },
        stdio: ["pipe", "pipe", "inherit"],
      }
    );

    mcpProcess = proc;
    mcpReady = false;
    attachStdoutDispatcher(proc);

    const startedAt = Date.now();
    const poll = setInterval(() => {
      if (mcpReady) {
        clearInterval(poll);
        resolve(proc);
      } else if (Date.now() - startedAt > 10_000) {
        clearInterval(poll);
        bootPromise = null;
        reject(new Error("lobster-press MCP did not become ready within 10s"));
      }
    }, 50);

    proc.once("error", (err) => {
      clearInterval(poll);
      bootPromise = null;
      reject(err);
    });

    proc.once("exit", (code) => {
      if (!mcpReady) {
        clearInterval(poll);
        bootPromise = null;
        reject(new Error(`lobster-press MCP exited before ready: code=${code ?? "unknown"}`));
      }
    });
  });

  try {
    return await bootPromise;
  } finally {
    if (mcpReady) bootPromise = null;
  }
}

async function callMcp(
  config: Record<string, unknown>,
  toolName: string,
  args: Record<string, unknown>
): Promise<{ content: Array<{ type: "text"; text: string }>; details: unknown }> {
  const proc = await ensureMcpServer(config);
  const requestId = generateRequestId();

  const response = await new Promise<McpEnvelope>((resolve, reject) => {
    const timer = setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error(`lobster-press MCP tool call timed out after 30s: ${toolName}`));
    }, 30_000);

    pendingRequests.set(requestId, { resolve, reject, timer });

    const request =
      JSON.stringify({
        method: "tools/call",
        requestId,
        params: { name: toolName, arguments: args },
      }) + "\n";

    proc.stdin?.write(request);
  });

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(response.result ?? response, null, 2),
      },
    ],
    details: response,
  };
}

// ─── Tool Schemas ─────────────────────────────────────────────────────────────

const LobsterGrepSchema = Type.Object({
  query: Type.String({ description: "搜索关键词或短语" }),
  conversation_id: Type.Optional(Type.String({ description: "限定搜索范围的会话 ID" })),
  limit: Type.Optional(Type.Number({ description: "最多返回条数，默认 5", default: 5 })),
});

const LobsterDescribeSchema = Type.Object({
  conversation_id: Type.Optional(Type.String({ description: "会话 ID（留空查全局）" })),
});

const LobsterExpandSchema = Type.Object({
  summary_id: Type.String({ description: "要展开的摘要节点 ID" }),
  max_depth: Type.Optional(Type.Number({ description: "最大展开层数，默认 2", default: 2 })),
});

// ─── Plugin Definition ────────────────────────────────────────────────────────

const lobsterPlugin = {
  id: "lobster-press",
  name: "LobsterPress Memory Engine",
  description:
    "Cognitive memory system for AI Agents: DAG compression, Ebbinghaus forgetting curve, semantic notes, contradiction detection",

  configSchema: {
    parse(value: unknown) {
      const raw =
        value && typeof value === "object" && !Array.isArray(value)
          ? (value as Record<string, unknown>)
          : {};
      return raw;
    },
  },

  register(api: OpenClawPluginApi) {
    const pluginConfig =
      api.pluginConfig && typeof api.pluginConfig === "object"
        ? (api.pluginConfig as Record<string, unknown>)
        : {};

    // ── lobster_grep ───────────────────────────────────────────────────────
    api.registerTool({
      name: "lobster_grep",
      label: "Lobster Grep",
      description:
        "在 LobsterPress 记忆库中全文搜索历史对话（FTS5 + TF-IDF 重排序）。" +
        "当你需要回忆某个决策、技术细节或历史错误时调用此工具。",
      parameters: LobsterGrepSchema,
      execute: async (_toolCallId: string, params: Record<string, unknown>) => {
        return callMcp(pluginConfig, "lobster_grep", params);
      },
    });

    // ── lobster_describe ────────────────────────────────────────────────────
    api.registerTool({
      name: "lobster_describe",
      label: "Lobster Describe",
      description:
        "查看 LobsterPress 的 DAG 摘要层级结构：共有多少层摘要、多少条原始消息已被压缩。",
      parameters: LobsterDescribeSchema,
      execute: async (_toolCallId: string, params: Record<string, unknown>) => {
        return callMcp(pluginConfig, "lobster_describe", params);
      },
    });

    // ── lobster_expand ──────────────────────────────────────────────────────
    api.registerTool({
      name: "lobster_expand",
      label: "Lobster Expand",
      description:
        "将 DAG 摘要节点展开，还原其对应的原始消息（无损检索）。" +
        "当摘要不够详细、需要原始对话时调用。",
      parameters: LobsterExpandSchema,
      execute: async (_toolCallId: string, params: Record<string, unknown>) => {
        return callMcp(pluginConfig, "lobster_expand", params);
      },
    });

    api.logger.info(
      `[lobster-press] Plugin loaded (db=${pluginConfig.dbPath ?? "~/.openclaw/lobster.db"}, ` +
      `provider=${pluginConfig.llmProvider ?? "none (extractive fallback)"})`
    );
  },
};

export default lobsterPlugin;
