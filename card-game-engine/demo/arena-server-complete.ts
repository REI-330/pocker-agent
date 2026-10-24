import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { ArenaGame, FirstLegalAgent, HumanAgent, type ArenaEvent } from "../src/arena.js";
import { GameEngine } from "../src/engine.js";
import { loadRuleModule } from "../src/module-loader.js";
import { EngineError } from "../src/errors.js";
import type { PlayerAgent, RuleAction, RuleModule } from "../src/index.js";
import { PlayerFactory, ArenaPlayerAdapter } from "../dist/players/index.js";

const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY || "";
const DEEPSEEK_API_URL = process.env.DEEPSEEK_API_URL || "https://api.deepseek.com/v1/chat/completions";

const port = Number(process.env.PORT ?? 3010);
const gamesDirectory = process.env.CGC_GAMES ?? ["./demo/games", "../card-game-core/build/node"].find((directory) => existsSync(directory)) ?? "./demo/games";
const modules = loadModules(gamesDirectory);
const engine = new GameEngine();
const arenas = new Map<string, ArenaGame>();
const subscribers = new Map<string, Map<ServerResponse, string | undefined>>();

const server = createServer(async (request, response) => {
  try { await handle(request, response); }
  catch (error) { writeError(response, error); }
});

server.listen(port, "127.0.0.1", () => console.log(`Arena demo listening at http://127.0.0.1:${port}`));

function loadModules(directory: string): Map<string, RuleModule> {
  const result = new Map<string, RuleModule>();
  for (const file of readdirSync(directory).filter((name) => name.endsWith(".cjs") && name !== "runtime.cjs")) {
    const module = loadRuleModule(join(directory, file));
    result.set(module.metadata().gameId, module);
  }
  if (!result.size) throw new Error(`没有在 ${directory} 找到编译后的规则模块`);
  return result;
}

async function handle(request: IncomingMessage, response: ServerResponse): Promise<void> {
  const url = new URL(request.url ?? "/", "http://localhost");
  const parts = url.pathname.split("/").filter(Boolean);
  if (request.method === "GET" && url.pathname === "/") { response.setHeader("content-type", "text/html; charset=utf-8"); response.end(readFileSync(join(process.cwd(), "demo", "arena.html"), "utf8")); return; }
  if (request.method === "GET" && url.pathname === "/games") { writeJson(response, 200, [...modules.values()].map((module) => module.metadata())); return; }
  if (request.method === "POST" && url.pathname === "/arena") {
    const body = await readJson(request);
    const gameId = requiredString(body.gameId, "gameId");
    const module = modules.get(gameId);
    if (!module) throw new EngineError("GAME_NOT_FOUND", `规则未加载: ${gameId}`);
    const players = Array.isArray(body.players) && body.players.length ? body.players : [{ id: "human", kind: "human" }, { id: "bot-1", kind: "ai" }];
    const agents: PlayerAgent[] = players.map((item: any) => {
      const id = requiredString(item.id, "player.id");
      const kind = item.kind || "ai";
      if (kind === "human") return new HumanAgent(id);
      if (kind === "llm") {
        const llm = PlayerFactory.createLLMAgent(id, {
          apiUrl: item.apiUrl || DEEPSEEK_API_URL, apiKey: item.apiKey || DEEPSEEK_API_KEY,
          model: item.model || "deepseek-chat",
          maxRetries: 2, fallbackStrategy: "random"
        });
        return ArenaPlayerAdapter.wrapPlayer(llm);
      }
      if (kind === "bot") {
        const bot = PlayerFactory.createAlgorithmBot(id, item.strategy || "random");
        return ArenaPlayerAdapter.wrapPlayer(bot);
      }
      return new FirstLegalAgent(id);
    });
    const instanceId = `arena-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    engine.createGame({ instanceId, module, players: agents.map((agent) => agent.id) });
    const arena = new ArenaGame(engine, instanceId, module, agents.map((agent) => ({ agent })));
    arena.on("event", (event) => {
      for (const [client, viewer] of subscribers.get(instanceId) ?? []) {
        (client as any).write(`data: ${JSON.stringify(projectEvent(event, viewer))}\n\n`);
      }
    });
    arenas.set(instanceId, arena);
    arena.start();
    writeJson(response, 201, { instanceId, players: agents.map((agent) => ({ id: agent.id, kind: agent.kind })), snapshot: publicSnapshot(arena) });
    return;
  }
  if (parts[0] !== "arena" || !parts[1]) { writeJson(response, 404, { error: { code: "NOT_FOUND", message: "route not found" } }); return; }
  const instanceId = parts[1];
  const arena = arenas.get(instanceId);
  if (!arena) throw new EngineError("GAME_NOT_FOUND", `Arena 对局不存在: ${instanceId}`);
  if (request.method === "GET" && parts[2] === "events") {
    const viewer = url.searchParams.get("playerId") ?? undefined;
    if (viewer) arena.decisionView(viewer);
    response.statusCode = 200; response.setHeader("content-type", "text/event-stream; charset=utf-8"); response.setHeader("cache-control", "no-cache"); response.setHeader("connection", "keep-alive");
    const clients = subscribers.get(instanceId) ?? new Map<ServerResponse, string | undefined>(); clients.set(response, viewer); subscribers.set(instanceId, clients);
    (response as any).write(`data: ${JSON.stringify({ type: "snapshot", instanceId, sequence: arena.snapshot.sequence, payload: { snapshot: publicSnapshot(arena) } })}\n\n`);
    (request as any).on("close", () => clients.delete(response));
    return;
  }
  if (request.method === "GET" && parts[2] === "decision") {
    const playerId = requiredString(url.searchParams.get("playerId"), "playerId");
    writeJson(response, 200, arena.decisionView(playerId));
    return;
  }
  if (request.method === "GET") { writeJson(response, 200, publicSnapshot(arena)); return; }
  if (request.method === "POST" && parts[2] === "action") {
    const body = await readJson(request);
    const playerId = requiredString(body.playerId, "playerId");
    arena.submitHumanAction(playerId, body.action as RuleAction, body.intent);
    writeJson(response, 202, { accepted: true });
    return;
  }
  writeJson(response, 405, { error: { code: "METHOD_NOT_ALLOWED", message: "method not allowed" } });
}

async function readJson(request: IncomingMessage): Promise<Record<string, any>> { const chunks: Uint8Array[] = []; for await (const chunk of request) chunks.push(new Uint8Array(chunk)); const text = new TextDecoder().decode(Buffer.concat(chunks)); try { return JSON.parse(text || "{}"); } catch { throw new EngineError("INVALID_REQUEST", "请求必须是 JSON"); } }
function requiredString(value: unknown, name: string): string { if (typeof value !== "string" || !value) throw new EngineError("INVALID_REQUEST", `${name} 必须是非空字符串`); return value; }
function writeJson(response: ServerResponse, status: number, body: unknown): void { response.statusCode = status; response.setHeader("content-type", "application/json; charset=utf-8"); response.end(JSON.stringify(body)); }
function writeError(response: ServerResponse, error: unknown): void { const code = error instanceof EngineError ? error.code : "INTERNAL_ERROR"; response.statusCode = code === "GAME_NOT_FOUND" ? 404 : 400; writeJson(response, response.statusCode, { error: { code, message: error instanceof Error ? error.message : String(error) } }); }
function publicSnapshot(arena: ArenaGame): Record<string, unknown> { const snapshot = arena.snapshot; return { instanceId: arena.instanceId, gameId: snapshot.gameId, sequence: snapshot.sequence, status: snapshot.status, activeActors: snapshot.activeActors, result: snapshot.result }; }

function projectEvent(event: ArenaEvent, viewer?: string): ArenaEvent {
  if (event.type !== "transition") return event;
  const stages = (event.payload.stages as Record<string, any>[]).map(({ views, publicState, ...stage }) => ({ ...stage, state: viewer ? views[viewer] : publicState }));
  return { ...event, payload: { ...event.payload, stages } };
}
