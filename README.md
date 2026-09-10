# Pocker Agent

Pocker Agent 是一个本机单用户 Web demo：用户用自然语言描述纸牌玩法，Agent 负责补全规则并生成可执行提案；用户确认后可以运行确定性模拟、与电脑试玩，并在部分规则下导出离线练习包。

项目当前的核心边界是“可验证的有限规则原语”，不是任意自然语言到完整商业纸牌游戏的编译器。内置规则提案经过结构校验和启动检查，完整模拟可在确认后单独运行；代码生成玩法在提供提案前还要经过固定行为测试与多种子重放。

## 能力概览

| 能力 | 当前状态 | 说明 |
| --- | --- | --- |
| 自然语言澄清与规则提案 | 可用 | Agent 保留对话上下文，要求不明确时先追问 |
| v0.1 固定 DSL | 可用 | 分阶段动作、摸牌/出牌/弃牌/跳过、轮次、最高牌或手牌数量计分 |
| v0.2 内置规则族 | 可用 | 24 点单人练习、无下注 21 点、同花/同点接牌基础变体 |
| Agent 代码生成 | 实验 | 生成 JavaScript 行为合约与源码，经 QuickJS 隔离执行；抽乌龟已有一份真实验收产物 |
| 模拟与单人试玩 | 可用 | Python 确定性引擎；电脑执行合法动作策略 |
| 保存与恢复 | 可用 | SQLite 保存配置与牌局，API Key 存 Windows Credential Manager/keyring |
| 离线导出 | 部分可用 | 阶段规则的有限固定发牌决策树，最多 2000 个决策节点 |
| 多人联网、下注、复杂牌型 | 未实现 | 不应把代码生成实验能力当作这些功能已经支持 |

已验收的细节与边界见 [PROJECT.md](PROJECT.md)、[架构说明](docs/architecture.md)、[代码生成协议](docs/generated-game-protocol.md) 和 [常见玩法审查](docs/mainstream-games-review.md)。

## 工作流

```text
自然语言描述
      ↓
Agent 澄清 / 选择规则 schema
      ↓
固定 DSL 或 JavaScript 代码生成
      ↓
结构校验 + 引擎启动检查 + 行为测试/多种子模拟
      ↓
用户确认规则 → 模拟 → 单人试玩 →（阶段规则）离线导出
```

修改玩法后，旧提案、确认状态、模拟轨迹和试玩状态会失效，需要重新确认，避免使用过期规则。

## 技术结构

```text
frontend/                    React + TypeScript + Vite 工作台
src/pocker_agent/
  api.py                     FastAPI 应用与 HTTP 路由
  agent.py                   对话、澄清、DSL/插件路由
  configuration.py           URL 校验、SQLite 元数据、keyring 凭据
  llm.py                     OpenAI-compatible Chat Completions 客户端
  models.py                  v0.1 DSL 的严格 Pydantic 模型
  game_rules.py              v0.2 规则族与 schema 分发
  engine.py                  v0.1 阶段规则引擎
  family_engines.py          24 点、21 点、接牌确定性引擎
  arithmetic.py              AST + Fraction 精确算式校验/求解
  simulation.py              与试玩共用的确定性模拟
  runtime.py                 牌局会话、电脑回合、revision 并发保护、恢复
  storage.py                 SQLite 事务边界
  plugin_schema.py           生成游戏合约与状态模型
  plugin_builder.py          先测后写、失败反馈、最多两次源码修复
  plugin_sandbox.py          QuickJS 子进程与资源限制
  plugin_worker.py           生成代码的受限执行入口
  plugin_engine.py           插件接入统一运行时
  build_jobs.py              单并发、限量、可轮询的后台生成任务
  exporting.py               v0.1 离线 HTML/SVG/DSL 打包
  assets/cards/              纸牌 SVG 与许可证
tests/                       后端单元/API/插件协议测试
docs/                        DSL、架构、验收和开发边界
benchmarks/                  自然语言回归与生成产物验收数据
scripts/                     独立验证和基准脚本
```

后端通过 `create_app()` 创建应用；默认导出的 `app` 供 uvicorn 使用。当前部署模型是本机、单用户、单进程，后台代码生成最多同时运行一个任务。

## 快速启动（Windows PowerShell）

要求：Python 3.11+、[uv](https://docs.astral.sh/uv/)、Node.js 以及 npm。

```powershell
uv sync
uv run uvicorn pocker_agent.api:app --app-dir src --host 127.0.0.1 --port 8000
```

另开一个终端启动前端：

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

打开 <http://127.0.0.1:5173>。前端默认直接请求 `http://127.0.0.1:8000` 的 API 和素材，可通过 `VITE_API_URL` 修改地址；当前 Vite 未配置代理。

## 模型配置

在页面的“模型设置”中填写兼容 Chat Completions 的 API 地址、API Key 和模型 ID。域名根地址会规范化为 `/v1`；明确填写 `/api/v2` 等路径会保留。获取模型列表和测试连接使用临时草稿，只有保存才会改变正式配置；修改后需要保存或撤销才能继续发送玩法。

配置存储位置默认是 `%LOCALAPPDATA%\PockerAgent\pocker.db`。可用 `POCKER_AGENT_DATA_DIR` 指定数据目录。SQLite 只保存配置元数据和 Key 引用，Key 保存到系统凭据库，不回退到明文文件。未配置模型时，可以通过环境变量提供初始值：

```powershell
$env:POCKER_AGENT_BASE_URL = "https://api.openai.com/v1"
$env:POCKER_AGENT_API_KEY = "your-key"
$env:POCKER_AGENT_MODEL = "gpt-4o-mini"
```

## HTTP 接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| GET/POST | `/api/agent/config` | 读取公开配置状态 / 保存配置 |
| POST | `/api/agent/models` | 用临时配置发现模型 |
| POST | `/api/agent/test-connection` | 用临时配置发起最小连接测试 |
| POST | `/api/agent/turn` | 同步进行一次澄清或规则生成 |
| POST/GET | `/api/agent/jobs`、`/api/agent/jobs/{id}` | 创建并轮询 Agent 任务，涵盖澄清、DSL 和代码生成 |
| POST | `/api/agent/confirm` | 校验提案并执行启动检查 |
| POST | `/api/rules/validate` | 只校验规则 payload |
| POST | `/api/simulations` | 按 seed 运行模拟 |
| POST/GET | `/api/runtime/sessions`、`/api/runtime/sessions/{id}` | 创建/读取试玩牌局 |
| POST | `/api/runtime/sessions/{id}/actions/{action}` | 按 revision 提交玩家动作 |
| POST | `/api/games/export` | 导出 v0.1 离线游戏包 |

动作失败不会提交副本状态、事件、分数或 revision；revision 不一致会返回冲突，客户端应先刷新牌局。

## 测试与构建

推荐在 Windows 受限环境中把 uv、pytest 临时文件放到项目可写目录：

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:POCKER_AGENT_DATA_DIR = "$PWD\.tmp-test-data"
uv run pytest -q --basetemp="$PWD\.test-tmp" -p no:cacheprovider
```

前端生产构建：

```powershell
npm run build --prefix frontend
```

自然语言真实模型回归（会使用当前已保存配置，不修改配置）：

```powershell
uv run python -X utf8 scripts/benchmark_games.py --timeout 45
```

测试集位于 `benchmarks/common_games.json`；生成游戏的独立抽乌龟核对可运行：

```powershell
uv run python -X utf8 scripts/verify_old_maid.py benchmarks/generated-old-maid.json
```

## 已知边界

- 固定 DSL 只表达已实现的阶段动作和计分原语，未知字段/动作会被拒绝。
- 内置 24 点是单人练习；21 点是无下注的一位玩家对一位庄家；接牌目前为 2–4 人标准 52 张牌的一局出完手牌玩法。
- 代码生成行为测试仍由模型根据用户描述制定，测试通过不能证明语义完全符合用户本意；生成执行环境不是可抵御原生 VM 漏洞的操作系统级沙箱。
- 算式、21点、接牌和插件玩法支持本机网页试玩与 SQLite 恢复，暂不支持离线决策树导出。
- 多人联网、账号隔离、房间/实时同步、下注/筹码、斗地主/桥牌/德州扑克等复杂牌型机制尚未实现或未完成验收。
- 离线导出使用固定 seed=7 的练习局，最多 2000 个决策节点；在线模拟不受该导出上限限制。

## 相关文档

- [项目进度](PROJECT.md)
- [开发问题与路线图](docs/development-issues.md)
- [架构](docs/architecture.md)
- [Agent 运作机制：上下文、路由、生成、验证与修复](docs/agent-workflow.md)
- [DSL 合约](docs/dsl.md)
- [代码生成协议与安全边界](docs/generated-game-protocol.md)
- [代码审查与验收记录](docs/review-and-acceptance.md)
- [常见玩法审查](docs/mainstream-games-review.md)
- [贡献指南](CONTRIBUTING.md)
- [第三方素材与许可证](THIRD_PARTY_NOTICES.md)
