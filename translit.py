"""Узбекская латиница -> кириллица (официальное соответствие алфавитов).

Фрагменты, которые нельзя трогать (HTML-теги, {плейсхолдеры}, @ники, английские
слова, формулы и аббревиатуры), остаются как есть. Для вопросов «чужие» токены
определяются автоматически: всё, что дословно встречается латиницей в русском
тексте того же вопроса, считается иностранным (She, goes, CPU, H₂O, pH, x…).
"""
import re
from functools import lru_cache
from typing import Iterable

APOS = "'ʻʼ’‘`´"

# защищённые сегменты: теги, плейсхолдеры, HTML-сущности, @ники, ссылки
_PROTECTED = re.compile(r"<[^>]+>|\{[^}]*\}|&\w+;|@\w+|https?://\S+")
# слово: латинские буквы, внутри допускаются апострофы между буквами (o'zbek, ma'no)
_A = re.escape(APOS)
_WORD = re.compile(rf"[A-Za-z]+(?:[{_A}][A-Za-z]+)*(?:(?<=[gGoO])[{_A}](?![A-Za-z]))?")
# заимствования: латинское «-ksiya/-nsiya/-rsional…» в кириллице пишется через «ц»
_LOAN_TS = re.compile(r"(?<=[knrpKNRP])([sS])(?=[iI](?:[yY][aAoO]|[oO][nN]))")
_LATIN_TOKEN = re.compile(r"[A-Za-z]+")

_SIMPLE = {
    "a": "а", "b": "б", "c": "с", "d": "д", "f": "ф", "g": "г", "h": "ҳ",
    "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
    "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
    "w": "в", "x": "х", "y": "й", "z": "з", "e": "е",
}


def latin_tokens(text: str) -> frozenset[str]:
    """Латинские токены текста (для определения «чужих» слов)."""
    return frozenset(_LATIN_TOKEN.findall(text or ""))


def _case(src: str, res: str) -> str:
    """Переносит регистр исходной группы букв на результат."""
    if len(src) > 1 and src.isupper():
        return res.upper()
    if src[0].isupper():
        return res[0].upper() + res[1:]
    return res


def _word(w: str) -> str:
    for a in APOS:
        w = w.replace(a, "'")
    w = _LOAN_TS.sub(lambda m: ("t" if m.group(1) == "s" else "T") + m.group(1), w)
    low = w.lower()
    out: list[str] = []
    i, n = 0, len(low)
    while i < n:
        c = low[i]
        two = low[i:i + 2]
        nxt = low[i + 1] if i + 1 < n else ""
        if two in ("o'", "g'"):
            out.append(_case(w[i:i + 2], "ў" if c == "o" else "ғ"))
            i += 2
        elif c == "'":
            out.append("ъ")
            i += 1
        elif two == "sh":
            out.append(_case(w[i:i + 2], "ш"))
            i += 2
        elif two == "ch":
            out.append(_case(w[i:i + 2], "ч"))
            i += 2
        elif two == "ts":
            out.append(_case(w[i:i + 2], "ц"))
            i += 2
        elif c == "y" and nxt in ("a", "u", "e") or (c == "y" and nxt == "o" and low[i + 2:i + 3] != "'"):
            out.append(_case(w[i:i + 2], {"a": "я", "u": "ю", "e": "е", "o": "ё"}[nxt]))
            i += 2
        elif c == "e" and i == 0:
            out.append(_case(w[i], "э"))
            i += 1
        else:
            out.append(_case(w[i], _SIMPLE.get(c, w[i])))
            i += 1
    return "".join(out)


def to_cyrillic(text: str, keep: Iterable[str] = ()) -> str:
    """Транслитерирует текст; токены из keep и защищённые сегменты не меняет."""
    if not text:
        return text
    keep = keep if isinstance(keep, (set, frozenset)) else frozenset(keep)

    def word(m: re.Match) -> str:
        token = m.group(0)
        if token[-1] in APOS and m.start() > 0 and m.string[m.start() - 1] in APOS:
            # это закрывающая кавычка ('go'), а не буква ў/ғ
            head = token[:-1]
            return (head if head in keep else _word(head)) + token[-1]
        return token if token in keep else _word(token)

    parts: list[str] = []
    pos = 0
    for m in _PROTECTED.finditer(text):
        parts.append(_WORD.sub(word, text[pos:m.start()]))
        parts.append(m.group(0))
        pos = m.end()
    parts.append(_WORD.sub(word, text[pos:]))
    return "".join(parts)


@lru_cache(maxsize=4096)
def question_text_to_cyrillic(uz: str, ru: str) -> str:
    """Вопрос/вариант/пояснение: латиница из русского текста остаётся латиницей."""
    return to_cyrillic(uz, latin_tokens(ru))


def convert_strings(obj, keep: Iterable[str] = ()):
    """Рекурсивно переводит словарь интерфейса (str / list / dict)."""
    if isinstance(obj, str):
        return to_cyrillic(obj, keep)
    if isinstance(obj, list):
        return [convert_strings(x, keep) for x in obj]
    if isinstance(obj, dict):
        return {k: convert_strings(v, keep) for k, v in obj.items()}
    return obj
