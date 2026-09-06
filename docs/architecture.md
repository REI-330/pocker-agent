# 架构（当前实现）

React 工作台：
- api.ts：HTTP 请求、错误信息和公共类型。
- ModelSettings：临时表单、完整模型列表、手动模型名、测试与保存。
- GameTable：开源 SVG 牌面、选牌、电脑回合结果、分数、重开与刷新。
- main.tsx：对话 → 提案 → 确认 → 模拟 → 试玩 → 导出；修改规则会取消旧确认并清除旧衍生结果。

FastAPI：
- configuration.py：校验、规范化 URL、正式配置快照；SQLite 元数据 + keyring 系统凭据。
- llm.py：复用 OpenAI Python SDK 的网络、鉴权与错误处理；服务地址、模型没有白名单。
- agent.py：完整 JSON Schema + 明确 DSL 执行语义；澄清、生成和修复。
- models.py / validation.py：严格模型、引用验证和边界。
- engine.py：唯一权威规则引擎；阶段、轮次、动作、计分、终止与可序列化状态。
- runtime.py：单人电脑回合、SQLite 牌局恢复、revision 并发保护。
- simulation.py：同一引擎的确定性模拟。
- exporting.py：同一引擎编译有限离线决策树，打包 HTML、DSL、纸牌与许可证。
- storage.py：有事务且明确关闭连接的 SQLite 边界。

配置 GET 不返回 Key。发现模型 / 测试连接不修改已保存状态。每次 Agent 请求取得完整不可变配置快照。
持久化目录默认位于 Windows 本地应用数据目录，排除于仓库之外。当前仅支持本机单用户单进程部署。
