# Pocker Agent 对话生命周期

本次重构把“聊天设计”和“生成/试玩”拆成两个明确阶段。模型在聊天阶段只负责澄清规则，不会因为用户说了“生成”就启动构建；只有用户确认规则后，应用层才创建生成任务。

## 目录边界

```text
frontend/src/features/conversation/  聊天输入、会话状态、确认按钮与轮询
frontend/src/features/game/           运行中的牌局、模拟和导出
src/pocker_agent/application/         生命周期编排与持久化会话服务
src/pocker_agent/agents/              单一职责 Agent（design、generation）
src/pocker_agent/domain/              规则、草稿、状态和值对象
src/pocker_agent/game_runtime/        已确认规则的构建、执行、模拟和导出
src/pocker_agent/infrastructure/      SQLite、模型客户端和外部适配器
```

依赖方向从接口进入 application，再进入 domain 或 infrastructure；domain 不调用模型、数据库或 HTTP。`game_runtime` 只接收已确认的规则，不反向依赖聊天服务。仓库根目录的旧模块仅保留兼容导入，不再承载业务实现。

## 状态机

```text
DESIGNING --用户消息--> THINKING --模型追问--> DESIGNING
                              \--完整草稿--> PROPOSAL_READY
PROPOSAL_READY --用户确认--> BUILDING --构建成功--> PLAYABLE
BUILDING --构建失败/重启--> FAILED
THINKING --取消/重启--> DESIGNING/FAILED
PLAYABLE --运行时操作--> PLAYABLE
```

每个写请求携带 `revision`。服务端在锁内校验版本并保存 SQLite，再在锁外调用模型或运行构建任务；旧快照不能覆盖新状态。聊天请求还携带 `request_id`，同一请求重试会返回已保存的结果，不会重复追加消息。

## 请求流程

1. `POST /api/conversations` 创建持久化会话。
2. `POST /api/conversations/{id}/messages` 追加一条用户消息。`DesignAgent` 只返回自然语言回复和可读草稿；前端可以继续发送下一轮。
3. 草稿进入 `proposal_ready` 后，前端显示“确认规则并生成游戏”。
4. `POST /api/conversations/{id}/confirm` 校验 `revision`，切换到 `building` 并启动 `BuildJobs`。构建进度和结果通过会话查询返回。
5. 构建成功后会话进入 `playable`，随后由 runtime API 创建牌局、模拟、试玩和导出。运行时不再调用聊天 Agent。

取消只改变当前会话的可见状态并使迟到的模型结果失效；模型调用在锁外执行，因此取消不会阻塞后续请求。服务重启时，持久化的 `thinking/building` 会话会恢复为 `failed` 并给出可重试错误，避免假装任务仍在运行。
