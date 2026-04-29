"""Tracks which topics have been used so the tool never repeats itself."""

import json
import random
import re
from pathlib import Path

HISTORY_FILE = Path("history.json")


def _load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_history(history: dict):
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def parse_topic_list(path: str) -> dict:
    """Parse a numbered markdown list → {1: "topic text", 2: ...}"""
    topics = {}
    pattern = re.compile(r"^\s*(\d+)\.\s+(.+)$")
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            topics[int(m.group(1))] = m.group(2).strip()
    return topics


def pick_topic(app_key: str, topic_list_path: str) -> tuple:
    """
    Pick a random topic that hasn't been used yet.
    Returns (topic_number, topic_text).
    Resets the history for this app automatically when all topics are exhausted.
    """
    topics = parse_topic_list(topic_list_path)
    total  = len(topics)

    history = _load_history()
    used    = set(history.get(app_key, []))
    available = [n for n in topics if n not in used]

    if not available:
        print(f"  All {total} topics used — resetting history for {app_key} and starting fresh.")
        history[app_key] = []
        _save_history(history)
        available = list(topics.keys())

    chosen = random.choice(available)
    return chosen, topics[chosen]


def pick_topics(app_key: str, topic_list_path: str, count: int) -> list:
    """Pick `count` unique unused topics in one shot. Returns [(number, text), ...]."""
    topics  = parse_topic_list(topic_list_path)
    total   = len(topics)
    history = _load_history()
    used    = set(history.get(app_key, []))

    available = [n for n in topics if n not in used]

    if len(available) < count:
        shortfall = count - len(available)
        print(f"  Only {len(available)} topics left — resetting history for {app_key} to fill the rest.")
        history[app_key] = []
        _save_history(history)
        extra = random.sample([n for n in topics if n not in available], min(shortfall, total))
        available = available + extra

    chosen = random.sample(available, min(count, len(available)))
    return [(n, topics[n]) for n in chosen]


def mark_used(app_key: str, topic_number: int, total: int):
    """Append topic number to history after a successful run."""
    history = _load_history()
    used    = history.get(app_key, [])

    if topic_number not in used:
        used.append(topic_number)

    history[app_key] = used
    _save_history(history)

    remaining = total - len(used)
    print(f"  History updated — topic #{topic_number} done. {remaining}/{total} remaining.")


def get_next_pillar(app_key: str) -> int:
    """Return next pillar (1/2/3) cycling for grid rhythm. Never repeats consecutively."""
    history  = _load_history()
    last     = history.get(f"{app_key}_pillar", 0)
    return (last % 3) + 1


def mark_pillar(app_key: str, pillar_num: int):
    history = _load_history()
    history[f"{app_key}_pillar"] = pillar_num
    _save_history(history)


def show_history(app_key: str, topic_list_path: str):
    """Print a summary of used vs remaining topics."""
    topics  = parse_topic_list(topic_list_path)
    total   = len(topics)
    history = _load_history()
    used    = set(history.get(app_key, []))

    print(f"\n  {app_key} — {len(used)}/{total} topics used")
    print(f"  Remaining: {total - len(used)}")
    if used:
        print(f"  Used numbers: {sorted(used)}")
