"""같은 IP에서 짧은 시간에 너무 많이 실패하는 요청을 막는다 (로그인 대입·계정 잠금 악용 방지).

웹 프로세스 메모리에 둔다(운영은 웹 컨테이너 하나). 프로세스가 다시 시작되면 초기화된다."""

import threading
import time
from collections import deque


class FailureWindow:
    def __init__(self, limit: int, seconds: int) -> None:
        self.limit = limit
        self.seconds = seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.seconds:
            hits.popleft()
        return hits

    def blocked(self, key: str) -> bool:
        with self._lock:
            hits = self._recent(key, time.monotonic())
            if not hits:
                self._hits.pop(key, None)
            return len(hits) >= self.limit

    def add(self, key: str) -> None:
        with self._lock:
            self._recent(key, time.monotonic()).append(time.monotonic())
            if len(self._hits) > 10_000:  # 오래된 키 정리 (메모리 상한)
                for stale in [k for k, v in self._hits.items() if not v][:5_000]:
                    del self._hits[stale]

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


# 같은 IP에서 10분에 로그인 실패 30번이면 잠시 막는다 (학교 공용 IP도 있어 넉넉히)
LOGIN_FAILURES = FailureWindow(limit=30, seconds=600)
