"""Real-model code generation acceptance using the saved credential store."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from pocker_agent.agent import AgentSession, RuleAgent
from pocker_agent.configuration import ConfigStore
from pocker_agent.llm import OpenAICompatibleClient

PROMPT = """请生成两人抽乌龟游戏，我和电脑玩，标准52张牌去掉黑桃Q，剩余51张洗牌依次轮流全部发完。
开局自动消除各人手中所有同点数对子（不要求同色）；四张同点数消除两对。
玩家0先从另一人隐藏手牌中任选一个位置抽一张，抽到后自动消除同点对子，再换另一人抽。
双方手牌始终对对方隐藏，不能从按钮或日志看见对方牌值。
手牌空者退出，最后剩余一张Q的人输，另一人赢。只玩一局，不下注、不计时。
请使用代码生成路径，生成实际逻辑并运行测试，不要改成比大小。
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/generated-old-maid.json")
    parser.add_argument("--previous")
    parser.add_argument("--prompt")
    parser.add_argument(
        "--model", help="Override for this test only; never save configuration"
    )
    parser.add_argument("--effort")
    args = parser.parse_args()
    client = OpenAICompatibleClient.from_config(ConfigStore().read())
    if args.model:
        client.model = args.model
    client.reasoning_effort = args.effort
    client.timeout_seconds = 180
    records = []
    complete = client.complete
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    def traced(messages, **kwargs):
        raw = complete(messages, **kwargs)
        records.append(raw)
        out.with_suffix(".responses.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return raw

    client.complete = traced
    session = AgentSession()
    if args.previous:
        data = json.loads(Path(args.previous).read_text(encoding="utf-8"))
        session = AgentSession(data["messages"], data["rules"])
    started = perf_counter()
    report = {"model": client.model}
    try:
        result = RuleAgent(client, lambda msg: print(msg, flush=True)).turn(
            session, args.prompt or PROMPT
        )
        report.update(
            kind=result.kind,
            message=result.message,
            errors=result.errors,
            build=result.build,
            rules=result.rules.model_dump(mode="json") if result.rules else None,
            messages=session.messages,
        )
        print("RESULT", result.kind, result.errors, flush=True)
    except Exception as error:
        report.update(kind="error", error=str(error))
        if error.__cause__:
            report["cause"] = {
                "type": type(error.__cause__).__name__,
                "detail": str(error.__cause__).replace(client.api_key, "[REDACTED]")[
                    :1000
                ],
            }
        print("FAILED", str(error), flush=True)
    report.update(seconds=round(perf_counter() - started, 2), responses=records)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return int(report["kind"] != "proposal")


if __name__ == "__main__":
    raise SystemExit(main())
