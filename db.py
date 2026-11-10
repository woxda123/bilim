import time
from datetime import date, timedelta

import aiosqlite

from .config import DB_PATH, DEFAULT_COUNT, DEFAULT_LANG

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    name      TEXT NOT NULL DEFAULT '',
    lang      TEXT,
    xp        INTEGER NOT NULL DEFAULT 0,
    total     INTEGER NOT NULL DEFAULT 0,
    correct   INTEGER NOT NULL DEFAULT 0,
    q_count   INTEGER NOT NULL DEFAULT 10,
    expl      INTEGER NOT NULL DEFAULT 1,
    shuffle   INTEGER NOT NULL DEFAULT 1,
    streak    INTEGER NOT NULL DEFAULT 0,
    last_day  TEXT,
    created   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS answers (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL,
    qid      TEXT NOT NULL,
    subject  TEXT NOT NULL,
    correct  INTEGER NOT NULL,
    pts      INTEGER NOT NULL,
    ts       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_answers_user ON answers(user_id);
CREATE INDEX IF NOT EXISTS idx_answers_ts ON answers(ts);
CREATE TABLE IF NOT EXISTS mistakes (
    user_id INTEGER NOT NULL,
    qid     TEXT NOT NULL,
    PRIMARY KEY (user_id, qid)
);
"""

ALLOWED_FIELDS = {"lang", "q_count", "expl", "shuffle"}


class Database:
    def __init__(self) -> None:
        self.conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(DB_PATH)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def _one(self, sql: str, args: tuple = ()):
        cur = await self.conn.execute(sql, args)
        return await cur.fetchone()

    async def _all(self, sql: str, args: tuple = ()):
        cur = await self.conn.execute(sql, args)
        return await cur.fetchall()

    # ---------- users ----------
    async def get_user(self, user_id: int):
        return await self._one("SELECT * FROM users WHERE user_id=?", (user_id,))

    async def ensure_user(self, user_id: int, name: str):
        await self.conn.execute(
            "INSERT INTO users(user_id, name, q_count, created) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET name=excluded.name",
            (user_id, name, DEFAULT_COUNT, int(time.time())),
        )
        await self.conn.commit()
        return await self.get_user(user_id)

    async def set_field(self, user_id: int, field: str, value) -> None:
        if field not in ALLOWED_FIELDS:
            raise ValueError(field)
        await self.conn.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
        await self.conn.commit()

    async def lang_of(self, user_id: int) -> str:
        row = await self._one("SELECT lang FROM users WHERE user_id=?", (user_id,))
        return (row["lang"] if row and row["lang"] else DEFAULT_LANG)

    async def count_users(self) -> int:
        row = await self._one("SELECT COUNT(*) AS c FROM users")
        return row["c"]

    async def all_user_ids(self) -> list[int]:
        return [r["user_id"] for r in await self._all("SELECT user_id FROM users")]

    # ---------- answers ----------
    async def record_answer(
        self, user_id: int, qid: str, subject: str, correct: bool, pts: int
    ) -> None:
        now = int(time.time())
        await self.conn.execute(
            "INSERT INTO answers(user_id, qid, subject, correct, pts, ts) VALUES(?,?,?,?,?,?)",
            (user_id, qid, subject, int(correct), pts, now),
        )
        await self.conn.execute(
            "UPDATE users SET xp=xp+?, total=total+1, correct=correct+? WHERE user_id=?",
            (pts, int(correct), user_id),
        )
        if correct:
            await self.conn.execute(
                "DELETE FROM mistakes WHERE user_id=? AND qid=?", (user_id, qid)
            )
        else:
            await self.conn.execute(
                "INSERT OR IGNORE INTO mistakes(user_id, qid) VALUES(?,?)", (user_id, qid)
            )
        await self.conn.commit()

    async def touch_streak(self, user_id: int) -> None:
        today = date.today()
        row = await self.get_user(user_id)
        last = row["last_day"]
        if last == today.isoformat():
            return
        streak = row["streak"] + 1 if last == (today - timedelta(days=1)).isoformat() else 1
        await self.conn.execute(
            "UPDATE users SET streak=?, last_day=? WHERE user_id=?",
            (streak, today.isoformat(), user_id),
        )
        await self.conn.commit()

    async def subject_stats(self, user_id: int):
        return await self._all(
            "SELECT subject, SUM(correct) AS c, COUNT(*) AS t FROM answers "
            "WHERE user_id=? GROUP BY subject ORDER BY t DESC",
            (user_id,),
        )

    # ---------- mistakes ----------
    async def get_mistakes(self, user_id: int, limit: int) -> list[str]:
        rows = await self._all(
            "SELECT qid FROM mistakes WHERE user_id=? ORDER BY RANDOM() LIMIT ?",
            (user_id, limit),
        )
        return [r["qid"] for r in rows]

    async def count_mistakes(self, user_id: int) -> int:
        row = await self._one("SELECT COUNT(*) AS c FROM mistakes WHERE user_id=?", (user_id,))
        return row["c"]

    # ---------- rating ----------
    async def top(self, weekly: bool, limit: int = 10):
        if weekly:
            since = int(time.time()) - 7 * 86400
            return await self._all(
                "SELECT u.user_id, u.name, SUM(a.pts) AS xp FROM answers a "
                "JOIN users u ON u.user_id=a.user_id WHERE a.ts>=? "
                "GROUP BY a.user_id HAVING xp>0 ORDER BY xp DESC LIMIT ?",
                (since, limit),
            )
        return await self._all(
            "SELECT user_id, name, xp FROM users WHERE xp>0 ORDER BY xp DESC LIMIT ?", (limit,)
        )

    async def rank_of(self, user_id: int, weekly: bool) -> tuple[int, int] | None:
        if weekly:
            since = int(time.time()) - 7 * 86400
            row = await self._one(
                "SELECT COALESCE(SUM(pts),0) AS xp FROM answers WHERE user_id=? AND ts>=?",
                (user_id, since),
            )
            xp = row["xp"]
            if xp <= 0:
                return None
            ahead = await self._one(
                "SELECT COUNT(*) AS c FROM (SELECT SUM(pts) AS s FROM answers WHERE ts>=? "
                "GROUP BY user_id HAVING s>?)",
                (since, xp),
            )
        else:
            row = await self._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
            xp = row["xp"] if row else 0
            if xp <= 0:
                return None
            ahead = await self._one("SELECT COUNT(*) AS c FROM users WHERE xp>?", (xp,))
        return ahead["c"] + 1, xp

    # ---------- reset ----------
    async def reset_stats(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM answers WHERE user_id=?", (user_id,))
        await self.conn.execute("DELETE FROM mistakes WHERE user_id=?", (user_id,))
        await self.conn.execute(
            "UPDATE users SET xp=0, total=0, correct=0, streak=0, last_day=NULL WHERE user_id=?",
            (user_id,),
        )
        await self.conn.commit()


db = Database()
