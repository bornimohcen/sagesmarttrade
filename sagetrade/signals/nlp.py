import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


ARABIC_RANGE = re.compile(r"[\u0600-\u06FF]")

POSITIVE_WORDS = {
    "profit",
    "surge",
    "gain",
    "bull",
    "upgrade",
    "positive",
    "rally",
    "upswing",
    "gains",
}

NEGATIVE_WORDS = {
    "loss",
    "drop",
    "fall",
    "bear",
    "downgrade",
    "negative",
    "selloff",
    "losses",
    "decline",
}

EVENT_KEYWORDS = {
    "earnings": {"earnings", "results", "quarter", "q1", "q2", "q3", "q4"},
    "ma": {"m&a", "merger", "acquisition"},
    "guidance": {"guidance", "forecast", "outlook"},
}


def clean_text(text: str) -> str:
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_language(text: str) -> str:
    if ARABIC_RANGE.search(text):
        return "ar"
    return "en"


def sentiment_score(text: str) -> float:
    text_l = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_l)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_l)
    if pos == 0 and neg == 0:
        return 0.0
    total = pos + neg
    score = (pos - neg) / float(total)
    return max(-1.0, min(1.0, score))


def detect_events(text: str) -> Dict[str, bool]:
    t = text.lower()
    events: Dict[str, bool] = {}
    for name, kws in EVENT_KEYWORDS.items():
        events[name] = any(kw.lower() in t for kw in kws)
    return events


@dataclass
class NLPSignals:
    entity: str
    sentiment: float
    event_flags: Dict[str, bool]
    impact_score: float
    language: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        return {
            "entity": self.entity,
            "sentiment": self.sentiment,
            "event_flags": self.event_flags,
            "impact_score": self.impact_score,
            "language": self.language,
        }


def get_signals(entity: str, items: Iterable[Dict[str, object]]) -> NLPSignals:
    """Aggregate sentiment/events for a given entity over a list of text items.

    For MVP, `entity` is informational only; items are assumed already filtered.
    Each item is expected to have `title` and/or `description` fields.
    """
    sentiments: List[float] = []
    agg_events: Dict[str, int] = {k: 0 for k in EVENT_KEYWORDS.keys()}
    lang_counts: Dict[str, int] = {}

    for item in items:
        title = str(item.get("title", "") or "")
        desc = str(item.get("description", "") or "")
        text = clean_text(f"{title}. {desc}").strip()
        if not text:
            continue

        lang = detect_language(text)
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

        s = sentiment_score(text)
        sentiments.append(s)
        events = detect_events(text)
        for k, v in events.items():
            if v:
                agg_events[k] += 1

    if not sentiments:
        return NLPSignals(
            entity=entity,
            sentiment=0.0,
            event_flags={k: False for k in EVENT_KEYWORDS.keys()},
            impact_score=0.0,
            language=None,
        )

    avg_sent = sum(sentiments) / float(len(sentiments))
    max_event_count = max(agg_events.values()) if agg_events else 0
    event_present = max_event_count > 0

    impact_score = min(1.0, abs(avg_sent) * 0.7 + (0.3 if event_present else 0.0))

    dominant_lang = None
    if lang_counts:
        dominant_lang = max(lang_counts.items(), key=lambda kv: kv[1])[0]

    flags = {k: v > 0 for k, v in agg_events.items()}

    return NLPSignals(
        entity=entity,
        sentiment=avg_sent,
        event_flags=flags,
        impact_score=impact_score,
        language=dominant_lang,
    )
