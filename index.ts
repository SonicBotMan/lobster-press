/**
 * @sonicbotman/lobster-press — Cognitive Memory System for AI Agents
 *
 * DAG-based conversation summarization with Ebbinghaus forgetting curve,
 * semantic notes, contradiction detection.
 */
import { spawn, type ChildProcess } from "node:child_process";
import { join } from "node:path";
import { Type } from "@sinclair/typebox";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

// Python MCP Server 进程（懒启动）
let mcpProcess: ChildProcess | null = null;
let mcpReady = false;

/** 启动 Python MCP Server */
function ensureMcpServer(config: Record<string, unknown>): ChildProcess {
  if (mcpProcess && mcpReady) return mcpProcess;

  const dbPath = (config.dbPath as string) || join(process.env.HOME ?? "~", ".openclaw/lobster.db");
  const pythonCmd = process.env.LOBSTER_PYTHON ?? "python3";

  mcpProcess = spawn(pythonCmd, [
    "-m", "mcp_server.lobster_mcp_server",
    "--db", dbPath,
    "--provider", (config.llmProvider as string) || "",
    "--model", (config.llmModel as string) || "",
  ], {
    env: {
      ...process.env,
      LOBSTER_LLM_API_KEY: (config.llmApiKey as string) || process.env.LOBSTER_LLM_API_KEY || "",
    },
    stdio: ["pipe", "pipe", "inherit"],
  });

  mcpReady = true;

  mcpProcess.on("exit", () => {
    mcpProcess = null;
    mcpReady = false;
  });

  return mcpProcess;
}

/** 向 Python MCP Server 发送请求 */
async function callMcp(
  config: Record<string, unknown>,
  toolName: string,
  args: Record<string, unknown>
): Promise<{ content: Array<{ type: "text"; text: string }>; details: unknown }> {
  const proc = ensureMcpServer(config);

  return new Promise((resolve, reject) => {
    const request = JSON.stringify({
      method: "tools/call",
      params: { name: toolName, arguments: args },
    }) + "\n";

    let output = "";

    const onData = (chunk: Buffer) => {
      output += chunk.toString();
      const lines = output.split("\n");
      for (const line of lines.slice(0, -1)) {
        if (line.trim()) {
          proc.stdout?.off("data", onData);
          try {
            const result = JSON.parse(line);
            resolve({
              content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
              details: result,
            });
          } catch (e) {
            reject(e);
          }
          return;
        }
      }
      output = lines[lines.length - 1] ?? "";
    };

    proc.stdout?.on("data", onData);
    proc.stdin?.write(request);

    setTimeout(() => {
      proc.stdout?.off("data", onData);
      reject(new Error("lobster-press MCP tool call timed out after 30s"));
    }, 30_000);
  });
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
