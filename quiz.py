import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from .. import keyboards as kb
from ..db import db
from ..i18n import subject_emoji, subject_name, t
from ..keyboards import LETTERS
from ..questions import Question, bank
from ..scoring import grade_key, level_of, level_title, points_for
from ..utils import esc, show, user_of

router = Router()
DIFF_ICON = {1: "🟢", 2: "🟡", 3: "🔴"}


# ---------- выбор предмета и сложности ----------
@router.callback_query(F.data == "subjects")
async def on_subjects(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = (await user_of(cb.from_user))["lang"]
    await show(cb, t(lang, "choose_subject"), kb.subjects_kb(lang))
    await cb.answer()


@router.callback_query(F.data.startswith("subj:"))
async def on_subject(cb: CallbackQuery) -> None:
    subject = cb.data.split(":")[1]
    lang = (await user_of(cb.from_user))["lang"]
    text = t(
        lang,
        "subject_card",
        emoji=subject_emoji(subject),
        name=subject_name(lang, subject),
        n=bank.count(subject),
    )
    await show(cb, text, kb.difficulty_kb(lang, subject))
    await cb.answer()


# ---------- запуск теста ----------
async def _begin(cb: CallbackQuery, state: FSMContext, ids: list[str], subject: str,
                 diff: int, mode: str) -> None:
    user = await user_of(cb.from_user)
    await state.set_data(
        {
            "ids": ids, "i": 0, "c": 0, "pts": 0, "streak": 0, "answered": False,
            "subject": subject, "diff": diff, "mode": mode, "start_xp": user["xp"], "perm": [],
        }
    )
    await _send_question(cb, state, user)


@router.callback_query(F.data.startswith("go:"))
async def on_go(cb: CallbackQuery, state: FSMContext) -> None:
    _, subject, diff = cb.data.split(":")
    diff = int(diff)
    user = await user_of(cb.from_user)
    ids = bank.pick(subject, diff or None, user["q_count"])
    if not ids:
        return await cb.answer(t(user["lang"], "no_questions"), show_alert=True)
    await _begin(cb, state, ids, subject, diff, "test")


@router.callback_query(F.data == "mistakes")
async def on_mistakes(cb: CallbackQuery, state: FSMContext) -> None:
    user = await user_of(cb.from_user)
    ids = [i for i in await db.get_mistakes(user["user_id"], user["q_count"]) if i in bank.by_id]
    if not ids:
        await show(cb, t(user["lang"], "mistakes_empty"), kb.home_kb(user["lang"]))
        return await cb.answer()
    await _begin(cb, state, ids, "mix", 0, "mistakes")


# ---------- показ вопроса ----------
def _render(q: Question, lang: str, perm: list[int], i: int, n: int) -> str:
    opts = q.options(lang)
    header = t(
        lang,
        "q_header",
        emoji=subject_emoji(q.subject),
        subject=subject_name(lang, q.subject),
        i=i + 1,
        n=n,
        level=DIFF_ICON[q.difficulty],
    )
    lines = [header, "", f"<b>{esc(q.text(lang))}</b>", ""]
    lines += [f"<b>{LETTERS[k]}</b>) {esc(opts[perm[k]])}" for k in range(len(perm))]
    return "\n".join(lines)


async def _send_question(cb: CallbackQuery, state: FSMContext, user) -> None:
    data = await state.get_data()
    q = bank.by_id[data["ids"][data["i"]]]
    perm = list(range(len(q.options(user["lang"]))))
    if user["shuffle"]:
        random.shuffle(perm)
    await state.update_data(perm=perm, answered=False)
    text = _render(q, user["lang"], perm, data["i"], len(data["ids"]))
    await show(cb, text, kb.answer_kb(len(perm)))
    await cb.answer()


# ---------- ответ ----------
@router.callback_query(F.data.startswith("ans:"))
async def on_answer(cb: CallbackQuery, state: FSMContext) -> None:
    user = await user_of(cb.from_user)
    lang = user["lang"]
    data = await state.get_data()
    if not data.get("ids"):
        return await cb.answer(t(lang, "expired"), show_alert=True)
    if data["answered"]:
        return await cb.answer()

    k = int(cb.data.split(":")[1])
    perm = data["perm"]
    q = bank.by_id[data["ids"][data["i"]]]
    correct = perm[k] == q.a
    streak = data["streak"] + 1 if correct else 0
    pts = points_for(q.difficulty, streak) if correct else 0
    await db.record_answer(user["user_id"], q.id, q.subject, correct, pts)
    await state.update_data(
        answered=True, streak=streak, c=data["c"] + int(correct), pts=data["pts"] + pts
    )

    n = len(data["ids"])
    parts = [_render(q, lang, perm, data["i"], n), ""]
    if correct:
        parts.append(t(lang, "right", pts=pts))
        if streak >= 2:
            parts.append(t(lang, "streak", n=streak))
    else:
        right_letter = LETTERS[perm.index(q.a)]
        ans = f"{right_letter}) {esc(q.options(lang)[q.a])}"
        parts.append(t(lang, "wrong", ans=ans))
    expl = q.explanation(lang)
    if user["expl"] and expl:
        parts += ["", t(lang, "expl", text=esc(expl))]
    last = data["i"] >= n - 1
    await show(cb, "\n".join(parts), kb.next_kb(lang, last))
    await cb.answer("✅" if correct else "❌")


@router.callback_query(F.data == "next")
async def on_next(cb: CallbackQuery, state: FSMContext) -> None:
    user = await user_of(cb.from_user)
    data = await state.get_data()
    if not data.get("ids"):
        return await cb.answer(t(user["lang"], "expired"), show_alert=True)
    await state.update_data(i=data["i"] + 1)
    await _send_question(cb, state, user)


# ---------- итог ----------
@router.callback_query(F.data.in_({"finish", "stop"}))
async def on_finish(cb: CallbackQuery, state: FSMContext) -> None:
    user = await user_of(cb.from_user)
    lang = user["lang"]
    data = await state.get_data()
    if not data.get("ids"):
        return await cb.answer(t(lang, "expired"), show_alert=True)

    answered = data["i"] + (1 if data["answered"] else 0)
    await state.clear()
    if answered == 0:
        await show(cb, t(lang, "menu"), kb.main_menu(lang))
        return await cb.answer()

    await db.touch_streak(user["user_id"])
    fresh = await db.get_user(user["user_id"])
    pct = round(100 * data["c"] / answered)
    text = t(
        lang,
        "result",
        emoji=subject_emoji(data["subject"]) if data["mode"] == "test" else "🔁",
        subject=subject_name(lang, data["subject"]) if data["mode"] == "test" else t(lang, "mistakes_title"),
        c=data["c"],
        n=answered,
        pct=pct,
        pts=data["pts"],
        grade=t(lang, grade_key(pct)),
    )
    new_lvl, old_lvl = level_of(fresh["xp"]), level_of(data["start_xp"])
    if new_lvl > old_lvl:
        text += "\n\n" + t(lang, "levelup", lvl=new_lvl, title=level_title(lang, new_lvl))
    await show(cb, text, kb.result_kb(lang, data["subject"], data["diff"], data["mode"]))
    await cb.answer()
