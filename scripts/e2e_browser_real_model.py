"""Real-browser E2E with a real OpenAI-compatible model, retry on model flakiness.

Prereqs: backend on 8765 with POCKER_AGENT_* env pointing to a real model
endpoint (Key stays in the backend process); frontend dev server on 5175
with VITE_API_URL=http://127.0.0.1:8765.

Flow: frontend -> model config visible -> describe Crazy Eights -> proposal
-> confirm -> simulate -> play legal actions in the browser -> settlement ->
reload restores the session.  Screenshots to .validation/e2e-browser/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

FRONTEND = "http://127.0.0.1:5175/"
OUT = Path(__file__).resolve().parent / "e2e-browser"
OUT.mkdir(exist_ok=True)

DESC = ("创建两人疯狂八游戏：标准52张牌无王，一名人类一名电脑，每人5张。只玩1局，"
        "同花色或同点数接牌，8为万能牌且打出时指定花色，起始牌不是8。有合法牌必须出，"
        "无合法牌持续摸到可出，牌堆耗尽回收弃牌保留顶牌，全员卡住平局，先出完获胜，"
        "隐藏对手手牌。规则已完整请直接生成。")


def snap(page, name: str):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
    print(f"[shot] {name}", flush=True)


def main() -> int:
    results: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        console_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append("PAGEERROR: " + str(e)))

        page.goto(FRONTEND, wait_until="networkidle", timeout=45000)
        page.wait_for_selector("text=deepseek-flash", timeout=30000)
        results["model_visible"] = "deepseek-flash"
        snap(page, "01-config")

        # generation with retry (real model occasionally returns invalid ToolPlan)
        generation_ok = False
        for attempt in range(1, 5):
            page.get_by_label("玩法描述").fill(DESC)
            send = page.get_by_role("button", name="发送")
            send.wait_for(state="visible", timeout=15000)
            try:
                send.click(timeout=5000)
            except PWTimeout:
                pass
            try:
                page.wait_for_selector(".rule-summary", timeout=240000)
                generation_ok = True
                break
            except PWTimeout:
                err = page.locator(".error").inner_text() if page.locator(".error").count() else "unknown"
                results.setdefault("retries", []).append(f"attempt {attempt}: {err[:200]}")
                print("generation failed:", err[:200], "retrying", flush=True)
                page.wait_for_timeout(2000)
                continue
        if not generation_ok:
            results["error"] = results["retries"]
            snap(page, "02-failed")
            browser.close()
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 1

        results["status"] = page.locator(".status").inner_text()
        results["proposal_title"] = page.locator(".rule-summary h3").inner_text()
        results["proposal_facts"] = page.locator(".rule-facts").inner_text()
        snap(page, "02-proposal")

        # confirm
        page.get_by_role("button", name="确认规则").click(timeout=10000)
        page.wait_for_selector(".pill:text('已确认')", timeout=30000)
        results["confirmed"] = True
        snap(page, "03-confirmed")

        # simulate
        page.get_by_role("button", name="运行模拟").click(timeout=10000)
        page.wait_for_selector(".events .event", timeout=30000)
        results["sim_events"] = page.locator(".events .event").count()
        snap(page, "04-simulation")

        # start play
        page.get_by_role("button", name="开始试玩").click(timeout=10000)
        page.wait_for_selector(".game-controls", timeout=30000)
        results["phase_start"] = page.locator(".runtime-caption").first.inner_text()
        snap(page, "05-play-start")

        # play until settlement
        moves = 0
        stalled = 0
        while moves < 100:
            page.wait_for_timeout(300)
            if page.locator(".runtime-complete").count():
                break
            if "本局结束" in page.locator(".status").inner_text():
                break
            action_taken = False
            play_btn = page.get_by_role("button", name="出牌", exact=True)
            draw_btn = page.get_by_role("button", name="摸牌", exact=True)
            if play_btn.count():
                # pick the first playable card first, then the play button
                card = page.locator(".card-choice:not([disabled])").first
                if card.count():
                    card.click()
                    page.wait_for_timeout(400)
                    if play_btn.is_enabled():
                        play_btn.click()
                        moves += 1
                        action_taken = True
            if not action_taken and draw_btn.count() and draw_btn.is_enabled():
                draw_btn.click()
                moves += 1
                action_taken = True
            if not action_taken:
                stalled += 1
                if stalled > 15:
                    results["stall_reason"] = page.locator(".status").inner_text()
                    break
                page.wait_for_timeout(800)
            else:
                stalled = 0
        results["moves_played"] = moves
        results["final_status"] = page.locator(".status").inner_text()
        results["result_title"] = page.locator(".runtime-complete strong").inner_text() if page.locator(".runtime-complete").count() else None
        snap(page, "06-finished")

        # event log
        if page.locator(".runtime-log summary").count():
            page.click(".runtime-log summary")
            page.wait_for_timeout(500)
            results["event_log_preview"] = page.locator(".runtime-log pre").inner_text()[:1500]
        snap(page, "07-events")

        # reload restores
        page.reload(wait_until="networkidle", timeout=45000)
        try:
            page.wait_for_selector("text=已恢复上次牌局", timeout=30000)
            results["restore_ok"] = True
        except PWTimeout:
            results["restore_ok"] = False
            results["restore_status"] = page.locator(".status").inner_text()
        snap(page, "08-restored")

        results["console_errors"] = console_errors[:10]
        browser.close()

    out = OUT / "e2e-browser-results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results.get("restore_ok") else 1


if __name__ == "__main__":
    sys.exit(main())
