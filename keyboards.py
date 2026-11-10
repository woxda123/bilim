from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import COUNT_OPTIONS, LANGS
from .i18n import LANG_LABELS, SUBJECTS, subject_emoji, subject_name, t
from .questions import bank

LETTERS = "ABCD"


def lang_kb(prefix: str = "lang") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code in LANGS:
        b.button(text=LANG_LABELS[code], callback_data=f"{prefix}:{code}")
    b.adjust(2)
    return b.as_markup()


def main_menu(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_test"), callback_data="subjects")
    b.button(text=t(lang, "btn_mistakes"), callback_data="mistakes")
    b.button(text=t(lang, "btn_stats"), callback_data="stats")
    b.button(text=t(lang, "btn_rating"), callback_data="rate:all")
    b.button(text=t(lang, "btn_settings"), callback_data="settings")
    b.button(text=t(lang, "btn_about"), callback_data="about")
    b.adjust(1, 1, 2, 2)
    return b.as_markup()


def home_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_home"), callback_data="home")
    return b.as_markup()


def subjects_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for sid in SUBJECTS:
        n = bank.count(sid)
        if n:
            b.button(
                text=f"{subject_emoji(sid)} {subject_name(lang, sid)} · {n}",
                callback_data=f"subj:{sid}",
            )
    b.button(text=t(lang, "mix"), callback_data="subj:mix")
    b.button(text=t(lang, "btn_home"), callback_data="home")
    b.adjust(2)
    return b.as_markup()


def difficulty_kb(lang: str, subject: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "diff_all"), callback_data=f"go:{subject}:0")
    for d in (1, 2, 3):
        if bank.count(subject, d):
            b.button(text=t(lang, f"diff_{d}"), callback_data=f"go:{subject}:{d}")
    b.button(text=t(lang, "btn_back"), callback_data="subjects")
    b.adjust(1, 3, 1)
    return b.as_markup()


def answer_kb(n_options: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i in range(n_options):
        b.button(text=LETTERS[i], callback_data=f"ans:{i}")
    b.adjust(n_options if n_options <= 4 else 2)
    b.row(InlineKeyboardButton(text="⛔", callback_data="stop"))
    return b.as_markup()


def next_kb(lang: str, last: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(
        text=t(lang, "btn_finish" if last else "btn_next"),
        callback_data="finish" if last else "next",
    )
    return b.as_markup()


def result_kb(lang: str, subject: str, diff: int, mode: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    again = "mistakes" if mode == "mistakes" else f"go:{subject}:{diff}"
    b.button(text=t(lang, "btn_again"), callback_data=again)
    b.button(text=t(lang, "btn_rating"), callback_data="rate:all")
    b.button(text=t(lang, "btn_home"), callback_data="home")
    b.adjust(1, 2)
    return b.as_markup()


def rating_kb(lang: str, weekly: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=("• " if not weekly else "") + t(lang, "btn_all"), callback_data="rate:all")
    b.button(text=("• " if weekly else "") + t(lang, "btn_week"), callback_data="rate:week")
    b.button(text=t(lang, "btn_home"), callback_data="home")
    b.adjust(2, 1)
    return b.as_markup()


def settings_kb(lang: str, user) -> InlineKeyboardMarkup:
    on, off = t(lang, "on"), t(lang, "off")
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "set_lang"), callback_data="set:lang")
    b.button(text=t(lang, "set_count", n=user["q_count"]), callback_data="set:count")
    b.button(
        text=t(lang, "set_expl", state=on if user["expl"] else off), callback_data="set:expl"
    )
    b.button(
        text=t(lang, "set_shuffle", state=on if user["shuffle"] else off),
        callback_data="set:shuffle",
    )
    b.button(text=t(lang, "set_reset"), callback_data="set:reset")
    b.button(text=t(lang, "btn_home"), callback_data="home")
    b.adjust(1)
    return b.as_markup()


def count_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for n in COUNT_OPTIONS:
        b.button(text=str(n), callback_data=f"count:{n}")
    b.button(text=t(lang, "btn_back"), callback_data="settings")
    b.adjust(4, 1)
    return b.as_markup()


def confirm_reset_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_yes"), callback_data="reset:yes")
    b.button(text=t(lang, "btn_no"), callback_data="settings")
    b.adjust(2)
    return b.as_markup()
