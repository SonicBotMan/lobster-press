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
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { readFileSync, appendFileSync } from "node:fs";
import { Type } from "@sinclair/typebox";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

// v4.0.19: 修复 __dirname 作用域问题（Issue #155 Bug #1）
// __dirname 必须在模块顶层定义，ensureMcpServer 需要使用它
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

let LOBSTERPRESS_VERSION = "unknown";
try {
  const packageJson = JSON.parse(readFileSync(join(__dirname, "package.json"), "utf-8"));
  LOBSTERPRESS_VERSION = packageJson.version ?? "unknown";
} catch {
  // 打包环境下路径可能变化，降级为 unknown
}

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
// v4.0.14: 移除全局 stdoutBuffer，改为闭包变量（Issue #152 Bug #2）
// let stdoutBuffer = "";  // ← 移除
// v4.0.17: 改为 per-session 锁，避免跨会话误阻塞（Issue #153 Bug #2）
const compressingSessions = new Set<string>();

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

// v4.0.17: 根据 LLM provider 获取 token 估算系数（Issue #153 Bug #5）
function getTokenEstimationCoefficients(provider?: string): { chinese: number; other: number } {
  switch (provider?.toLowerCase()) {
    case "deepseek":
    case "zhipu":
    case "glm":
    case "wenxin":
    case "qwen":
      // 中文优化模型：中文字符约 1-1.2 tokens
      return { chinese: 1.2, other: 4 };
    case "claude":
    case "anthropic":
      // Claude: 中文字符约 2 tokens
      return { chinese: 2.0, other: 4 };
    case "gemini":
    case "google":
      // Gemini: 中文字符约 1-1.5 tokens
      return { chinese: 1.5, other: 4 };
    case "openai":
    case "gpt":
    case "mistral":
    default:
      // GPT/默认: 中文字符约 1.5 tokens
      return { chinese: 1.5, other: 4 };
  }
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

  // v4.0.14: 改为闭包变量，避免多进程/多会话数据串流（Issue #152 Bug #2）
  let localBuffer = "";

  proc.stdout.on("data", (chunk: Buffer) => {
    localBuffer += chunk.toString("utf8");
    const lines = localBuffer.split("\n");
    localBuffer = lines.pop() ?? "";

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
        cwd: join(__dirname, ".."), // v4.0.53: 修复 cwd 路径错误 - dist/index.js 的 __dirname 指向 dist/，需要回到包根目录
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
    // v4.0.26: 修复竞态条件，只有当前进程成功启动才清除（Issue #167 Bug #1）
    // 避免并发请求时启动多个 Python 子进程
    if (mcpProcess && mcpReady) {
      bootPromise = null;
    }
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
      
      // v4.0.17: 添加字段校验（Issue #153 Bug #6）
      const validated: Record<string, unknown> = {};
      
      // dbPath: 必须是字符串
      if (typeof raw.dbPath === "string") {
        validated.dbPath = raw.dbPath;
      }
      
      // contextThreshold: 必须是数字，且在 0-1 之间
      if (typeof raw.contextThreshold === "number" && 
          raw.contextThreshold >= 0 && raw.contextThreshold <= 1) {
        validated.contextThreshold = raw.contextThreshold;
      } else if (typeof raw.contextThreshold === "string") {
        // 尝试解析字符串
        const parsed = parseFloat(raw.contextThreshold);
        if (!isNaN(parsed) && parsed >= 0 && parsed <= 1) {
          validated.contextThreshold = parsed;
        }
      }
      
      // llmProvider: 必须是字符串
      if (typeof raw.llmProvider === "string") {
        validated.llmProvider = raw.llmProvider;
      }
      
      // llmModel: 必须是字符串
      if (typeof raw.llmModel === "string") {
        validated.llmModel = raw.llmModel;
      }
      
      // llmApiKey: 必须是字符串
      if (typeof raw.llmApiKey === "string") {
        validated.llmApiKey = raw.llmApiKey;
      }
      
      // namespace: 必须是字符串
      if (typeof raw.namespace === "string") {
        validated.namespace = raw.namespace;
      }
      
      // freshTailCount: 必须是正整数
      if (typeof raw.freshTailCount === "number" && 
          Number.isInteger(raw.freshTailCount) && raw.freshTailCount > 0) {
        validated.freshTailCount = raw.freshTailCount;
      }
      
      // maxContextTokens: 必须是正整数（v4.0.20: Issue #156 Bug #3）
      // v4.0.27: 添加默认值 40000（Issue #166 P1-1）
      if (typeof raw.maxContextTokens === "number" &&
          Number.isInteger(raw.maxContextTokens) && raw.maxContextTokens > 0) {
        validated.maxContextTokens = raw.maxContextTokens;
      } else if (typeof raw.maxContextTokens === "string") {
        const parsed = parseInt(raw.maxContextTokens, 10);
        if (!isNaN(parsed) && parsed > 0) {
          validated.maxContextTokens = parsed;
        }
      } else {
        // 用户未设置时使用默认值
        validated.maxContextTokens = 40000;
      }

      // registerAsDefault: 必须是布尔值（v4.0.17: Issue #153 Bug #4）
      if (typeof raw.registerAsDefault === "boolean") {
        validated.registerAsDefault = raw.registerAsDefault;
      }
      
      // 其他字段直接透传
      for (const key of Object.keys(raw)) {
        if (!(key in validated)) {
          validated[key] = raw[key];
        }
      }
      
      return validated;
    },
  },

  register(api: OpenClawPluginApi) {
    const pluginConfig =
      api.pluginConfig && typeof api.pluginConfig === "object"
        ? (api.pluginConfig as Record<string, unknown>)
        : {};

    // v4.0.48: Debug logging - write to file to bypass all loggers (ESM compatible)
    const debugLog = (msg: string) => {
      const logLine = `[${new Date().toISOString()}] [lobster-press] DEBUG: ${msg}\n`;
      try { appendFileSync('/tmp/lobster-debug.log', logLine); } catch {}
    };
    debugLog('register() called');
    debugLog(`pluginConfig=${JSON.stringify({
      dbPath: pluginConfig.dbPath,
      llmProvider: pluginConfig.llmProvider,
      lifecycleEnabled: pluginConfig.lifecycleEnabled,
      contextThreshold: pluginConfig.contextThreshold,
      maxContextTokens: pluginConfig.maxContextTokens,
    })}`);
    debugLog(`api object methods: ${Object.keys(api).join(', ')}`);

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
        
        // v4.0.18: 修复解析路径（Issue #154 Bug #3）
        const text = describeResult.content?.[0]?.text;
        const stats = text ? JSON.parse(text) : {};
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
          
          // v4.0.22: 提取实际压缩结果，不透传 McpEnvelope 内部字段（Issue #158 Bug #1）
          const compressText = compressResult.content?.[0]?.text;
          const compressData = compressText ? JSON.parse(compressText) : {};
          
          return {
            content: [
              {
                type: "text",
                text: `✅ 上下文检查：${messageCount} 条消息，已触发压缩\n\n${JSON.stringify(compressData, null, 2)}`,
              },
            ],
            details: { message_count: messageCount, action: "compressed", compress_result: compressData },
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
        version: LOBSTERPRESS_VERSION,  // v4.0.17: 从 package.json 读取（Issue #153 Bug #3）
        ownsCompaction: true,
      },

      // 关键：每次 turn 后自动检查上下文使用率
      // v4.0.0: Focus 主动压缩触发（定时 + 紧急 + 被动三策略）
      // v4.0.23: 异常处理策略文档化（Issue #160 建议 #2）
      // v4.0.30: 三种策略均捕获异常，不中断对话（Issue #169）
      //
      // ── 异常处理设计决策 ──
      // 三种策略均捕获异常并记录日志，不向上冒泡：
      // 压缩失败不应中断用户对话，由日志监控告警。
      async afterTurn(params: any) {
        // v4.0.6: 调试日志 - 确认 afterTurn 被调用（Issue #141 诊断）
        api.logger.info(`[lobster-press] afterTurn called (sessionId=${params?.sessionId ?? "unknown"})`);

        // v4.0.0: Focus 主动压缩触发常量
        const FOCUS_COMPRESSION_INTERVAL = 12;  // 论文建议 10-15，取 12
        const FOCUS_URGENT_THRESHOLD = 0.85;    // 上下文使用率超过 85% 时立即触发

        // v4.0.14: 删除无用的 _getDb() 调用（Issue #152 Bug #5）
        const threshold = (pluginConfig.contextThreshold as number) ?? 0.8;
        // v4.0.26: 优先读取 pluginConfig.maxContextTokens（Issue #167 Bug #2）
        const tokenBudget = (pluginConfig.maxContextTokens as number) ?? params.tokenBudget ?? 128000;

        // v4.0.0: 获取轮次数
        const turnCount = await this._getTurnCount(params.sessionId);

        // v4.0.17: 根据 llmProvider 动态调整 token 估算系数（Issue #153 Bug #5）
        const coef = getTokenEstimationCoefficients(pluginConfig.llmProvider as string);
        
        const currentTokenCount = (params.messages || []).reduce((total: number, msg: any) => {
          let content = "";
          if (typeof msg.content === "string") {
            content = msg.content;
          } else if (Array.isArray(msg.content)) {
            content = msg.content.map((c: any) => c.text || "").join("");
          }
          
          // 根据 provider 动态调整估算系数
          const chineseCharCount = (content.match(/[\u4e00-\u9fff]/g) || []).length;
          const otherCharCount = content.length - chineseCharCount;
          const estimated = Math.ceil(chineseCharCount * coef.chinese + otherCharCount / coef.other);
          
          return total + estimated;
        }, 0);

        const ratio = currentTokenCount / tokenBudget;

        // ── Focus 策略一：定时主动提示（每 N 轮）──
        if (turnCount > 0 && turnCount % FOCUS_COMPRESSION_INTERVAL === 0) {
          api.logger.info(
            `[lobster-press] Focus scheduled compression at turn ${turnCount}`
          );

          // v4.0.30: 添加异常捕获（Issue #169）
          try {
            await callMcp(pluginConfig, "lobster_compress", {
              conversation_id: params.sessionId,
              current_tokens: currentTokenCount,
              token_budget: tokenBudget,
              strategy: 'focus_scheduled',
              force: true,
            });
          } catch (err) {
            api.logger.error(`[lobster-press] scheduled compression failed at turn ${turnCount}: ${err}`);
            // 定时压缩失败不中断对话，记录日志后继续
          }

          // v4.0.0: 定时压缩完成，不注入消息（避免干扰对话）
          return;
        }

        // ── Focus 策略二：紧急触发（上下文使用率过高）──
        if (ratio > FOCUS_URGENT_THRESHOLD) {
          api.logger.warn(
            `[lobster-press] URGENT compression triggered: context at ${(ratio * 100).toFixed(1)}%`
          );
          
          // v4.0.9: 修复 P0-1 - 紧急压缩必须执行，不能只打日志（Issue #142）
          // v4.0.30: 添加异常捕获（Issue #169）
          try {
            await callMcp(pluginConfig, "lobster_compress", {
              conversation_id: params.sessionId,
              current_tokens: currentTokenCount,
              token_budget: tokenBudget,
              strategy: "urgent",
              force: true,
            });
          } catch (err) {
            api.logger.error(`[lobster-press] URGENT compression failed (context at ${(ratio * 100).toFixed(1)}%): ${err}`);
            // 紧急压缩失败需要记录，但不应中断用户对话
          }
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

        // v4.0.17: 改为 per-session 锁，避免跨会话误阻塞（Issue #153 Bug #2）
        if (compressingSessions.has(params.sessionId)) {
          api.logger.warn(`[lobster-press] Compression already in progress for session ${params.sessionId}, skipping`);
          return;
        }
        
        compressingSessions.add(params.sessionId);
        try {
          await callMcp(pluginConfig, "lobster_compress", {
            conversation_id: params.sessionId,
            current_tokens: currentTokenCount,
            token_budget: tokenBudget,
            force: true,  // v3.4.0: TS 层已判断，Python 层直接执行
          });
        } catch (err) {
          api.logger.error(`[lobster-press] auto-compress failed: ${err}`);
        } finally {
          compressingSessions.delete(params.sessionId);
        }
      },

      // v4.0.0: 辅助方法 - 获取轮次数
      async _getTurnCount(sessionId: string): Promise<number> {
        try {
          const result = await callMcp(pluginConfig, "lobster_describe", {
            conversation_id: sessionId
          });
          // v4.0.14: 正确解析 MCP 返回值
          const text = result.content?.[0]?.text;
          if (!text) return 0;
          const data = JSON.parse(text);
          return data?.turn_count ?? 0;
        } catch (err) {
          api.logger.error(`[lobster-press] _getTurnCount failed: ${err}`);
          return 0;
        }
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

        // v4.0.21: 统一使用 content[0].text 解析路径（Issue #157 Bug #1）
        // v4.0.22: 不透传 McpEnvelope 内部字段（Issue #158 Bug #1 同类问题）
        const compressText = result.content?.[0]?.text;
        const compressResult = compressText ? JSON.parse(compressText) : {};
        const tokensAfter = compressResult?.tokens_after ?? 0;
        const tokensSaved = compressResult?.tokens_saved ?? 0;

        return {
          ok: true,
          compacted: true,
          result: {
            tokensBefore: p.currentTokenCount ?? 0,
            tokensAfter: tokensAfter,  // v3.4.0: 真实值
            tokensSaved: tokensSaved,  // v3.4.0: 真实值
            details: compressResult,   // v4.0.22: 使用实际压缩结果
          },
        };
      },

      // v4.0.18: 实现基本的 bootstrap 和 ingest（Issue #154 Bug #4）
      async bootstrap() {
        try {
          // 调用 lobster_status 验证数据库是否可用
          const statusResult = await callMcp(pluginConfig, "lobster_status", {
            conversation_id: "bootstrap-test",
          });
          const text = statusResult.content?.[0]?.text;
          const status = text ? JSON.parse(text) : {};
          
          // v4.0.21: 修复 if 判断逻辑（Issue #157 Bug #3）
          if (status.error) {
            if (status.error.includes("not found")) {
              // 数据库正常，只是没有这个 conversation
              return { bootstrapped: true };
            }
            // 真实错误
            return { bootstrapped: false, reason: status.error };
          }
          // 无错误，数据库正常
          return { bootstrapped: true };
        } catch (error) {
          return { bootstrapped: false, reason: String(error) };
        }
      },
      
      async ingest(params: { sessionId: string; sessionKey?: string; message: any; isHeartbeat?: boolean }) {
        // v4.0.20: 调用 lobster_ingest MCP 工具存储消息（Issue #156 Bug #2）
        // v4.0.28: 与 prepareContext 保持一致，优先 sessionId，fallback 到 sessionKey（Issue #172）
        const conversationId = params.sessionId || params.sessionKey;
        if (!conversationId) {
          api.logger.warn(`[lobster-press] ingest called with no sessionId or sessionKey, skipping`);
          return { ingested: false, error: "no conversationId", conversation_id: "" };
        }
        
        try {
          // 构建消息对象
          // v4.0.26: 移除 crypto.randomUUID() 兼容性问题（Issue #167 Bug #5）
          const messages = [{
            id: params.message?.id ?? `msg-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
            role: params.message?.role || "user",
            content: typeof params.message?.content === "string" 
              ? params.message.content 
              : JSON.stringify(params.message?.content || {}),
            timestamp: params.message?.timestamp || new Date().toISOString(),
          }];
          
          // 调用 lobster_ingest MCP 工具
          const result = await callMcp(pluginConfig, "lobster_ingest", {
            conversation_id: conversationId,
            messages: messages,
          });
          
          // 解析返回结果
          const responseText = result?.content?.[0]?.text;
          const response = responseText ? JSON.parse(responseText) : {};
          
          return {
            ingested: response.ingested > 0,
            count: response.ingested || 0,
            conversation_id: conversationId,
          };
        } catch (error) {
          // v4.0.21: 修复降级逻辑，返回失败状态而非掩盖错误（Issue #157 Bug #2）
          // v4.0.27: 添加警告日志（Issue #166 P0-2）
          api.logger.warn(`[lobster-press] ingest failed for session ${conversationId}: ${error}`);
          return {
            ingested: false,
            error: String(error),
            conversation_id: conversationId,
          };
        }
      },
      async assemble(p: { messages: any[]; sessionId?: string; tokenBudget?: number }) {
        // v3.6.0: 调用 lobster_assemble 按三层记忆模型拼装上下文（Issue #127 模块一）
        if (!p.sessionId) {
          return { messages: p.messages as any[], estimatedTokens: 0 };
        }

        try {
          const result = await callMcp(pluginConfig, "lobster_assemble", {
            conversation_id: p.sessionId,
            token_budget: p.tokenBudget ?? 128000,
          });

          // v4.0.19: 统一解析路径（Issue #155 Bug #4）
          // v4.0.23: 移除多余的 .result 中间层（Issue #160 建议 #1）
          const text = result.content?.[0]?.text;
          const data = text ? JSON.parse(text) : {};
          const assembled = data?.assembled ?? [];
          const totalTokens = data?.total_tokens ?? 0;

          // 将三层记忆转为 messages 格式
          const messages = assembled.map((item: any) => ({
            role: item.role ?? "assistant",
            content: item.content ?? "",
            _tier: item.tier, // 保留层级信息
          }));

          return { messages, estimatedTokens: totalTokens };
        } catch (error) {
          // v4.0.29: 添加错误日志（Issue #170）
          api.logger.error(`[lobster-press] assemble failed for session ${p.sessionId}: ${error}`);
          return { messages: p.messages as any[], estimatedTokens: 0 };
        }
      },

      // v4.0.7: prepareContext 防御线（Issue #141 评论）
      // v4.0.9: 修复 P0-2 - latest_summary 字段不存在，改用两步调用（Issue #142）
      // v4.0.14: 修复 P1-4 - MCP 返回结构解析错误（Issue #152 Bug #4）
      // 每轮对话开始前，OpenClaw 自动调用，将最新摘要注入 system prompt
      async prepareContext(params: { sessionId?: string; sessionKey?: string }) {
        const sessionId = params.sessionId || params.sessionKey;
        if (!sessionId) {
          return null;
        }

        try {
          // 第一步：调用 lobster_describe 获取摘要结构
          const describe = await callMcp(pluginConfig, "lobster_describe", {
            conversation_id: sessionId,
          });
          
          // v4.0.14: 正确解析 MCP 返回值（从 content[0].text 解析 JSON）
          const describeText = describe.content?.[0]?.text;
          if (!describeText) {
            return null;
          }
          const describeResult = JSON.parse(describeText);
          
          const byDepth = describeResult?.by_depth ?? {};
          const depths = Object.keys(byDepth).map(Number).sort((a, b) => b - a);
          
          // 如果没有摘要，返回 null
          if (depths.length === 0) {
            return null;
          }
          
          // 获取最高深度的第一个摘要的 summary_id
          const topSummaryId = byDepth[depths[0]]?.[0]?.summary_id;
          if (!topSummaryId) {
            return null;
          }
          
          // 第二步：调用 lobster_expand 获取摘要内容（v4.0.17: Issue #153 Bug #1）
          // lobster_describe 不接受 summary_id 参数，应该用 lobster_expand
          const detail = await callMcp(pluginConfig, "lobster_expand", {
            summary_id: topSummaryId,
            max_depth: 1,  // 只展开一层，获取直接子节点
          });
          
          // v4.0.20: 统一使用 content[0].text 解析路径（Issue #156 Bug #1）
          const expandText = detail.content?.[0]?.text;
          const expandResult = expandText ? JSON.parse(expandText) : {};
          const messages = expandResult?.messages ?? [];
          
          if (messages.length === 0) {
            return null;
          }
          
          // v4.0.26: 修复截断逻辑（Issue #167 Bug #3）
          // prepareContext 用于注入摘要到 system prompt，不是全量上下文
          // 使用固定 4000 字符上限，避免逻辑混淆
          const maxContextChars = 4000;
          const content = messages
            .slice(-5)  // 最新 5 条（而非前 5 条）
            .map((m: any) => `[${m.role}]: ${m.content ?? ''}`)
            .join('\n')
            .slice(0, maxContextChars);
          
          return content ? `[Memory Context]\n${content}` : null;
        } catch (error) {
          api.logger.error(`[lobster-press] prepareContext failed: ${error}`);
          return null;
        }
      },
    };

    // 注册为 ContextEngine
    // v4.0.17: 添加配置选项控制是否抢占 default（Issue #153 Bug #4）
    api.registerContextEngine("lobster-press", () => lobsterEngine);
    
    const registerAsDefault = pluginConfig.registerAsDefault !== false;  // 默认 true
    if (registerAsDefault) {
      api.registerContextEngine("default", () => lobsterEngine);
      api.logger.info(`[lobster-press] Registered as both "lobster-press" and "default" ContextEngine`);
    } else {
      api.logger.info(`[lobster-press] Registered as "lobster-press" ContextEngine only`);
    }

    // v4.0.6: 调试日志 - 确认 ContextEngine 注册（Issue #141 诊断）
    api.logger.info(`[lobster-press] Plugin loaded (db=${pluginConfig.dbPath ?? "~/.openclaw/lobster.db"}, ` +
      `provider=${pluginConfig.llmProvider ?? "none (extractive fallback)"})`);
    api.logger.info(
      `[lobster-press] ContextEngine registered (threshold=${(pluginConfig.contextThreshold as number) ?? 0.8})`
    );
    // v4.0.21: 降级为 info 级别（Issue #157 Bug #4）
    api.logger.info(
      `[lobster-press] Note: If you don't see "[lobster-press] afterTurn called" logs, ` +
      `your OpenClaw Gateway may not support ContextEngine.afterTurn hook`
    );
    
    // ── Lifecycle Hooks (v4.0.38: Issue #183 双模式插件) ───────────────────────
    // 参考 MemOS OpenClaw Plugin：使用 lifecycle hooks 作为 ContextEngine 的降级方案
    // 当 OpenClaw Gateway 不支持 ContextEngine.afterTurn 时，通过 lifecycle hooks 实现记忆管理
    
    // TODO(OpenClaw Issue #52810): 正在验证 hooks 是否触发
    // v4.0.50: 恢复 lifecycle hooks 进行实际 agent 交互测试
    
    // v4.0.46: Debug logging - lifecycle hooks
    debugLog('About to register lifecycle hooks...');
    debugLog(`api.on type: ${typeof api.on}`);

    // 1. before_agent_start: 召回记忆
    debugLog('Registering before_agent_start hook...');
    api.on("before_agent_start", async (event: any, ctx: any) => {
      // Debug: hook 被调用
      debugLog(`HOOK FIRED: before_agent_start, ctx.sessionId=${ctx?.sessionId}`);
      
      // 检查是否启用 lifecycle 模式
      const lifecycleEnabled = pluginConfig.lifecycleEnabled !== false;  // 默认 true
      debugLog(`before_agent_start: lifecycleEnabled=${lifecycleEnabled}`);
      if (!lifecycleEnabled) {
        debugLog('before_agent_start: lifecycle disabled, skipping');
        return;
      }
      
      // 获取 conversation_id
      const conversationId = ctx?.sessionId || ctx?.sessionKey;
      debugLog(`before_agent_start: conversationId=${conversationId}`);
      if (!conversationId) {
        debugLog(`before_agent_start: no conversationId, ctx keys=${Object.keys(ctx || {}).join(',')}`);
        return;
      }
      
      // 检查 prompt 是否存在
      const promptLength = event?.prompt?.length || 0;
      debugLog(`before_agent_start: prompt length=${promptLength}`);
      if (!event?.prompt || promptLength < 3) {
        debugLog('before_agent_start: no prompt or too short, skipping');
        return;
      }
      
      try {
        api.logger.info(`[lobster-press] Lifecycle: before_agent_start for session ${conversationId}`);
        
        // 调用 lobster_assemble 获取相关记忆
        const result = await callMcp(pluginConfig, "lobster_assemble", {
          conversation_id: conversationId,
          token_budget: pluginConfig.maxContextTokens ?? 128000,
        });
        
        // 解析返回结果
        const text = result.content?.[0]?.text;
        const data = text ? JSON.parse(text) : {};
        const assembled = data?.assembled ?? [];
        
        if (assembled.length === 0) {
          api.logger.info(`[lobster-press] Lifecycle: no memories found for session ${conversationId}`);
          return;
        }
        
        // 将记忆格式化为上下文
        const memoryContext = assembled
          .slice(-10)  // 最新 10 条记忆
          .map((item: any) => `[${item.tier || 'memory'}]: ${item.content || ''}`)
          .join('\n\n')
          .slice(0, 8000);  // 限制 8000 字符
        
        if (!memoryContext) return;
        
        api.logger.info(`[lobster-press] Lifecycle: injected ${assembled.length} memories (${memoryContext.length} chars)`);
        
        // 返回 prependContext 注入记忆
        return {
          prependContext: `[LobsterPress Memory Context]\n${memoryContext}`,
        };
      } catch (error) {
        api.logger.warn(`[lobster-press] Lifecycle: before_agent_start failed: ${error}`);
      }
    });
    debugLog('before_agent_start hook registered');

    // 2. agent_end: 写入记忆
    debugLog('Registering agent_end hook...');
    api.on("agent_end", async (event: any, ctx: any) => {
      // Debug: hook 被调用
      debugLog(`HOOK FIRED: agent_end, event.success=${event?.success}, ctx.sessionId=${ctx?.sessionId}`);
      
      // 检查是否启用 lifecycle 模式
      const lifecycleEnabled = pluginConfig.lifecycleEnabled !== false;  // 默认 true
      debugLog(`agent_end: lifecycleEnabled=${lifecycleEnabled}`);
      if (!lifecycleEnabled) {
        debugLog('agent_end: lifecycle disabled, skipping');
        return;
      }
      
      // 检查是否成功
      const hasMessages = event?.messages?.length > 0;
      debugLog(`agent_end: success=${event?.success}, hasMessages=${hasMessages}`);
      if (!event?.success || !hasMessages) {
        debugLog('agent_end: event not successful or no messages, skipping');
        return;
      }
      
      // 获取 conversation_id
      const conversationId = ctx?.sessionId || ctx?.sessionKey;
      debugLog(`agent_end: conversationId=${conversationId}`);
      if (!conversationId) {
        debugLog(`agent_end: no conversationId, ctx keys=${Object.keys(ctx || {}).join(',')}`);
        return;
      }
      
      try {
        api.logger.info(`[lobster-press] Lifecycle: agent_end for session ${conversationId}`);
        
        // 提取最后一条对话（user + assistant）
        const messages = event.messages.slice(-2).map((msg: any) => ({
          id: msg.id || `msg-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
          role: msg.role || "user",
          content: typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content || {}),
          timestamp: msg.timestamp || new Date().toISOString(),
        }));
        
        if (messages.length === 0) return;
        
        // 调用 lobster_ingest 保存消息
        const result = await callMcp(pluginConfig, "lobster_ingest", {
          conversation_id: conversationId,
          messages: messages,
        });
        
        // 解析返回结果
        const responseText = result?.content?.[0]?.text;
        const response = responseText ? JSON.parse(responseText) : {};
        
        if (response.ingested > 0) {
          api.logger.info(`[lobster-press] Lifecycle: ingested ${response.ingested} messages for session ${conversationId}`);
          
          // 检查是否需要压缩（消息数 > 50）
          const describeResult = await callMcp(pluginConfig, "lobster_describe", {
            conversation_id: conversationId,
          });
          
          const describeText = describeResult.content?.[0]?.text;
          const stats = describeText ? JSON.parse(describeText) : {};
          const messageCount = stats?.message_count ?? 0;
          
          if (messageCount > 50) {
            api.logger.info(`[lobster-press] Lifecycle: triggering compress for session ${conversationId} (${messageCount} messages)`);
            
            // 调用 lobster_compress 压缩记忆
            await callMcp(pluginConfig, "lobster_compress", {
              conversation_id: conversationId,
              force: false,
            });
          }
        }
      } catch (error) {
        api.logger.warn(`[lobster-press] Lifecycle: agent_end failed: ${error}`);
      }
    });
    debugLog('agent_end hook registered');
    
    console.log(`[${new Date().toISOString()}] [lobster-press] DEBUG: All lifecycle hooks registered successfully`);
    api.logger.info(`[lobster-press] Lifecycle hooks registered (before_agent_start + agent_end)`);
    // END: lifecycle hooks (v4.0.50: re-enabled for testing)
  },
};

export default lobsterPlugin;
