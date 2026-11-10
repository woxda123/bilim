from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import keyboards as kb
from ..config import LANGS, LANGS_LINE
from ..db import db
from ..i18n import SUBJECTS, subject_emoji, subject_name, t
from ..questions import bank
from ..scoring import level_of, level_title, points_to_next
from ..utils import esc, short_name, show, user_of

router = Router()
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


async def _menu_text(user) -> tuple[str, object]:
    lang = user["lang"]
    return t(lang, "menu"), kb.main_menu(lang)


# ---------- старт и главное меню ----------
@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext) -> None:
    await state.clear()
    user = await user_of(m.from_user)
    if not user["lang"]:
        await m.answer(t(None, "choose_lang"), reply_markup=kb.lang_kb("lang"))
        return
    lang = user["lang"]
    await m.answer(t(lang, "welcome", name=esc(m.from_user.first_name)))
    await m.answer(t(lang, "menu"), reply_markup=kb.main_menu(lang))


@router.message(Command("menu"))
async def cmd_menu(m: Message, state: FSMContext) -> None:
    await state.clear()
    user = await user_of(m.from_user)
    if not user["lang"]:
        await m.answer(t(None, "choose_lang"), reply_markup=kb.lang_kb("lang"))
        return
    text, markup = await _menu_text(user)
    await m.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("lang:"))
async def on_first_lang(cb: CallbackQuery) -> None:
    code = cb.data.split(":")[1]
    if code not in LANGS:
        return await cb.answer()
    await user_of(cb.from_user)
    await db.set_field(cb.from_user.id, "lang", code)
    await show(cb, t(code, "welcome", name=esc(cb.from_user.first_name)))
    await cb.message.answer(t(code, "menu"), reply_markup=kb.main_menu(code))
    await cb.answer()


@router.callback_query(F.data == "home")
async def on_home(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await user_of(cb.from_user)
    text, markup = await _menu_text(user)
    await show(cb, text, markup)
    await cb.answer()


# ---------- о боте ----------
@router.callback_query(F.data == "about")
async def on_about(cb: CallbackQuery) -> None:
    lang = (await user_of(cb.from_user))["lang"]
    await show(cb, t(lang, "about", total=bank.total(), langs=LANGS_LINE), kb.home_kb(lang))
    await cb.answer()


# ---------- статистика ----------
async def _stats_text(user) -> str:
    lang = user["lang"]
    lvl = level_of(user["xp"])
    acc = round(100 * user["correct"] / user["total"]) if user["total"] else 0
    rows = []
    for r in await db.subject_stats(user["user_id"]):
        if r["subject"] in SUBJECTS:
            pct = round(100 * r["c"] / r["t"])
            rows.append(
                t(
                    lang,
                    "stats_row",
                    emoji=subject_emoji(r["subject"]),
                    name=subject_name(lang, r["subject"]),
                    c=r["c"],
                    t=r["t"],
                    pct=pct,
                )
            )
    return t(
        lang,
        "stats",
        name=short_name(user["name"], 30),
        lvl=lvl,
        title=level_title(lang, lvl),
        xp=user["xp"],
        need=points_to_next(user["xp"]),
        acc=acc,
        c=user["correct"],
        t=user["total"],
        streak=user["streak"],
        rows="\n".join(rows) or t(lang, "stats_empty"),
    )


@router.callback_query(F.data == "stats")
async def on_stats(cb: CallbackQuery) -> None:
    user = await user_of(cb.from_user)
    await show(cb, await _stats_text(user), kb.home_kb(user["lang"]))
    await cb.answer()


@router.message(Command("stats"))
async def cmd_stats(m: Message) -> None:
    user = await user_of(m.from_user)
    if user["lang"]:
        await m.answer(await _stats_text(user), reply_markup=kb.home_kb(user["lang"]))


# ---------- рейтинг ----------
async def _rating_text(user, weekly: bool) -> str:
    lang = user["lang"]
    period = t(lang, "period_week" if weekly else "period_all")
    lines = [t(lang, "rating", period=period), ""]
    rows = await db.top(weekly, 10)
    if not rows:
        lines.append(t(lang, "rating_empty"))
    for i, r in enumerate(rows, 1):
        you = " 👈" if r["user_id"] == user["user_id"] else ""
        lines.append(f"{MEDALS.get(i, f'{i}.')} {short_name(r['name'])} — <b>{r['xp']}</b>{you}")
    mine = await db.rank_of(user["user_id"], weekly)
    if mine:
        lines += ["", t(lang, "your_place", rank=mine[0], xp=mine[1])]
    return "\n".join(lines)


@router.callback_query(F.data.startswith("rate:"))
async def on_rating(cb: CallbackQuery) -> None:
    weekly = cb.data.split(":")[1] == "week"
    user = await user_of(cb.from_user)
    await show(cb, await _rating_text(user, weekly), kb.rating_kb(user["lang"], weekly))
    await cb.answer()


@router.message(Command("top"))
async def cmd_top(m: Message) -> None:
    user = await user_of(m.from_user)
    if user["lang"]:
        await m.answer(await _rating_text(user, False), reply_markup=kb.rating_kb(user["lang"], False))


# ---------- настройки ----------
async def _show_settings(cb: CallbackQuery) -> None:
    user = await user_of(cb.from_user)
    await show(cb, t(user["lang"], "settings"), kb.settings_kb(user["lang"], user))


@router.callback_query(F.data == "settings")
async def on_settings(cb: CallbackQuery) -> None:
    await _show_settings(cb)
    await cb.answer()


@router.callback_query(F.data == "set:lang")
async def on_set_lang(cb: CallbackQuery) -> None:
    lang = (await user_of(cb.from_user))["lang"]
    await show(cb, t(lang, "choose_lang"), kb.lang_kb("setlang"))
    await cb.answer()


@router.callback_query(F.data.startswith("setlang:"))
async def on_setlang(cb: CallbackQuery) -> None:
    code = cb.data.split(":")[1]
    if code in LANGS:
        await db.set_field(cb.from_user.id, "lang", code)
    await _show_settings(cb)
    await cb.answer()


@router.callback_query(F.data == "set:count")
async def on_set_count(cb: CallbackQuery) -> None:
    lang = (await user_of(cb.from_user))["lang"]
    await show(cb, t(lang, "choose_count"), kb.count_kb(lang))
    await cb.answer()


@router.callback_query(F.data.startswith("count:"))
async def on_count(cb: CallbackQuery) -> None:
    from ..config import COUNT_OPTIONS

    n = int(cb.data.split(":")[1])
    if n in COUNT_OPTIONS:
        await db.set_field(cb.from_user.id, "q_count", n)
    await _show_settings(cb)
    await cb.answer()


@router.callback_query(F.data.in_({"set:expl", "set:shuffle"}))
async def on_toggle(cb: CallbackQuery) -> None:
    field = cb.data.split(":")[1]
    user = await user_of(cb.from_user)
    await db.set_field(cb.from_user.id, field, 0 if user[field] else 1)
    await _show_settings(cb)
    await cb.answer()


@router.callback_query(F.data == "set:reset")
async def on_reset_ask(cb: CallbackQuery) -> None:
    lang = (await user_of(cb.from_user))["lang"]
    await show(cb, t(lang, "confirm_reset"), kb.confirm_reset_kb(lang))
    await cb.answer()


@router.callback_query(F.data == "reset:yes")
async def on_reset_do(cb: CallbackQuery) -> None:
    user = await user_of(cb.from_user)
    await db.reset_stats(cb.from_user.id)
    await show(cb, t(user["lang"], "reset_done"), kb.home_kb(user["lang"]))
    await cb.answer()
