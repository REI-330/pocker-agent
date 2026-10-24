# Arena AI 多玩家系统 - 使用指南

欢迎使用 Arena AI 多玩家系统！本系统支持三种玩家类型（真人、算法Bot、大模型AI）混合参与卡牌游戏。

---

## 📚 目录

1. [快速开始](#快速开始)
2. [系统架构](#系统架构)
3. [使用方式](#使用方式)
   - [方式1：浏览器界面](#方式1浏览器界面)
   - [方式2：HTTP API](#方式2http-api)
4. [玩家类型配置](#玩家类型配置)
5. [LLM 配置指南](#llm-配置指南)
6. [游戏列表](#游戏列表)
7. [常见问题](#常见问题)
8. [开发者指南](#开发者指南)

---

## 快速开始

### 1. 启动服务器

```bash
cd card-game-engine
export PORT=3010
export CGC_GAMES="../card-game-core/build/node"
npx tsx demo/arena-server-complete.ts
```

服务器将在 `http://127.0.0.1:3010` 启动。

### 2. 打开浏览器

访问 http://127.0.0.1:3010

### 3. 配置玩家

1. 点击右上角 **⚙ 配置** 按钮
2. 添加/删除玩家，选择玩家类型
3. 如果使用 LLM，填写 API Key
4. 保存配置

### 4. 开始游戏

1. 从下拉框选择游戏
2. 点击 **开始新对局** 按钮
3. 观看游戏自动进行

---

## 系统架构

```
┌─────────────────┐
│  card-game-core │  游戏规则定义（JSON）
└────────┬────────┘
         │ 编译
         ↓
┌─────────────────┐
│ card-game-engine│  游戏引擎执行
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Arena系统     │  多玩家管理
│  ┌───────────┐  │
│  │ Algorithm │  │  算法Bot
│  │    Bot    │  │
│  ├───────────┤  │
│  │  Human    │  │  真人玩家
│  │  Player   │  │
│  ├───────────┤  │
│  │    LLM    │  │  大模型AI
│  │   Agent   │  │
│  └───────────┘  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   浏览器界面    │  实时观战
└─────────────────┘
```

---

## 使用方式

### 方式1：浏览器界面

**适合人群**：普通用户、游戏测试、快速演示

#### 步骤详解

**第一步：配置玩家**

点击 ⚙ 配置按钮，打开玩家配置面板：

```
┌─────────────────────────────────┐
│        玩家配置                  │
├─────────────────────────────────┤
│ 玩家1                           │
│ 类型: [真人 ▼]                  │
├─────────────────────────────────┤
│ 玩家2                           │
│ 类型: [Bot ▼]                   │
│ 策略: [随机 ▼]                  │
├─────────────────────────────────┤
│ [+ 添加玩家]                    │
│                                 │
│ [取消]  [保存]                  │
└─────────────────────────────────┘
```

**第二步：选择玩家类型**

- **真人**：需要在浏览器中手动操作
- **Bot**：自动运行，可选择策略
  - 随机策略：随机选择合法动作
  - 贪婪策略：选择最复杂的动作
- **LLM**：AI智能决策，需要配置 API

**第三步：配置 LLM（如果使用）**

选择 LLM 玩家后，需要填写：

```
┌─────────────────────────────────┐
│ API Key: [sk-xxxxx...]          │
│                                 │
│ API URL:                        │
│ [https://api.deepseek.com/v1... │
│                                 │
│ [测试连接] ← 点击获取模型列表    │
│                                 │
│ 模型: [deepseek-chat ▼]         │
└─────────────────────────────────┘
```

**第四步：测试连接**

点击 **测试连接** 按钮：
- ✅ 成功：自动获取可用模型列表
- ❌ 失败：检查 API Key 和 URL

**第五步：开始游戏**

1. 保存玩家配置
2. 选择游戏（如：high-card-race）
3. 点击 **开始新对局**

**第六步：观战**

游戏自动进行，右侧面板实时显示：
- AI 的决策理由
- Bot 的策略选择
- 所有玩家的动作历史

---

### 方式2：HTTP API

**适合人群**：开发者、自动化测试、批量运行

#### API 端点

**1. 查看可用游戏**

```bash
GET http://127.0.0.1:3010/games
```

响应：
```json
[
  {
    "gameId": "high-card-race",
    "players": {"min": 2, "max": 6},
    "moduleApiVersion": "0.28.0"
  }
]
```

**2. 创建游戏**

```bash
POST http://127.0.0.1:3010/arena
Content-Type: application/json

{
  "gameId": "high-card-race",
  "players": [
    {"id": "player1", "kind": "bot", "strategy": "random"},
    {
      "id": "player2",
      "kind": "llm",
      "apiKey": "sk-xxxxx",
      "apiUrl": "https://api.deepseek.com/v1/chat/completions",
      "model": "deepseek-chat"
    }
  ]
}
```

响应：
```json
{
  "instanceId": "arena-1792827426543-ckb1z",
  "status": "running"
}
```

**3. 查询游戏状态**

```bash
GET http://127.0.0.1:3010/arena/{instanceId}/decision?playerId=player1
```

响应：
```json
{
  "status": "ended",
  "observation": {
    "round": 26,
    "scores": {"player1": 15, "player2": 14}
  }
}
```

---

## 玩家类型配置

### 1. 算法 Bot

**特点**：
- 速度快，无网络延迟
- 策略可预测
- 适合测试和基准对比

**配置示例**：
```json
{
  "id": "bot-random",
  "kind": "bot",
  "strategy": "random"
}
```

**可用策略**：
- `random`：随机选择合法动作
- `greedy`：选择约束最多的动作

### 2. 真人玩家

**特点**：
- 需要浏览器交互
- 支持超时设置
- 实时观战体验

**配置示例**：
```json
{
  "id": "human-1",
  "kind": "human"
}
```

**注意事项**：
- 需要在浏览器中等待真人操作
- 默认超时60秒

### 3. LLM AI 玩家

**特点**：
- 智能决策
- 自动理解游戏规则
- 无需针对每个游戏编程

**配置示例**：
```json
{
  "id": "ai-deepseek",
  "kind": "llm",
  "apiKey": "sk-xxxxx",
  "apiUrl": "https://api.deepseek.com/v1/chat/completions",
  "model": "deepseek-chat"
}
```

**支持的 LLM 提供商**：
- DeepSeek
- OpenAI (GPT-3.5/4)
- Anthropic Claude
- 任何 OpenAI 兼容接口



---

## 游戏列表

当前系统支持以下游戏：

### 1. high-card-race（比大小）

**玩家数**：2-6人  
**游戏时长**：短（约26轮）  
**规则**：抽牌比大小，得分最高者获胜  
**适合场景**：快速测试、演示

**示例配置**：
```json
{
  "gameId": "high-card-race",
  "players": [
    {"id": "bot1", "kind": "bot", "strategy": "random"},
    {"id": "ai1", "kind": "llm", "apiKey": "..."}
  ]
}
```

### 2. old-maid-single-ghost（抽鬼牌）

**玩家数**：2-6人  
**游戏时长**：短（约3轮）  
**规则**：配对消牌，避免持有鬼牌  
**适合场景**：测试 LLM 配对策略

### 3. zha-jin-hua（炸金花）

**玩家数**：2-6人  
**游戏时长**：中  
**规则**：下注、比牌，最大牌型获胜  
**适合场景**：测试 LLM 概率推理

### 4. guandan-level-match（掼蛋）

**玩家数**：4人（固定）  
**游戏时长**：长  
**规则**：复杂的扑克牌游戏  
**适合场景**：测试 LLM 复杂规则理解

---

### 如何添加新游戏？

**A**: 三个步骤：
```bash
# 1. 编写游戏 JSON 规则
vi card-game-core/games/my-game.json

# 2. 编译游戏
cd card-game-core
node node/dist/compile.cjs games/my-game.json --output build/node/my-game.cjs

# 3. 重启服务器
# 新游戏自动可用，无需修改代码
```

## 开发者指南

### 集成到你的项目

**步骤1：引入 Player 模块**

```typescript
import { 
  PlayerFactory, 
  ArenaPlayerAdapter 
} from './card-game-engine/dist/players/index.js';
```

**步骤2：创建玩家**

```typescript
// 创建 Bot
const bot = PlayerFactory.createAlgorithmBot('bot-1', 'random');

// 创建 LLM Agent
const llm = PlayerFactory.createLLMAgent('ai-1', {
  apiKey: 'sk-xxxxx',
  apiUrl: 'https://api.deepseek.com/v1/chat/completions',
  model: 'deepseek-chat'
});

// 创建真人玩家
const human = PlayerFactory.createHumanPlayer('human-1', (msg) => {
  // WebSocket 发送消息
  ws.send(JSON.stringify(msg));
});
```

**步骤3：适配到 Arena**

```typescript
// 包装为 Arena 兼容的 Agent
const botAgent = ArenaPlayerAdapter.wrapPlayer(bot);
const llmAgent = ArenaPlayerAdapter.wrapPlayer(llm);

// 创建 Arena 游戏
const arena = new ArenaGame(engine, instanceId, module, [
  { agent: botAgent },
  { agent: llmAgent }
]);
```

### 添加新的 Bot 策略

**步骤1：实现 BotStrategy 接口**

```typescript
import type { BotStrategy } from './strategies/bot-strategy.js';

export class MyStrategy implements BotStrategy {
  selectAction(context: DecisionContext): number {
    // 你的策略逻辑
    const { legalActions } = context;
    // 返回动作索引
    return 0;
  }
}
```

**步骤2：注册策略**

```typescript
import { StrategyRegistry } from './strategies/strategy-registry.js';
import { MyStrategy } from './my-strategy.js';

StrategyRegistry.register('my-strategy', n
