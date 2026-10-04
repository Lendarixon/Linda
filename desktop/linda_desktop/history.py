# -*- coding: utf-8 -*-
"""Local history of checks ("cabinet"): a SQLite file in the app data folder. Nothing leaves the machine.

Each check keeps the text and the full result (compressed). Settings: "save_history" (default on) switches saving off; everything can be deleted from the UI."""
from __future__ import annotations

import contextlib
import difflib
import hashlib
import json
import re
import sqlite3
import threading
import time
import zlib

from . import config

_LOCK = threading.Lock()
SCHEMA = """CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, title TEXT NOT NULL, filename TEXT, mode TEXT, verdict TEXT,
    pct INTEGER, ai_share REAL, authorship TEXT, words INTEGER, sha TEXT, text BLOB, result BLOB)"""


@contextlib.contextmanager
def _db():
    """Open, commit and always close the connection (the plain `with sqlite3.connect()` only commits)."""
    con = sqlite3.connect(str(config.data_dir() / "history.db"))
    con.row_factory = sqlite3.Row
    try:
        con.execute(SCHEMA)
        con.execute("CREATE TABLE IF NOT EXISTS folders (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, color TEXT, ts REAL NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '')")
        if "folder_id" not in {r[1] for r in con.execute("PRAGMA table_info(checks)")}:  # databases made by 1.2 before folders existed
            con.execute("ALTER TABLE checks ADD COLUMN folder_id INTEGER")
        yield con
        con.commit()
    finally:
        con.close()


def audit(action: str, detail: str = "") -> int:
    """Записать событие в журнал аудита (для корпоративных клиентов): кто/что/когда, локально."""
    with _LOCK, _db() as con:
        cur = con.execute("INSERT INTO audit (ts, action, detail) VALUES (?,?,?)",
                          (time.time(), str(action)[:60], str(detail)[:2000]))
        return int(cur.lastrowid)


def audit_list(action: str = "", limit: int = 200, offset: int = 0) -> list[dict]:
    """Прочитать журнал аудита: новые первыми. action='' — все действия."""
    sql, args = "SELECT id, ts, action, detail FROM audit", []
    if action:
        sql += " WHERE action = ?"
        args.append(action)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    with _LOCK, _db() as con:
        return [dict(r) for r in con.execute(sql, (*args, min(max(int(limit), 1), 1000), max(int(offset), 0)))]


def audit_clear() -> int:
    """Очистить журнал аудита (действие само фиксируется отдельной записью после очистки)."""
    with _LOCK, _db() as con:
        n = con.execute("DELETE FROM audit").rowcount
    audit("audit_clear", "журнал очищен (%d записей)" % n)
    return n


def _pack(obj) -> bytes:
    return zlib.compress(json.dumps(obj, ensure_ascii=False).encode("utf-8"), 6)


def _unpack(b: bytes):
    return json.loads(zlib.decompress(b).decode("utf-8"))


def _title(text: str, filename: str | None) -> str:
    if filename:
        return filename
    first = re.sub(r"\s+", " ", text.strip())[:60]
    return first or "(untitled)"


def add(text: str, res: dict, mode: str, title: str | None = None, filename: str | None = None, folder_id: int | None = None) -> int:
    sent = res.get("sentences") or []
    tot = sum(max(1, len(s["text"].split())) for s in sent) or 1
    ai_share = sum(max(1, len(s["text"].split())) for s in sent if s.get("label") == "ai") / tot if res.get('heatmap_available',True) else None
    pct = None
    if res.get("p_ai") is not None or res.get("ens_z") is not None:
        import math

        pct = min(99, max(1, round(float(res["p_ai"]) * 100))) if res.get("p_ai") is not None else min(99, max(1, round(100 / (1 + math.exp(-1.7 * float(res["ens_z"]))))))
    row = (time.time(), (title or _title(text, filename))[:200], filename, mode, res.get("verdict"), pct, round(ai_share, 4) if ai_share is not None else None,
           (res.get("authorship") or {}).get("label"), len(text.split()), hashlib.sha256(text.encode("utf-8")).hexdigest(),
           zlib.compress(text.encode("utf-8"), 6), _pack(res), folder_id or None)
    with _LOCK, _db() as con:
        cur = con.execute("INSERT INTO checks (ts,title,filename,mode,verdict,pct,ai_share,authorship,words,sha,text,result,folder_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
        return int(cur.lastrowid)


LIST_COLS = "id,ts,title,filename,mode,verdict,pct,ai_share,authorship,words,sha,folder_id"
SORTS = {"date": "ts", "title": "title COLLATE NOCASE", "ai": "ai_share", "words": "words", "verdict": "verdict", "pct": "pct"}


def list_checks(q: str = "", verdict: str = "", limit: int = 200, offset: int = 0, folder: int | None = None, sort: str = "date", order: str = "desc") -> list[dict]:
    """folder: None = everything, 0 = not in any folder, N = that folder."""
    sql, args = f"SELECT {LIST_COLS} FROM checks", []
    where = []
    if q:
        where.append("title LIKE ?")
        args.append(f"%{q}%")
    if verdict in ("ai", "human", "uncertain"):
        where.append("verdict = ?")
        args.append(verdict)
    if folder == 0:
        where.append("folder_id IS NULL")
    elif folder:
        where.append("folder_id = ?")
        args.append(int(folder))
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {SORTS.get(sort, 'ts')} {'ASC' if order == 'asc' else 'DESC'}, id DESC LIMIT ? OFFSET ?"
    with _LOCK, _db() as con:
        return [dict(r) for r in con.execute(sql, (*args, int(limit), int(offset)))]


def folders() -> list[dict]:
    """Folders with the number of checks in each, plus the virtual counts for 'all' and 'unsorted'."""
    with _LOCK, _db() as con:
        rows = [dict(r) for r in con.execute("SELECT f.id, f.name, f.color, (SELECT COUNT(*) FROM checks c WHERE c.folder_id = f.id) AS n FROM folders f ORDER BY f.name COLLATE NOCASE")]
        total = con.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
        unsorted = con.execute("SELECT COUNT(*) FROM checks WHERE folder_id IS NULL").fetchone()[0]
    return {"folders": rows, "total": int(total), "unsorted": int(unsorted)}


def folder_add(name: str, color: str | None = None) -> int:
    with _LOCK, _db() as con:
        return int(con.execute("INSERT INTO folders (name, color, ts) VALUES (?,?,?)", (name.strip()[:80] or "New folder", color, time.time())).lastrowid)


def folder_update(folder_id: int, name: str | None = None, color: str | None = None) -> bool:
    with _LOCK, _db() as con:
        n = 0
        if name is not None:
            n += con.execute("UPDATE folders SET name = ? WHERE id = ?", (name.strip()[:80] or "Folder", int(folder_id))).rowcount
        if color is not None:
            n += con.execute("UPDATE folders SET color = ? WHERE id = ?", (color, int(folder_id))).rowcount
        return n > 0


def folder_delete(folder_id: int, with_checks: bool = False) -> int:
    """Removes the folder; its checks go back to 'unsorted' unless with_checks is set (then they are deleted too). Returns how many checks were deleted."""
    with _LOCK, _db() as con:
        deleted = 0
        if with_checks:
            deleted = con.execute("DELETE FROM checks WHERE folder_id = ?", (int(folder_id),)).rowcount
        else:
            con.execute("UPDATE checks SET folder_id = NULL WHERE folder_id = ?", (int(folder_id),))
        con.execute("DELETE FROM folders WHERE id = ?", (int(folder_id),))
        return deleted


def move(ids: list[int], folder_id: int | None) -> int:
    ids = [int(i) for i in ids]
    if not ids:
        return 0
    with _LOCK, _db() as con:
        return con.execute(f"UPDATE checks SET folder_id = ? WHERE id IN ({','.join('?' * len(ids))})", (folder_id or None, *ids)).rowcount


def delete_many(ids: list[int]) -> int:
    ids = [int(i) for i in ids]
    if not ids:
        return 0
    with _LOCK, _db() as con:
        return con.execute(f"DELETE FROM checks WHERE id IN ({','.join('?' * len(ids))})", ids).rowcount


def purge_older_than(days: int) -> int:
    """Retention: delete checks older than `days` (0 = keep forever)."""
    if days <= 0:
        return 0
    with _LOCK, _db() as con:
        return con.execute("DELETE FROM checks WHERE ts < ?", (time.time() - days * 86400,)).rowcount


def get(check_id: int) -> dict | None:
    with _LOCK, _db() as con:
        r = con.execute("SELECT * FROM checks WHERE id = ?", (int(check_id),)).fetchone()
    if r is None:
        return None
    d = {k: r[k] for k in r.keys() if k not in ("text", "result")}
    d["text"] = zlib.decompress(r["text"]).decode("utf-8")
    d["result"] = _unpack(r["result"])
    return d


def rename(check_id: int, title: str) -> bool:
    with _LOCK, _db() as con:
        return con.execute("UPDATE checks SET title = ? WHERE id = ?", (title.strip()[:200] or "(untitled)", int(check_id))).rowcount > 0


def delete(check_id: int) -> bool:
    with _LOCK, _db() as con:
        return con.execute("DELETE FROM checks WHERE id = ?", (int(check_id),)).rowcount > 0


def clear() -> int:
    with _LOCK, _db() as con:
        n = con.execute("DELETE FROM checks").rowcount
    with _LOCK:
        con = sqlite3.connect(str(config.data_dir() / "history.db"), isolation_level=None)
        try:
            con.execute("VACUUM")  # give the disk space back
        finally:
            con.close()
    return n


def stats() -> dict:
    with _LOCK, _db() as con:
        r = con.execute("SELECT COUNT(*) n, SUM(verdict='ai') ai, SUM(verdict='uncertain') unc, SUM(verdict='human') hum, SUM(words) words FROM checks").fetchone()
    return {k: int(r[k] or 0) for k in r.keys()}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def compare(a: dict, b: dict) -> dict:
    """Align the sentences of two checks (A = earlier / original, B = later / revised) and show how the colouring changed."""
    sa, sb = a["result"].get("sentences") or [], b["result"].get("sentences") or []
    na, nb = [_norm(x["text"]) for x in sa], [_norm(x["text"]) for x in sb]
    sm = difflib.SequenceMatcher(None, na, nb, autojunk=False)

    def cell(s):
        return {"text": s["text"], "label": s["label"], "p_ai": s["p_ai"]}

    rows = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            rows += [{"kind": "same", "a": cell(sa[i]), "b": cell(sb[j])} for i, j in zip(range(i1, i2), range(j1, j2))]
        else:
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                x = sa[i1 + k] if i1 + k < i2 else None
                y = sb[j1 + k] if j1 + k < j2 else None
                kind = "changed" if x and y else ("removed" if x else "added")
                rows.append({"kind": kind, "a": cell(x) if x else None, "b": cell(y) if y else None})

    def summary(c: dict) -> dict:
        r = c["result"]
        sent = r.get("sentences") or []
        tot = sum(max(1, len(s["text"].split())) for s in sent) or 1
        return {"id": c["id"], "title": c["title"], "ts": c["ts"], "verdict": r.get("verdict"), "pct": c.get("pct"), "words": c["words"],
                "authorship": r.get("authorship"), "sentences": len(sent),
                "ai_words_share": round(sum(max(1, len(s["text"].split())) for s in sent if s["label"] == "ai") / tot, 4)}

    shared = shared_passages(a["text"], b["text"])
    ta, tb = _norm(a["text"]), _norm(b["text"])
    return {"a": summary(a), "b": summary(b), "similarity": round(difflib.SequenceMatcher(None, na, nb, autojunk=False).ratio(), 4),
            "text_equal": ta == tb, "rows": rows, "shared": shared,
            "counts": {k: sum(1 for r in rows if r["kind"] == k) for k in ("same", "changed", "added", "removed")}}


_TOKEN = re.compile(r"\S+")
_STRIP = re.compile(r"^\W+|\W+$")


def shared_passages(text_a: str, text_b: str, min_words: int = 8, limit: int = 40) -> dict:
    """Passages that appear in both texts (runs of at least `min_words` equal words, ignoring case and punctuation), longest first, with their position in each text."""
    ta, tb = _TOKEN.findall(text_a), _TOKEN.findall(text_b)
    na, nb = [_STRIP.sub("", w).lower() for w in ta], [_STRIP.sub("", w).lower() for w in tb]
    blocks = [m for m in difflib.SequenceMatcher(None, na, nb, autojunk=False).get_matching_blocks() if m.size >= min_words]
    blocks.sort(key=lambda m: -m.size)
    passages = [{"words": m.size, "text": " ".join(ta[m.a:m.a + m.size]), "a_start": m.a, "b_start": m.b,
                 "a_pos": round(m.a / max(1, len(ta)), 3), "b_pos": round(m.b / max(1, len(tb)), 3)} for m in blocks[:limit]]
    covered_a = sum(m.size for m in blocks)
    return {"passages": passages, "count": len(blocks), "words_shared": covered_a,
            "share_of_a": round(covered_a / max(1, len(ta)), 4), "share_of_b": round(covered_a / max(1, len(tb)), 4), "a_words": len(ta), "b_words": len(tb)}
