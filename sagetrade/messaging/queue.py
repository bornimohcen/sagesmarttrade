import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple


@dataclass
class Message:
    topic: str
    data: Dict[str, Any]
    ts: float


class MessageQueue:
    def publish(self, topic: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def consume(self, topic: str, timeout_ms: int = 1000) -> Iterator[Message]:
        raise NotImplementedError


class InMemoryQueue(MessageQueue):
    def __init__(self) -> None:
        self._topics: Dict[str, list] = {}
        self._conds: Dict[str, threading.Condition] = {}

    def _get_cond(self, topic: str) -> threading.Condition:
        if topic not in self._conds:
            self._conds[topic] = threading.Condition()
        return self._conds[topic]

    def publish(self, topic: str, data: Dict[str, Any]) -> None:
        cond = self._get_cond(topic)
        with cond:
            self._topics.setdefault(topic, []).append(Message(topic, data, time.time()))
            cond.notify_all()

    def consume(self, topic: str, timeout_ms: int = 1000) -> Iterator[Message]:
        cond = self._get_cond(topic)
        idx = 0
        while True:
            with cond:
                if topic not in self._topics:
                    self._topics[topic] = []
                q = self._topics[topic]
                if idx < len(q):
                    m = q[idx]
                    idx += 1
                    yield m
                    continue
                cond.wait(timeout=timeout_ms / 1000.0)


class RedisQueue(MessageQueue):
    """Redis Streams backed queue.

    Uses stream per topic: key = f"{namespace}:{topic}"
    Requires `redis` package. If not available, raises ImportError on init.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0, namespace: str = "sagetrade") -> None:
        try:
            import redis  # type: ignore
        except Exception as e:
            raise ImportError("redis package not installed. `pip install redis`.") from e
        self._redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._ns = namespace

    def _key(self, topic: str) -> str:
        return f"{self._ns}:{topic}"

    def publish(self, topic: str, data: Dict[str, Any]) -> None:
        payload = {"json": json.dumps(data), "ts": str(time.time())}
        self._redis.xadd(self._key(topic), payload, maxlen=10_000, approximate=True)

    def consume(self, topic: str, timeout_ms: int = 1000) -> Iterator[Message]:
        last_id = "$"  # start from new messages only
        key = self._key(topic)
        while True:
            resp = self._redis.xread({key: last_id}, count=100, block=timeout_ms)
            if not resp:
                continue
            stream_key, entries = resp[0]
            for msg_id, fields in entries:
                last_id = msg_id
                data = {}
                try:
                    data = json.loads(fields.get("json", "{}"))
                except Exception:
                    pass
                ts = float(fields.get("ts", time.time()))
                yield Message(topic=topic, data=data, ts=ts)


def build_queue_from_env() -> MessageQueue:
    backend = (os.environ.get("MSG_BACKEND") or "memory").strip().lower()
    namespace = os.environ.get("MSG_NAMESPACE") or "sagetrade"
    if backend == "redis":
        host = os.environ.get("REDIS_HOST", "127.0.0.1")
        port = int(os.environ.get("REDIS_PORT", "6379"))
        db = int(os.environ.get("REDIS_DB", "0"))
        return RedisQueue(host=host, port=port, db=db, namespace=namespace)
    return InMemoryQueue()

