# 多玩家系统

支持三种玩家类型的统一决策框架：人类玩家（WebSocket）、算法Bot（策略模式）、LLM Agent（大模型API）。

## 核心接口

所有玩家实现统一的 `Player` 接口：

```typescript
interface Player {
  readonly id: string;
  readonly type: PlayerType;
  decideAction(context: DecisionContext): Promise<PlayerDecision>;
  dispose?(): void;
}
```

## 快速开始

### 1. 创建算法Bot

```typescript
import { PlayerFactory } from "./players/index.js";

// 使用预定义策略
const randomBot = PlayerFactory.createAlgorithmBot("bot1", "random");
const greedyBot = PlayerFactory.createAlgorithmBot("bot2", "greedy");

// 或使用自定义策略
import { AlgorithmBot, RandomStrategy } from "./players/index.js";
const customBot = new AlgorithmBot("bot3", new RandomStrategy());
```

### 2. 创建人类玩家

```typescript
import { HumanPlayer } from "./players/index.js";

const human = new HumanPlayer("player1", (message) => {
  // 发送到WebSocket客户端
  wsConnection.send(JSON.stringify(message));
});

// 在WebSocket消息处理器中提交动作
wsConnection.on("message", (data) => {
  const response = JSON.parse(data);
  if (response.type === "action_response") {
    human.submitAction(response);
  }
});
```

### 3. 创建LLM Agent

```typescript
import { PlayerFactory } from "./players/index.js";

const llmAgent = PlayerFactory.createLLMAgent("ai1", {
  apiUrl: "https://api.openai.com/v1/chat/completions",
  apiKey: process.env.OPENAI_API_KEY,
  model: "gpt-4",
  systemPrompt: "你是一个专业的卡牌游戏AI",
  maxRetries: 2,
  fallbackStrategy: "first",
  historyRounds: 4,
});
```

### 4. 在Arena中使用

```typescript
import { ArenaPlayerAdapter } from "./players/index.js";

// 将Player包装为Arena兼容格式
const wrappedBot = ArenaPlayerAdapter.wrapPlayer(randomBot);
const wrappedHuman = ArenaPlayerAdapter.wrapPlayer(human);
const wrappedLLM = ArenaPlayerAdapter.wrapPlayer(llmAgent);

// 创建Arena
const arena = new ArenaGame(
  engine,
  instanceId,
  module,
  [
    { agent: wrappedBot },
    { agent: wrappedHuman },
    { agent: wrappedLLM },
  ]
);

arena.start();
```

## 架构层次

### 1. 决策层 (DecisionMaker)
- `Player` 接口统一所有玩家类型
- `decideAction()` 方法返回标准决策

### 2. 观察转换层 (ObservationTransformer)
- `toHumanFormat()` - 完整JSON
- `toBotFeatures()` - 特征向量
- `toLLMDescription()` - 自然语言

### 3. 动作解析层 (ActionParser)
- `parseActionFromResponse()` - 解析LLM输出
- `resolveConstraints()` - 填充动作参数

### 4. 决策管理层 (DecisionManager)
- 统一超时处理
- 自动重试机制
- 降级策略

### 5. 策略注册表 (StrategyRegistry)
- 运行时策略管理
- 支持动态注册

### 6. 会话管理层 (ConversationManager)
- LLM历史记录
- Token优化

## 扩展策略

实现 `BotStrategy` 接口创建自定义策略：

```typescript
import { BotStrategy } from "./players/strategies/bot-strategy.js";

class MCTSStrategy implements BotStrategy {
  readonly name = "MCTS";
  
  selectAction(context: DecisionContext): RuleAction {
    // 实现蒙特卡洛树搜索
    // ...
  }
}

// 注册到全局注册表
import { defaultStrategyRegistry } from "./players/index.js";
defaultStrategyRegistry.register(new MCTSStrategy());
```

## 异常处理

所有决策错误通过 `DecisionError` 抛出：

```typescript
try {
  const decision = await player.decideAction(context);
} catch (error) {
  if (error instanceof DecisionError) {
    console.error(`Player ${error.playerId} error: ${error.code}`);
    // 处理超时、连接丢失、策略错误等
  }
}
```
