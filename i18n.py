from .config import DEFAULT_LANG, LANGS
from .strings import en, ru, uz
from .translit import convert_strings, to_cyrillic

# Узбекская кириллица строится из латинской версии автоматически (см. translit.py).
# Латиницей остаются бренд и аббревиатуры.
_KEEP = frozenset({"WOX", "IELTS", "English"})
_UZC = convert_strings(uz.STRINGS, _KEEP)
_UZC["choose_lang"] = ru.STRINGS["choose_lang"]  # одна строка на всех языках

_STRINGS = {"ru": ru.STRINGS, "uz": uz.STRINGS, "uzc": _UZC, "en": en.STRINGS}

LANG_LABELS = {
    "ru": "🇷🇺 Русский",
    "uz": "🇺🇿 O'zbekcha",
    "uzc": "🇺🇿 Ўзбекча",
    "en": "🇬🇧 English",
}

# id: (эмодзи, названия по языкам). Для uzc название берётся из uz и транслитерируется.
SUBJECTS: dict[str, tuple[str, dict[str, str]]] = {
    "math": ("🧮", {"ru": "Математика", "uz": "Matematika", "en": "Mathematics"}),
    "physics": ("⚛️", {"ru": "Физика", "uz": "Fizika", "en": "Physics"}),
    "chemistry": ("🧪", {"ru": "Химия", "uz": "Kimyo", "en": "Chemistry"}),
    "biology": ("🧬", {"ru": "Биология", "uz": "Biologiya", "en": "Biology"}),
    "informatics": ("💻", {"ru": "Информатика", "uz": "Informatika", "en": "Computer Science"}),
    "law": ("⚖️", {"ru": "Право", "uz": "Huquq", "en": "Law"}),
    "english": ("🇬🇧", {"ru": "Английский язык", "uz": "Ingliz tili", "en": "English"}),
    "ielts": ("🎓", {"ru": "IELTS", "uz": "IELTS", "en": "IELTS"}),
    "history": ("🏛", {"ru": "История Узбекистана", "uz": "O'zbekiston tarixi", "en": "History of Uzbekistan"}),
}


def norm_lang(lang: str | None) -> str:
    return lang if lang in LANGS else DEFAULT_LANG


def t(lang: str | None, key: str, **kw) -> str:
    lang = norm_lang(lang)
    text = _STRINGS[lang].get(key) or _STRINGS[DEFAULT_LANG].get(key, key)
    return text.format(**kw) if kw and isinstance(text, str) else text


def subject_name(lang: str | None, subject: str) -> str:
    if subject == "mix":
        return t(lang, "mix")
    _, names = SUBJECTS[subject]
    lang = norm_lang(lang)
    if lang == "uzc":
        return names["uz"] if subject == "ielts" else to_cyrillic(names["uz"], _KEEP)
    return names.get(lang, names["ru"])


def subject_emoji(subject: str) -> str:
    return "🎲" if subject == "mix" else SUBJECTS[subject][0]
