"""Загрузка и валидация базы вопросов (data/questions/*.json)."""
import json
import random
from dataclasses import dataclass
from typing import Any

from .config import DEFAULT_LANG, LANGS, QUESTIONS_DIR
from .translit import question_text_to_cyrillic as _cyr


@dataclass(frozen=True)
class Question:
    id: str
    subject: str
    difficulty: int
    q: dict[str, str]
    o: Any  # list (общие варианты) или {lang: [..]}
    a: int
    e: dict[str, str]

    # Узбекская кириллица (uzc): явный текст в JSON приоритетнее, иначе берётся
    # транслитерация узбекской латиницы; русский текст нужен, чтобы не трогать
    # английские слова и формулы.
    def text(self, lang: str) -> str:
        if lang == "uzc" and "uzc" not in self.q and "uz" in self.q:
            return _cyr(self.q["uz"], self.q.get(DEFAULT_LANG, ""))
        return self.q.get(lang) or self.q[DEFAULT_LANG]

    def options(self, lang: str) -> list[str]:
        if isinstance(self.o, list):
            return self.o
        if lang == "uzc" and "uzc" not in self.o and "uz" in self.o:
            ref = self.o.get(DEFAULT_LANG, self.o["uz"])
            return [_cyr(u, r) for u, r in zip(self.o["uz"], ref)]
        return self.o.get(lang) or self.o[DEFAULT_LANG]

    def explanation(self, lang: str) -> str:
        if lang == "uzc" and "uzc" not in self.e and "uz" in self.e:
            return _cyr(self.e["uz"], self.e.get(DEFAULT_LANG, ""))
        return self.e.get(lang) or self.e.get(DEFAULT_LANG, "")


class QuestionBank:
    def __init__(self) -> None:
        self.by_id: dict[str, Question] = {}
        self.by_subject: dict[str, list[Question]] = {}

    def load(self) -> None:
        self.by_id.clear()
        self.by_subject.clear()
        for path in sorted(QUESTIONS_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            subject = data["subject"]
            for raw in data["questions"]:
                q = self._build(subject, raw, path.name)
                if q.id in self.by_id:
                    raise ValueError(f"{path.name}: повторяющийся id {q.id}")
                self.by_id[q.id] = q
                self.by_subject.setdefault(subject, []).append(q)

    @staticmethod
    def _build(subject: str, raw: dict, fname: str) -> Question:
        qid = raw["id"]
        where = f"{fname}:{qid}"
        if DEFAULT_LANG not in raw["q"]:
            raise ValueError(f"{where}: нет текста на {DEFAULT_LANG}")
        if set(raw["q"]) - set(LANGS):
            raise ValueError(f"{where}: неизвестный язык в q")
        opts = raw["o"]
        lists = [opts] if isinstance(opts, list) else list(opts.values())
        if isinstance(opts, dict) and DEFAULT_LANG not in opts:
            raise ValueError(f"{where}: нет вариантов на {DEFAULT_LANG}")
        size = len(lists[0])
        if not 2 <= size <= 4 or any(len(x) != size for x in lists):
            raise ValueError(f"{where}: должно быть 2-4 варианта, одинаково во всех языках")
        if not 0 <= raw["a"] < size:
            raise ValueError(f"{where}: индекс ответа вне диапазона")
        d = raw.get("d", 1)
        if d not in (1, 2, 3):
            raise ValueError(f"{where}: сложность должна быть 1-3")
        return Question(qid, subject, d, raw["q"], opts, raw["a"], raw.get("e", {}))

    def count(self, subject: str | None = None, difficulty: int | None = None) -> int:
        return len(self._pool(subject, difficulty))

    def _pool(self, subject: str | None, difficulty: int | None) -> list[Question]:
        pool = (
            list(self.by_id.values())
            if subject in (None, "mix")
            else self.by_subject.get(subject, [])
        )
        if difficulty:
            pool = [q for q in pool if q.difficulty == difficulty]
        return pool

    def pick(self, subject: str, difficulty: int | None, n: int) -> list[str]:
        pool = self._pool(subject, difficulty)
        return [q.id for q in random.sample(pool, min(n, len(pool)))]

    def total(self) -> int:
        return len(self.by_id)


bank = QuestionBank()
