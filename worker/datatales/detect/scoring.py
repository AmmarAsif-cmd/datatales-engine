"""Score = effect x surprise x relatability x freshness. Each part is 0..1, so is the score."""

from datetime import date

from datatales.detect.base import Finding


def effect_norm(effect: float) -> float:
    """Map an unbounded effect size (>= 0) onto 0..1: 1 -> 0.5, 3 -> 0.75, 9 -> 0.9."""
    e = max(0.0, effect)
    return e / (1.0 + e)


def freshness(release: date | None, today: date) -> float:
    """1.0 for data released today, minus 0.2 per year of age, floored at 0.2."""
    if release is None:
        return 0.5
    age_years = max(0.0, (today - release).days / 365.25)
    return max(0.2, min(1.0, 1.0 - 0.2 * age_years))


def score(f: Finding, relatability: int, fresh: float) -> Finding:
    parts = {
        "effect": round(effect_norm(f.effect), 4),
        "surprise": round(max(0.0, min(1.0, f.surprise)), 4),
        "relatability": round(max(1, min(5, relatability)) / 5, 4),
        "freshness": round(fresh, 4),
    }
    f.score_parts = parts
    product = parts["effect"] * parts["surprise"] * parts["relatability"] * parts["freshness"]
    f.score = round(product, 4)
    return f
