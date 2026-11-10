"""Проверки контента и транслитерации (не требуют aiogram и сети).

Запуск:  python -m tests.test_content      (или pytest)
"""
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import LANGS  # noqa: E402
from bot.i18n import _STRINGS, SUBJECTS, subject_name, t  # noqa: E402
from bot.questions import bank  # noqa: E402
from bot.translit import to_cyrillic  # noqa: E402

_FMT = string.Formatter()


def _fields(value) -> set[str]:
    if isinstance(value, str):
        return {f for _, f, _, _ in _FMT.parse(value) if f}
    return set()


def test_transliteration_rules():
    cases = {
        "O'zbekiston Respublikasi": "Ўзбекистон Республикаси",
        "ma'lumot, a'zo, mas'ul": "маълумот, аъзо, масъул",
        "yo'q, yaxshi, yil, yuz, yer, yo'l, yoz": "йўқ, яхши, йил, юз, ер, йўл, ёз",
        "shahar, choy, tug'ilgan, g'oya, bog'": "шаҳар, чой, туғилган, ғоя, боғ",
        "ekran, elektr, eng": "экран, электр, энг",
        "Konstitutsiya, protsessor": "Конституция, процессор",
        "funksiya, reaksiyaga, interferensiya, stansiya": "функция, реакцияга, интерференция, станция",
        "Rossiya, Osiyo, progressiya, asosiy": "Россия, Осиё, прогрессия, асосий",
        "SHAHAR, O'ZBEKISTON": "ШАҲАР, ЎЗБЕКИСТОН",
        "<b>{name}</b> @woffix {n}": "<b>{name}</b> @woffix {n}",
        "o‘zbek, oʻzbek, o`zbek": "ўзбек, ўзбек, ўзбек",
    }
    for src, expected in cases.items():
        assert to_cyrillic(src) == expected, (src, to_cyrillic(src), expected)


def test_keep_tokens_untouched():
    assert to_cyrillic("To'g'ri: She goes", {"She", "goes"}) == "Тўғри: She goes"


def test_ui_keys_and_placeholders_match_in_all_languages():
    base = _STRINGS["ru"]
    for lang in LANGS:
        assert set(_STRINGS[lang]) == set(base), (lang, set(_STRINGS[lang]) ^ set(base))
        for key, value in base.items():
            assert _fields(_STRINGS[lang][key]) == _fields(value), (lang, key)
        assert len(_STRINGS[lang]["levels"]) == len(base["levels"]), lang


def test_ui_formats_without_error():
    for lang in LANGS:
        for key, value in _STRINGS[lang].items():
            if isinstance(value, str) and _fields(value):
                kw = {f: "x" for f in _fields(value)}
                t(lang, key, **kw)


def test_uzc_ui_is_cyrillic():
    for key, value in _STRINGS["uzc"].items():
        if key == "choose_lang" or not isinstance(value, str):
            continue
        text = re.sub(r"<[^>]+>|\{[^}]*\}|@\w+", "", value)
        # допустимая латиница: бренд и английское название
        text = re.sub(r"\b(WOX|IELTS|English)\b", "", text)
        assert not re.search(r"[A-Za-z]{2,}", text), (key, value)


def test_subject_names_all_languages():
    for sid in SUBJECTS:
        for lang in LANGS:
            assert subject_name(lang, sid).strip(), (sid, lang)


def test_every_question_complete_in_every_language():
    bank.load()
    assert bank.total() > 0
    for q in bank.by_id.values():
        for lang in LANGS:
            assert q.text(lang).strip(), (q.id, lang, "text")
            opts = q.options(lang)
            assert 2 <= len(opts) <= 4 and all(o.strip() for o in opts), (q.id, lang)
            assert len(opts) == len(q.options("ru")), (q.id, lang, "options count")
            assert q.explanation(lang).strip(), (q.id, lang, "explanation")
        assert 0 <= q.a < len(q.options("ru"))


def test_uzc_questions_have_no_leftover_uzbek_latin():
    """В кириллическом тексте латиницей допускаются лишь токены из русского текста."""
    bank.load()
    for q in bank.by_id.values():
        ru_tokens = set(re.findall(r"[A-Za-z]+", q.text("ru") + q.explanation("ru") +
                                   " ".join(q.options("ru"))))
        shown = q.text("uzc") + " " + q.explanation("uzc") + " " + " ".join(q.options("uzc"))
        for tok in re.findall(r"[A-Za-z]+", shown):
            assert tok in ru_tokens or tok in " ".join(q.options("ru")), (q.id, tok)


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("OK  ", name)
            except AssertionError as e:
                failed += 1
                print("FAIL", name, e)
    sys.exit(1 if failed else 0)
