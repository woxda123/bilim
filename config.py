import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS: set[int] = {
    int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
}

DB_PATH: Path = BASE_DIR / "data" / "wox.db"
QUESTIONS_DIR: Path = BASE_DIR / "data" / "questions"

BOT_NAME = "WOX · База знаний"
LANGS = ("ru", "uz", "uzc", "en")  # uzc — узбекский кириллицей
DEFAULT_LANG = "ru"
LANGS_LINE = "русский, o'zbek, ўзбек, English"

# Баллы за правильный ответ по сложности (1 — лёгкий, 2 — средний, 3 — сложный)
POINTS_BY_DIFFICULTY = {1: 10, 2: 15, 3: 25}
STREAK_BONUS_EVERY = 3  # каждые 3 правильных подряд даёт +5
STREAK_BONUS = 5

COUNT_OPTIONS = (5, 10, 15, 20)
DEFAULT_COUNT = 10
