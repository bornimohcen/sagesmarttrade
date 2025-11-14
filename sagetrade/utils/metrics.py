from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict


@dataclass
class Counter:
    name: str
    help: str = ""
    value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount


@dataclass
class Gauge:
    name: str
    help: str = ""
    value: float = 0.0

    def set(self, value: float) -> None:
        self.value = value


@dataclass
class MetricsRegistry:
    """Minimal in-process metrics registry.

    Designed for Prometheus-style scraping via text exposition format.
    """

    counters: Dict[str, Counter] = field(default_factory=dict)
    gauges: Dict[str, Gauge] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def counter(self, name: str, help: str = "") -> Counter:
        with self._lock:
            if name not in self.counters:
                self.counters[name] = Counter(name=name, help=help)
            return self.counters[name]

    def gauge(self, name: str, help: str = "") -> Gauge:
        with self._lock:
            if name not in self.gauges:
                self.gauges[name] = Gauge(name=name, help=help)
            return self.gauges[name]

    def render_prometheus(self) -> str:
        """Render all metrics in a basic Prometheus text format."""
        lines: list[str] = []
        with self._lock:
            for c in self.counters.values():
                if c.help:
                    lines.append(f"# HELP {c.name} {c.help}")
                lines.append(f"# TYPE {c.name} counter")
                lines.append(f"{c.name} {c.value}")
            for g in self.gauges.values():
                if g.help:
                    lines.append(f"# HELP {g.name} {g.help}")
                lines.append(f"# TYPE {g.name} gauge")
                lines.append(f"{g.name} {g.value}")
        return "\n".join(lines) + "\n"


REGISTRY = MetricsRegistry()


def get_registry() -> MetricsRegistry:
    return REGISTRY

