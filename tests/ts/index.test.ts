/**
 * LobsterPress Plugin - Production Test Suite
 *
 * Tests the actual plugin code with mocked MCP server IPC.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ─── Mock setup (must be before any imports that use them) ───

let fakeStdoutCallback: ((chunk: Buffer) => void) | null = null;

vi.mock('node:child_process', () => ({
  spawn: vi.fn(() => {
    const proc = {
      stdin: {
        write: vi.fn((data: string) => {
          const msg = JSON.parse(data.trim());
          setTimeout(() => {
            if (!fakeStdoutCallback) return;
            let result: Record<string, unknown>;
            switch (msg.params?.name) {
              case 'lobster_status':
                result = { status: 'ok' };
                break;
              case 'lobster_describe':
                result = { message_count: 25, summary_count: 3, turn_count: 12, by_depth: {} };
                break;
              case 'lobster_compress':
                result = { compressed: true, tokens_after: 5000, tokens_saved: 20000 };
                break;
              case 'lobster_ingest':
                result = { ingested: 2 };
                break;
              case 'lobster_assemble':
                result = { assembled: [{ role: 'assistant', content: 'test memory', tier: 'semantic' }], total_tokens: 500 };
                break;
              case 'lobster_sweep':
                result = { swept: 5 };
                break;
              default:
                result = {};
            }
            const response = { requestId: msg.requestId, status: 'ok', result };
            fakeStdoutCallback!(Buffer.from(JSON.stringify(response) + '\n'));
          }, 10);
        }),
      },
      stdout: {
        on: vi.fn((event: string, cb: (chunk: Buffer) => void) => {
          if (event === 'data') {
            fakeStdoutCallback = cb;
            setTimeout(() => cb(Buffer.from(JSON.stringify({ type: 'lobster-press/ready' }) + '\n')), 30);
          }
        }),
      },
      stderr: { on: vi.fn() },
      on: vi.fn(),
      once: vi.fn(),
      kill: vi.fn(),
    };
    return proc;
  }),
}));

vi.mock('node:fs', () => ({
  readFileSync: vi.fn(() => JSON.stringify({ version: '5.0.3' })),
  appendFileSync: vi.fn(),
  writeFileSync: vi.fn(),
  existsSync: vi.fn(() => false),
}));

// Import after mocks
// @ts-expect-error — ESM import of project module
import pluginDefault from '../../index.js';

// The plugin export shape: definePluginEntry returns { id, name, description, configSchema, register }
const plugin = pluginDefault as {
  id?: string;
  name?: string;
  description?: string;
  configSchema: { parse: (v: unknown) => Record<string, unknown> };
  register: (api: any) => void;
};

// ─── Mock API ───

function createMockApi(config: Record<string, unknown> = {}) {
  const registeredTools: Array<{ name: string; execute: Function }> = [];
  const registeredEngines: Array<{ id: string; factory: Function }> = [];

  return {
    logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
    pluginConfig: {
      dbPath: ':memory:',
      contextThreshold: 0.8,
      maxContextTokens: 40000,
      namespace: 'test',
      ...config,
    },
    registerTool: vi.fn((tool: any) => registeredTools.push(tool)),
    registerContextEngine: vi.fn((id: string, factory: Function) =>
      registeredEngines.push({ id, factory }),
    ),
    on: vi.fn(),
    get registeredTools() {
      return registeredTools;
    },
    get registeredEngines() {
      return registeredEngines;
    },
  };
}

// ─── Tests ───

describe('LobsterPress Plugin', () => {
  let mockApi: ReturnType<typeof createMockApi>;

  beforeEach(() => {
    vi.clearAllMocks();
    fakeStdoutCallback = null;
    mockApi = createMockApi();
  });

  // ── Plugin Registration ──

  describe('Plugin registration', () => {
    it('registers 5 tools', () => {
      plugin.register(mockApi);
      expect(mockApi.registerTool).toHaveBeenCalledTimes(5);
    });

    it('registers tools with correct names', () => {
      plugin.register(mockApi);
      const names = mockApi.registeredTools.map((t) => t.name);
      expect(names).toContain('lobster_grep');
      expect(names).toContain('lobster_describe');
      expect(names).toContain('lobster_expand');
      expect(names).toContain('lobster_check_context');
      expect(names).toContain('lobster_configure');
    });

    it('registers context engine', () => {
      plugin.register(mockApi);
      expect(mockApi.registerContextEngine).toHaveBeenCalled();
      const ids = mockApi.registeredEngines.map((e) => e.id);
      expect(ids).toContain('lobster-press');
      expect(ids).toContain('default');
    });

    it('registers lifecycle hooks when api.on is available', () => {
      plugin.register(mockApi);
      expect(mockApi.on).toHaveBeenCalledWith('before_agent_start', expect.any(Function));
      expect(mockApi.on).toHaveBeenCalledWith('agent_end', expect.any(Function));
    });

    it('does not crash when api.on is unavailable', () => {
      const apiNoOn = { ...mockApi, on: undefined };
      expect(() => plugin.register(apiNoOn)).not.toThrow();
    });
  });

  // ── configSchema.parse() ──

  describe('configSchema.parse()', () => {
    it('validates known fields', () => {
      const result = plugin.configSchema.parse({
        dbPath: '/tmp/test.db',
        contextThreshold: 0.75,
        llmProvider: 'deepseek',
        maxContextTokens: 200000,
      }) as Record<string, unknown>;
      expect(result.dbPath).toBe('/tmp/test.db');
      expect(result.contextThreshold).toBe(0.75);
      expect(result.maxContextTokens).toBe(200000);
    });

    it('defaults maxContextTokens to 40000', () => {
      const result = plugin.configSchema.parse({});
      expect(result.maxContextTokens).toBe(40000);
    });

    it('rejects out-of-range contextThreshold', () => {
      const result = plugin.configSchema.parse({ contextThreshold: 2.0 });
      expect(result.contextThreshold).toBeUndefined();
    });

    it('passes through unknown fields', () => {
      const result = plugin.configSchema.parse({ customField: 'hello' });
      expect(result.customField).toBe('hello');
    });

    it('parses string contextThreshold to number', () => {
      const result = plugin.configSchema.parse({ contextThreshold: '0.6' });
      expect(result.contextThreshold).toBe(0.6);
    });

    it('parses string maxContextTokens to number', () => {
      const result = plugin.configSchema.parse({ maxContextTokens: '64000' });
      expect(result.maxContextTokens).toBe(64000);
    });
  });

  // ── Plugin metadata ──

  describe('Plugin metadata', () => {
    it('has correct id', () => {
      expect(plugin.id).toBe('lobster-press');
    });

    it('has a name', () => {
      expect(plugin.name).toBeTruthy();
    });

    it('has a description', () => {
      expect(plugin.description).toBeTruthy();
    });

    it('has configSchema with parse method', () => {
      expect(typeof plugin.configSchema.parse).toBe('function');
    });
  });
});
