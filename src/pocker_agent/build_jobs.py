"""Bounded background builds with observable progress and restart-aware failures."""

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

logger = logging.getLogger(__name__)


class BuildJobs:
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="game-build")
        self.lock = threading.RLock()
        self.jobs = {}

    def start(self, operation):
        with self.lock:
            if any(j["status"] == "running" for j in self.jobs.values()):
                raise ValueError("已有游戏正在生成，请等待当前生成完成")
            # Keep a small bounded history; full accepted code lives in proposals/sessions.
            self.jobs = {
                k: v for k, v in self.jobs.items() if time.time() - v["created"] < 3600
            }
            while len(self.jobs) >= 20:
                self.jobs.pop(next(iter(self.jobs)))
            id = uuid.uuid4().hex
            self.jobs[id] = {
                "id": id,
                "status": "running",
                "created": time.time(),
                "progress": [],
                "result": None,
                "error": None,
            }
        self.pool.submit(self._run, id, operation)
        return self.get(id)

    def _run(self, id, operation):
        def progress(message):
            with self.lock:
                self.jobs[id]["progress"].append(
                    {"message": message, "time": time.time()}
                )

        try:
            result = operation(progress)
            with self.lock:
                self.jobs[id].update(status="completed", result=result)
        except (RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
            with self.lock:
                self.jobs[id].update(status="failed", error=str(error)[:2500])
        except Exception:
            logger.exception("game build failed unexpectedly")
            with self.lock:
                self.jobs[id].update(
                    status="failed",
                    error="生成任务内部错误，未发布游戏；请查看后端日志",
                )

    def get(self, id):
        with self.lock:
            if id not in self.jobs:
                raise ValueError("生成任务已失效（可能后端已重启），请重新发送玩法")
            return deepcopy(self.jobs[id])
