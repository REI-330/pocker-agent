# Agent → ToolPlan → Tool 真实链路验收

这份验收记录专门回答“牌局是否真的由 Agent 生成并调用 Tool”，不把启动了某个专用 Engine 当成证据。

## 验收命令

在 checkout 根目录运行：

```powershell
.venv\Scripts\python.exe scripts/validate_agent_tool_chain.py
```

脚本会启动一个临时的本地 OpenAI-compatible HTTP 端点。它只用于提供确定的模型响应，因此不需要外部 API Key；Pocker Agent 仍使用生产中的 `OpenAICompatibleClient`，通过真实 HTTP 请求调用 `/v1/chat/completions`。脚本不会 monkeypatch `RuleAgent`、`ToolPlan` 或 `GameLayer`。

## 已观察结果（2026-09-10）

```json
{
  "model_requests": 2,
  "generated_game_id": "agent-http-crazy-eights",
  "tool_plan_source": "engine_agent",
  "plan_tools": ["deck", "zones"],
  "tool_called": [
    {"tool": "deck", "operation": "deal"},
    {"tool": "zones", "operation": "create"},
    {"tool": "zones", "operation": "create"}
  ]
}
```

独立证据保存在运行时生成的 `artifacts/agent-tool-chain-http.json`（该目录被 gitignore，避免把临时端口、请求内容和测试产物提交到仓库）。其中同时记录了模型请求、模型返回的 `game_id/title`、API 返回的 ToolPlan 以及 RuleExecutor 发出的 `tool_called` 事件。

## 当前边界

这条验收证明了：

1. 用户自然语言经过真实模型协议进入 `RuleAgent`；
2. 模型返回的规则字段（包括自定义 `game_id/title`）被 API 接受并校验；
3. `EngineAgent` 再通过真实模型协议返回 ToolPlan，且返回值带有 `tool_plan_source=engine_agent`；
4. `/api/agent/confirm` 接受并返回同一计划；
5. `/api/runtime/sessions` 持久化同一计划，并在创建时通过 `GameLayer`/`RuleExecutor` 调用声明的 Tool；
6. `/api/tools/plan/execute` 的 `tool_called` 轨迹与 runtime session 的 `tool_events` 一致。

## 德州完整运行时验收

针对德州扑克使用真实源代码 Uvicorn 进程运行：

```powershell
.venv\Scripts\python.exe scripts/validate_holdem_agent_runtime.py
```

结果（2026-09-10）：

```json
{
  "model_requests": 2,
  "tool_plan_source": "engine_agent",
  "actions": ["call", "check", "check", "check"],
  "finished": true,
  "board_count": 5,
  "tool_called": [
    ["deck", "deal"],
    ["betting_round", "act"],
    ["all_in", "check"],
    ["phase_progress", "advance"],
    ["community_deal", "deal"],
    ["showdown", "call"],
    ["settle_pots", "call"]
  ]
}
```

这条验收覆盖完整一手牌：模型先生成规则，再生成 ToolPlan；运行会话持久化同一计划；每次下注、全下检测、街道推进、公共牌发放、摊牌和底池结算都会由计划中声明的确定性工具执行并写入 `tool_called`。运行时保留状态适配器负责 HTTP 会话、版本号和持久化，牌局规则本身由工具实现。若模型返回无效计划，EngineAgent 会返回明确错误并拒绝偷偷改用宿主硬编码计划。

兼容部分 OpenAI 网关自定义的“阶段/工具调用”响应时，EngineAgent 只做结构降级：保留模型选择的已注册工具和阶段，再转换成项目的严格 ToolPlan；不会执行模型返回的代码或未注册操作。随机文本、未知工具和无法降级的响应仍会失败。
