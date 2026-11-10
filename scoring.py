from .config import (
    POINTS_BY_DIFFICULTY,
    STREAK_BONUS,
    STREAK_BONUS_EVERY,
)
from .i18n import t


def points_for(difficulty: int, streak: int) -> int:
    """Баллы за верный ответ. streak — серия верных подряд, включая этот ответ."""
    pts = POINTS_BY_DIFFICULTY.get(difficulty, 10)
    if streak and streak % STREAK_BONUS_EVERY == 0:
        pts += STREAK_BONUS
    return pts


def level_of(xp: int) -> int:
    return int((max(xp, 0) / 50) ** 0.5) + 1


def points_to_next(xp: int) -> int:
    lvl = level_of(xp)
    return lvl * lvl * 50 - xp


def level_title(lang: str, lvl: int) -> str:
    titles = t(lang, "levels")
    return titles[min(lvl - 1, len(titles) - 1)]


def grade_key(pct: int) -> str:
    if pct >= 90:
        return "grade_4"
    if pct >= 70:
        return "grade_3"
    if pct >= 50:
        return "grade_2"
    return "grade_1"
