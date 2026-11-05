"""Rule-based matching of a client's request to experts.

Deliberately simple and explainable: every point an expert scores comes with a
plain-language reason shown to the client. It can later be swapped for
embeddings or a learned ranker behind the same `match_experts` function.
"""
import re
from dataclasses import dataclass, field

from .constants import CATEGORY_KEYWORDS

WORD = re.compile(r"[a-z0-9]+")

WEIGHT_CATEGORY = 5.0
WEIGHT_SKILL = 2.0
WEIGHT_HUB = 1.5
WEIGHT_RATING = 1.0  # multiplied by (rating - 4), so 4.9 adds 0.9


def tokenize(text: str) -> set[str]:
    return set(WORD.findall((text or "").lower()))


def guess_category(description: str) -> str | None:
    """Best category for free text, or None when nothing matches."""
    words = tokenize(description)
    scores = {cat: len(words & kws) for cat, kws in CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


@dataclass
class Match:
    expert: dict
    score: float
    reasons: list[str] = field(default_factory=list)
    relevant: bool = False


def score_expert(expert, category: str, words: set[str], hub_pref: str | None) -> Match:
    m = Match(expert=dict(expert), score=0.0)
    m.relevant = False

    if expert["category"] == category:
        m.relevant = True
        m.score += WEIGHT_CATEGORY
        m.reasons.append("Works in the area you chose")

    skill_hits = [
        s.strip() for s in expert["skills"].split(",")
        if tokenize(s) & words
    ]
    if skill_hits:
        m.relevant = True
        m.score += WEIGHT_SKILL * len(skill_hits)
        m.reasons.append("Skills that fit your request: " + ", ".join(skill_hits))

    if hub_pref and expert["hub"] == hub_pref:
        m.score += WEIGHT_HUB
        m.reasons.append(f"Based in {expert['hub']}, as you preferred")

    m.score += WEIGHT_RATING * max(expert["rating"] - 4, 0)
    return m


def match_experts(db, category: str, description: str,
                  hub_pref: str | None = None, limit: int = 3) -> list[Match]:
    experts = db.execute("SELECT * FROM experts WHERE is_active = 1").fetchall()
    words = tokenize(description)
    matches = [score_expert(e, category, words, hub_pref) for e in experts]
    # Location and rating only rank experts; they never make one relevant.
    matches = [m for m in matches if m.relevant]
    matches.sort(key=lambda m: (m.score, m.expert["rating"]), reverse=True)
    return matches[:limit]
