"""Which geography codes the site can draw on a map (site/src/data/geo, ONS boundaries)."""

import json
from functools import cache

from datatales.config import WORKER_DIR

GEO_DIR = WORKER_DIR.parent / "site" / "src" / "data" / "geo"
FILES = ("nations.json", "regions.json", "local-authorities.json")


@cache
def boundary_codes() -> tuple[frozenset[str], ...]:
    out = []
    for name in FILES:
        path = GEO_DIR / name
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append(frozenset(f["code"] for f in data["features"]))
    return tuple(out)


def mappable(codes: set[str]) -> bool:
    """True when one boundary file has every code (the site draws one file per map)."""
    return bool(codes) and any(codes <= file for file in boundary_codes())
