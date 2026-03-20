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
        "--namespace",  // v3.6.0 新增（Issue #127 模块四）
        (config.namespace as string) || "default",
      ],
      {
        cwd: join(__dirname, ".."), // 设置工作目录为包根目录，让 Python 找到 mcp_server 模块
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

// v4.0.6: 手动上下文检查工具（Issue #141 降级方案）
const LobsterCheckContextSchema = Type.Object({
  conversation_id: Type.Optional(Type.String({ description: "会话 ID" })),
  force_compress: Type.Optional(Type.Boolean({ description: "是否强制压缩", default: false })),
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

    // ── lobster_check_context (v4.0.6) ───────────────────────────────────────
    // Issue #141 降级方案：手动检查上下文并触发压缩
    api.registerTool({
      name: "lobster_check_context",
      label: "Lobster Check Context",
      description:
        "手动检查上下文使用率并触发压缩（降级方案）。" +
        "当 OpenClaw Gateway 不支持 ContextEngine.afterTurn 钩子时使用。" +
        "建议每隔几轮对话调用一次。",
      parameters: LobsterCheckContextSchema,
      execute: async (_toolCallId: string, params: Record<string, unknown>) => {
        // 获取当前上下文状态
        const describeResult = await callMcp(pluginConfig, "lobster_describe", {
          conversation_id: params.conversation_id,
        });
        
        const stats = (describeResult.details as any)?.result;
        const messageCount = stats?.message_count ?? 0;
        const summaryCount = stats?.summary_count ?? 0;
        
        // 如果消息数太少，不需要压缩
        if (messageCount < 10) {
          return {
            content: [
              {
                type: "text",
                text: `📊 上下文检查：${messageCount} 条消息，无需压缩（< 10 条）`,
              },
            ],
            details: { message_count: messageCount, action: "none" },
          };
        }
        
        // 如果强制压缩或消息数较多，触发压缩
        if (params.force_compress || messageCount > 50) {
          api.logger.info(`[lobster-press] Manual context check: ${messageCount} messages, triggering compress`);
          
          const compressResult = await callMcp(pluginConfig, "lobster_compress", {
            conversation_id: params.conversation_id,
            force: true,
          });
          
          return {
            content: [
              {
                type: "text",
                text: `✅ 上下文检查：${messageCount} 条消息，已触发压缩\n\n${JSON.stringify(compressResult.details, null, 2)}`,
              },
            ],
            details: { message_count: messageCount, action: "compressed", compress_result: compressResult.details },
          };
        }
        
        // 否则只返回状态
        return {
          content: [
            {
              type: "text",
              text: `📊 上下文检查：${messageCount} 条消息，${summaryCount} 条摘要\n\n` +
                `建议：当消息数超过 50 条时，可设置 force_compress=true 触发压缩`,
            },
          ],
          details: { message_count: messageCount, summary_count: summaryCount, action: "none" },
        };
      },
    });

    // ── ContextEngine Registration (v3.3.0) ────────────────────────────────────
    // 参考 lossless-claw 的实现，注册为 ContextEngine，实现自动压缩
    // v4.0.7: 必须同时注册 "default"，阻止 OpenClaw 内置压缩抢先运行（Issue #141 评论）
    const lobsterEngine = {
      info: {
        id: "lobster-press",
        name: "LobsterPress Memory Engine",
        version: "3.3.0",
        ownsCompaction: true,
      },

      // 关键：每次 turn 后自动检查上下文使用率
      // v4.0.0: Focus 主动压缩触发（定时 + 紧急 + 被动三策略）
      async afterTurn(params: any) {
        // v4.0.6: 调试日志 - 确认 afterTurn 被调用（Issue #141 诊断）
        api.logger.info(`[lobster-press] afterTurn called (sessionId=${params?.sessionId ?? "unknown"})`);

        // v4.0.0: Focus 主动压缩触发常量
        const FOCUS_COMPRESSION_INTERVAL = 12;  // 论文建议 10-15，取 12
        const FOCUS_URGENT_THRESHOLD = 0.85;    // 上下文使用率超过 85% 时立即触发

        const db = await this._getDb();
        const threshold = (pluginConfig.contextThreshold as number) ?? 0.8;
        const tokenBudget = params.tokenBudget ?? 128000;

        // v4.0.0: 获取轮次数
        const turnCount = await this._getTurnCount(params.sessionId);

        // 估算当前 token 数量（从 messages 中）
        const currentTokenCount = (params.messages || []).reduce((total: number, msg: any) => {
          let content = "";
          if (typeof msg.content === "string") {
            content = msg.content;
          } else if (Array.isArray(msg.content)) {
            content = msg.content.map((c: any) => c.text || "").join("");
          }
          // 粗略估算：1 token ≈ 4 字符
          return total + Math.ceil(content.length / 4);
        }, 0);

        const ratio = currentTokenCount / tokenBudget;

        // ── Focus 策略一：定时主动提示（每 N 轮）──
        if (turnCount > 0 && turnCount % FOCUS_COMPRESSION_INTERVAL === 0) {
          api.logger.info(
            `[lobster-press] Focus scheduled compression at turn ${turnCount}`
          );

          await callMcp(pluginConfig, "lobster_compress", {
            conversation_id: params.sessionId,
            current_tokens: currentTokenCount,
            token_budget: tokenBudget,
            strategy: 'focus_scheduled',
            force: true,
          });

          // v4.0.0: 定时压缩完成，不注入消息（避免干扰对话）
          return;
        }

        // ── Focus 策略二：紧急触发（上下文使用率过高）──
        if (ratio > FOCUS_URGENT_THRESHOLD) {
          api.logger.warn(
            `[lobster-press] URGENT: Context at ${(ratio * 100).toFixed(1)}% capacity - manual compression recommended`
          );

          // v4.0.0: 紧急警告，但不强制中断（让 Agent 决定是否压缩）
          return;
        }

        // ── Focus 策略三：被动阈值触发（原有逻辑）──
        if (ratio <= threshold) {
          api.logger.info(
            `[lobster-press] Context ${(ratio * 100).toFixed(1)}% ≤ ${threshold * 100}%, no compression needed`
          );
          return;
        }

        api.logger.info(
          `[lobster-press] Context ${(ratio * 100).toFixed(1)}% > ${threshold * 100}%, triggering auto-compress`
        );

        // v3.4.0: 修复 Bug #124 - afterTurn 触发时传 force: true
        callMcp(pluginConfig, "lobster_compress", {
          conversation_id: params.sessionId,
          current_tokens: currentTokenCount,
          token_budget: tokenBudget,
          force: true,  // v3.4.0: TS 层已判断，Python 层直接执行
        }).catch((err) =>
          api.logger.error(`[lobster-press] auto-compress failed: ${err}`)
        );
      },

      // v4.0.0: 辅助方法 - 获取轮次数
      async _getTurnCount(sessionId: string): Promise<number> {
        try {
          const result = await callMcp(pluginConfig, "lobster_describe", {
            conversation_id: sessionId
          });
          // lobster_describe 返回 turn_count（如果数据库实现了 get_turn_count）
          return (result.details as any)?.turn_count ?? 0;
        } catch (err) {
          api.logger.error(`[lobster-press] _getTurnCount failed: ${err}`);
          return 0;
        }
      },

      // v4.0.0: 辅助方法 - 获取数据库实例
      async _getDb(): Promise<any> {
        // 返回空对象，实际调用在 Python 层
        return {};
      },

      // ContextEngine 必需方法：compact
      async compact(p: {
        sessionId: string;
        sessionFile: string;
        tokenBudget?: number;
        force?: boolean;
        currentTokenCount?: number;
      }) {
        api.logger.info(`[lobster-press] compact() called (force=${p.force ?? false})`);

        const result = await callMcp(pluginConfig, "lobster_compress", {
          conversation_id: p.sessionId,
          current_tokens: p.currentTokenCount ?? 0,
          token_budget: p.tokenBudget ?? 128000,
          force: p.force ?? false,
        });

        // v3.5.1: 修复 Bug #126 - 正确的取值路径（tokens_after 在 details.result 里）
        const compressResult = (result.details as any)?.result;
        const tokensAfter = compressResult?.tokens_after ?? 0;
        const tokensSaved = compressResult?.tokens_saved ?? 0;

        return {
          ok: true,
          compacted: true,
          result: {
            tokensBefore: p.currentTokenCount ?? 0,
            tokensAfter: tokensAfter,  // v3.4.0: 真实值
            tokensSaved: tokensSaved,  // v3.4.0: 真实值
            details: result.details,
          },
        };
      },

      // 其他必需方法（暂时用空实现）
      async bootstrap() {
        return { bootstrapped: false, reason: "not implemented" };
      },
      async ingest() {
        return { ingested: true };
      },
      async assemble(p: { messages: any[]; sessionId?: string; tokenBudget?: number }) {
        // v3.6.0: 调用 lobster_assemble 按三层记忆模型拼装上下文（Issue #127 模块一）
        if (!p.sessionId) {
          return { messages: p.messages as any[], estimatedTokens: 0 };
        }

        try {
          const result = await callMcp(pluginConfig, "lobster_assemble", {
            conversation_id: p.sessionId,
            token_budget: p.tokenBudget ?? 8000,
          });

          const assembled = (result.details as any)?.result?.assembled ?? [];
          const totalTokens = (result.details as any)?.result?.total_tokens ?? 0;

          // 将三层记忆转为 messages 格式
          const messages = assembled.map((item: any) => ({
            role: item.role ?? "assistant",
            content: item.content ?? "",
            _tier: item.tier, // 保留层级信息
          }));

          return { messages, estimatedTokens: totalTokens };
        } catch (error) {
          // 失败时返回原始消息
          return { messages: p.messages as any[], estimatedTokens: 0 };
        }
      },

      // v4.0.7: prepareContext 防御线（Issue #141 评论）
      // 每轮对话开始前，OpenClaw 自动调用，将最新摘要注入 system prompt
      async prepareContext(params: { sessionId?: string; sessionKey?: string }) {
        const sessionId = params.sessionId || params.sessionKey;
        if (!sessionId) {
          return null;
        }

        try {
          // 调用 lobster_describe 获取最新摘要
          const result = await callMcp(pluginConfig, "lobster_describe", {
            conversation_id: sessionId,
          });

          const summaryText = (result.details as any)?.result?.latest_summary;
          if (!summaryText) {
            return null;
          }

          // 返回摘要内容，注入到 system prompt
          return `[Memory Context]\n${summaryText}`;
        } catch (error) {
          api.logger.error(`[lobster-press] prepareContext failed: ${error}`);
          return null;
        }
      },
    };

    // 注册为 ContextEngine
    // v4.0.7: 必须同时注册 "default"，阻止 OpenClaw 内置压缩抢先运行（Issue #141 评论）
    api.registerContextEngine("lobster-press", () => lobsterEngine);
    api.registerContextEngine("default", () => lobsterEngine);  // ← 关键：抢占 default

    // v4.0.6: 调试日志 - 确认 ContextEngine 注册（Issue #141 诊断）
    api.logger.info(`[lobster-press] Plugin loaded (db=${pluginConfig.dbPath ?? "~/.openclaw/lobster.db"}, ` +
      `provider=${pluginConfig.llmProvider ?? "none (extractive fallback)"})`);
    api.logger.info(
      `[lobster-press] ContextEngine registered (threshold=${(pluginConfig.contextThreshold as number) ?? 0.8})`
    );
    api.logger.info(
      `[lobster-press] DEBUG: ContextEngine.afterTurn should be called after each turn`
    );
    api.logger.warn(
      `[lobster-press] DEBUG: If you don't see "[lobster-press] afterTurn called" logs, ` +
      `your OpenClaw Gateway may not support ContextEngine.afterTurn hook`
    );
  },
};

export default lobsterPlugin;
