"""Run every registered detector over a clean table and keep the top findings."""

from datetime import date
from typing import Any

import pandas as pd

from datatales.detect import REGISTRY, Finding
from datatales.detect.prepare import prepare
from datatales.detect.scoring import freshness, score
from datatales.sources import DetectConfig


def run_detectors(
    clean: pd.DataFrame,
    config: DetectConfig,
    relatability: int,
    release: date | None,
    today: date,
    detectors: list[str] | None = None,
) -> tuple[list[Finding], int]:
    """Returns (top findings by score, number of distinct candidates found)."""
    frame, meta = prepare(clean, config)
    fresh = freshness(release, today)
    found: dict[tuple[Any, ...], Finding] = {}
    for name in detectors or sorted(REGISTRY):
        for f in REGISTRY[name](frame, meta):
            f = score(f, relatability, fresh)
            if f.key not in found or f.score > found[f.key].score:
                found[f.key] = f
    ranked = sorted(
        found.values(),
        key=lambda f: (-f.score, f.detector, str(f.numbers.get("group")), f.title_hint),
    )
    return merge_related(ranked)[: config.top_n], len(found)


def merge_related(ranked: list[Finding]) -> list[Finding]:
    """One finding per (slice, group): the best-scoring one keeps its place and carries the
    others' numbers under `related`, so a story can use them without wasting top-N slots."""
    kept: dict[tuple[Any, ...], Finding] = {}
    for f in ranked:
        k = (tuple(sorted(f.slice.items())), f.numbers.get("group"))
        if k not in kept:
            kept[k] = f
            continue
        extra = {key: v for key, v in f.numbers.items() if key not in f.slice}
        related = kept[k].numbers.setdefault("related", [])
        related.append({"detector": f.detector, "title_hint": f.title_hint, "numbers": extra})
    return list(kept.values())


def finding_record(f: Finding) -> dict[str, Any]:
    """What gets stored in `findings`: the exact numbers plus how the score was built."""
    return {
        "detector": f.detector,
        "title_hint": f.title_hint,
        "score": f.score,
        "numbers": {**f.numbers, "score_parts": f.score_parts, "effect_size": round(f.effect, 4)},
    }
