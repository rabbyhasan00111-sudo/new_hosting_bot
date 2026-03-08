# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║   ⚡  GADGET PREMIUM HOST  v5.0  ·  database.py                           ║
# ║   Full SQLite engine with WAL, referrals, economy, analytics              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

from __future__ import annotations

import sqlite3
import time
import logging
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional

import config

log = logging.getLogger("GPH.db")
_conn: Optional[sqlite3.Connection] = None


# ─── CONNECTION ──────────────────────────────────────────────────────────────

def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("PRAGMA cache_size=-8000")
        _conn.execute("PRAGMA temp_store=MEMORY")
    return _conn


# ─── SCHEMA ──────────────────────────────────────────────────────────────────

def init() -> None:
    conn().executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id          INTEGER PRIMARY KEY,
            username         TEXT    DEFAULT '',
            full_name        TEXT    DEFAULT '',
            lang             TEXT    DEFAULT 'en',
            is_banned        INTEGER DEFAULT 0,
            ban_reason       TEXT    DEFAULT '',
            plan             TEXT    DEFAULT 'free',
            bonus_slots      INTEGER DEFAULT 0,
            coins            INTEGER DEFAULT 0,
            total_earned     INTEGER DEFAULT 0,
            daily_streak     INTEGER DEFAULT 0,
            last_daily       TEXT    DEFAULT NULL,
            weekly_claimed   INTEGER DEFAULT 0,
            monthly_claimed  INTEGER DEFAULT 0,
            admin_note       TEXT    DEFAULT '',
            referrer_id      INTEGER DEFAULT NULL,
            joined_at        TEXT    DEFAULT (datetime('now')),
            last_seen        TEXT    DEFAULT (datetime('now')),
            message_count    INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS bots (
            bot_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id         INTEGER NOT NULL,
            bot_name         TEXT    NOT NULL,
            file_path        TEXT    NOT NULL,
            pid              INTEGER DEFAULT NULL,
            status           TEXT    DEFAULT 'stopped',
            auto_restart     INTEGER DEFAULT 1,
            restart_count    INTEGER DEFAULT 0,
            total_restarts   INTEGER DEFAULT 0,
            crash_count      INTEGER DEFAULT 0,
            total_uptime     INTEGER DEFAULT 0,
            start_ts         REAL    DEFAULT NULL,
            memory_usage     INTEGER DEFAULT 0,
            cpu_usage        REAL    DEFAULT 0.0,
            schedule_start   TEXT    DEFAULT NULL,
            schedule_stop    TEXT    DEFAULT NULL,
            created_at       TEXT    DEFAULT (datetime('now')),
            last_started     TEXT    DEFAULT NULL,
            FOREIGN KEY (owner_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS bot_envvars (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id  INTEGER NOT NULL,
            key     TEXT    NOT NULL,
            value   TEXT    NOT NULL,
            UNIQUE (bot_id, key),
            FOREIGN KEY (bot_id) REFERENCES bots(bot_id)
        );

        CREATE TABLE IF NOT EXISTS referrals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id  INTEGER NOT NULL,
            referee_id   INTEGER NOT NULL UNIQUE,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS coin_tx (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      INTEGER NOT NULL,
            balance     INTEGER DEFAULT 0,
            reason      TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS admin_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id    INTEGER NOT NULL,
            action      TEXT    NOT NULL,
            target_id   INTEGER DEFAULT NULL,
            detail      TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS broadcasts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id    INTEGER NOT NULL,
            preview     TEXT    DEFAULT '',
            sent        INTEGER DEFAULT 0,
            failed      INTEGER DEFAULT 0,
            pinned      INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS system_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            detail      TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_activity (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            action      TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_bots_owner ON bots(owner_id);
        CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status);
        CREATE INDEX IF NOT EXISTS idx_coin_tx_user ON coin_tx(user_id);
        CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
        CREATE INDEX IF NOT EXISTS idx_user_activity ON user_activity(user_id);
        CREATE INDEX IF NOT EXISTS idx_events_type ON system_events(event_type);
    """)
    conn().commit()
    log.info("Database ready ✔")


# ─── USER CRUD ───────────────────────────────────────────────────────────────

def get_user(uid: int) -> Optional[sqlite3.Row]:
    return conn().execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()


def upsert_user(uid: int, username: str, full_name: str,
                referrer_id: Optional[int] = None) -> bool:
    existing = get_user(uid)
    if existing is None:
        conn().execute(
            "INSERT INTO users (user_id,username,full_name,referrer_id) VALUES(?,?,?,?)",
            (uid, username or "", full_name or "", referrer_id),
        )
        if referrer_id and referrer_id != uid:
            _credit_referral(referrer_id, uid)
        conn().commit()
        log_activity(uid, "JOINED")
        return True
    conn().execute(
        "UPDATE users SET username=?,full_name=?,last_seen=datetime('now'),"
        "message_count=message_count+1 WHERE user_id=?",
        (username or "", full_name or "", uid),
    )
    conn().commit()
    return False


def _credit_referral(referrer_id: int, referee_id: int) -> None:
    try:
        conn().execute(
            "INSERT OR IGNORE INTO referrals(referrer_id,referee_id) VALUES(?,?)",
            (referrer_id, referee_id),
        )
        if config.ENABLE_COINS:
            _add_coins(referrer_id, config.REFERRAL_COINS, f"referral:{referee_id}")
    except Exception as e:
        log.warning(f"Referral credit failed: {e}")


def ban_user(uid: int, reason: str = "") -> None:
    conn().execute(
        "UPDATE users SET is_banned=1,ban_reason=? WHERE user_id=?", (reason, uid)
    )
    conn().commit()


def unban_user(uid: int) -> None:
    conn().execute(
        "UPDATE users SET is_banned=0,ban_reason='' WHERE user_id=?", (uid,)
    )
    conn().commit()


def set_plan(uid: int, plan: str) -> None:
    conn().execute("UPDATE users SET plan=? WHERE user_id=?", (plan, uid))
    conn().commit()


def set_note(uid: int, note: str) -> None:
    conn().execute("UPDATE users SET admin_note=? WHERE user_id=?", (note, uid))
    conn().commit()


def add_bonus_slots(uid: int, n: int) -> None:
    conn().execute(
        "UPDATE users SET bonus_slots=bonus_slots+? WHERE user_id=?", (n, uid)
    )
    conn().commit()


def set_bonus_slots(uid: int, n: int) -> None:
    conn().execute("UPDATE users SET bonus_slots=? WHERE user_id=?", (n, uid))
    conn().commit()


def get_slot_counts(uid: int) -> tuple[int, int]:
    row = get_user(uid)
    if not row:
        return 0, config.PLANS["free"]["slots"]
    plan_max = config.PLANS.get(row["plan"], config.PLANS["free"])["slots"]
    total_max = plan_max + (row["bonus_slots"] or 0)
    used = conn().execute(
        "SELECT COUNT(*) FROM bots WHERE owner_id=? AND status!='deleted'", (uid,)
    ).fetchone()[0]
    return used, total_max


def all_users() -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM users ORDER BY joined_at DESC"
    ).fetchall()


def search_users(query: str) -> list[sqlite3.Row]:
    q = f"%{query}%"
    return conn().execute(
        "SELECT * FROM users WHERE username LIKE ? OR full_name LIKE ? "
        "OR CAST(user_id AS TEXT) LIKE ? LIMIT 25",
        (q, q, q),
    ).fetchall()


def user_stats() -> dict:
    c = conn()
    return {
        "total":     c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "banned":    c.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0],
        "premium":   c.execute("SELECT COUNT(*) FROM users WHERE plan!='free'").fetchone()[0],
        "today":     c.execute(
            "SELECT COUNT(*) FROM users WHERE date(joined_at)=date('now')"
        ).fetchone()[0],
        "active_24h": c.execute(
            "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now','-1 day')"
        ).fetchone()[0],
        "active_7d": c.execute(
            "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now','-7 days')"
        ).fetchone()[0],
        "active_30d": c.execute(
            "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now','-30 days')"
        ).fetchone()[0],
    }


def user_count() -> int:
    return conn().execute("SELECT COUNT(*) FROM users").fetchone()[0]


def all_user_ids() -> list[int]:
    rows = conn().execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    return [r[0] for r in rows]


def referral_count(uid: int) -> int:
    return conn().execute(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,)
    ).fetchone()[0]


def top_referrers(limit: int = 10) -> list[sqlite3.Row]:
    return conn().execute(
        """SELECT u.user_id,u.full_name,u.username,COUNT(r.id) rc
           FROM referrals r JOIN users u ON u.user_id=r.referrer_id
           GROUP BY r.referrer_id ORDER BY rc DESC LIMIT ?""",
        (limit,),
    ).fetchall()


def top_coins(limit: int = 10) -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT user_id,full_name,username,coins FROM users ORDER BY coins DESC LIMIT ?",
        (limit,),
    ).fetchall()


# ─── DAILY / WEEKLY / MONTHLY ───────────────────────────────────────────────

def claim_daily(uid: int) -> tuple[bool, int, int, str]:
    row = get_user(uid)
    if not row:
        return False, 0, 0, ""
    today = date.today().isoformat()
    last  = row["last_daily"]
    streak = row["daily_streak"] or 0

    if last == today:
        return False, 0, streak, ""

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    streak = (streak + 1) if last == yesterday else 1

    streak_bonus = min((streak - 1) * config.DAILY_STREAK_BONUS, config.MAX_STREAK_BONUS)
    earned = config.DAILY_BASE_COINS + streak_bonus
    bonus_msg = ""

    if streak == 7 and not row["weekly_claimed"]:
        earned += config.WEEKLY_BONUS_COINS
        bonus_msg = f"🎉 7-Day Streak Bonus! +{config.WEEKLY_BONUS_COINS} coins!"
        conn().execute("UPDATE users SET weekly_claimed=1 WHERE user_id=?", (uid,))
    elif streak == 30 and not row["monthly_claimed"]:
        earned += config.MONTHLY_BONUS_COINS
        bonus_msg = f"🏆 30-Day Legend Bonus! +{config.MONTHLY_BONUS_COINS} coins!"
        conn().execute("UPDATE users SET monthly_claimed=1 WHERE user_id=?", (uid,))

    _add_coins(uid, earned, f"daily streak={streak}")
    conn().execute(
        "UPDATE users SET daily_streak=?,last_daily=? WHERE user_id=?",
        (streak, today, uid),
    )
    conn().commit()
    log_activity(uid, "DAILY_CLAIM")
    return True, earned, streak, bonus_msg


# ─── COINS ───────────────────────────────────────────────────────────────────

def _add_coins(uid: int, amount: int, reason: str = "") -> None:
    conn().execute(
        "UPDATE users SET coins=coins+?,total_earned=total_earned+? WHERE user_id=?",
        (amount, max(amount, 0), uid),
    )
    row = get_user(uid)
    bal = row["coins"] if row else 0
    conn().execute(
        "INSERT INTO coin_tx(user_id,amount,balance,reason) VALUES(?,?,?,?)",
        (uid, amount, bal, reason),
    )


def add_coins(uid: int, amount: int, reason: str = "") -> None:
    _add_coins(uid, amount, reason)
    conn().commit()


def spend_coins(uid: int, amount: int, reason: str = "") -> bool:
    row = get_user(uid)
    if not row or (row["coins"] or 0) < amount:
        return False
    _add_coins(uid, -amount, reason)
    conn().commit()
    return True


def coin_history(uid: int, limit: int = 15) -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM coin_tx WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (uid, limit),
    ).fetchall()


def economy_stats() -> dict:
    c = conn()
    return {
        "total_coins":    c.execute("SELECT COALESCE(SUM(coins),0) FROM users").fetchone()[0],
        "total_earned":   c.execute("SELECT COALESCE(SUM(total_earned),0) FROM users").fetchone()[0],
        "tx_count":       c.execute("SELECT COUNT(*) FROM coin_tx").fetchone()[0],
        "slots_bought":   c.execute(
            "SELECT COUNT(*) FROM coin_tx WHERE reason LIKE '%slot%'"
        ).fetchone()[0],
    }


# ─── BOT CRUD ────────────────────────────────────────────────────────────────

def get_bot(bid: int) -> Optional[sqlite3.Row]:
    return conn().execute("SELECT * FROM bots WHERE bot_id=?", (bid,)).fetchone()


def get_user_bots(uid: int) -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM bots WHERE owner_id=? AND status!='deleted' ORDER BY bot_id DESC",
        (uid,),
    ).fetchall()


def get_all_active_bots() -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM bots WHERE status!='deleted' ORDER BY bot_id DESC"
    ).fetchall()


def get_running_bots() -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM bots WHERE status='running' ORDER BY bot_id DESC"
    ).fetchall()


def create_bot(uid: int, name: str, file_path: str) -> int:
    c = conn()
    c.execute(
        "INSERT INTO bots(owner_id,bot_name,file_path) VALUES(?,?,?)",
        (uid, name, file_path),
    )
    c.commit()
    bid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    log_activity(uid, f"DEPLOY:{bid}")
    log_event("BOT_DEPLOY", f"uid={uid} bid={bid} name={name}")
    return bid


def update_bot_status(bid: int, status: str, pid: int = None) -> None:
    c = conn()
    now_ts = time.time()
    if status == "running":
        c.execute(
            "UPDATE bots SET status=?,pid=?,start_ts=?,last_started=datetime('now') WHERE bot_id=?",
            (status, pid, now_ts, bid),
        )
    elif status in ("stopped", "error", "deleted"):
        row = get_bot(bid)
        uptime_add = 0
        if row and row["start_ts"]:
            uptime_add = max(0, int(now_ts - row["start_ts"]))
        c.execute(
            "UPDATE bots SET status=?,pid=NULL,start_ts=NULL,total_uptime=total_uptime+? WHERE bot_id=?",
            (status, uptime_add, bid),
        )
    else:
        c.execute("UPDATE bots SET status=?,pid=? WHERE bot_id=?", (status, pid, bid))
    c.commit()


def update_bot_resources(bid: int, cpu: float, mem_bytes: int) -> None:
    conn().execute(
        "UPDATE bots SET cpu_usage=?,memory_usage=? WHERE bot_id=?",
        (cpu, mem_bytes, bid),
    )
    conn().commit()


def rename_bot(bid: int, name: str) -> None:
    conn().execute("UPDATE bots SET bot_name=? WHERE bot_id=?", (name, bid))
    conn().commit()


def toggle_auto_restart(bid: int) -> bool:
    row = get_bot(bid)
    if not row:
        return False
    new = 0 if row["auto_restart"] else 1
    conn().execute("UPDATE bots SET auto_restart=? WHERE bot_id=?", (new, bid))
    conn().commit()
    return bool(new)


def inc_restart_count(bid: int) -> int:
    conn().execute(
        "UPDATE bots SET restart_count=restart_count+1,total_restarts=total_restarts+1 WHERE bot_id=?",
        (bid,),
    )
    conn().commit()
    row = get_bot(bid)
    return row["restart_count"] if row else 0


def inc_crash_count(bid: int) -> None:
    conn().execute("UPDATE bots SET crash_count=crash_count+1 WHERE bot_id=?", (bid,))
    conn().commit()


def reset_restart_count(bid: int) -> None:
    conn().execute("UPDATE bots SET restart_count=0 WHERE bot_id=?", (bid,))
    conn().commit()


def set_bot_schedule(bid: int, start_time: Optional[str], stop_time: Optional[str]) -> None:
    conn().execute(
        "UPDATE bots SET schedule_start=?,schedule_stop=? WHERE bot_id=?",
        (start_time, stop_time, bid),
    )
    conn().commit()


def soft_delete_bot(bid: int) -> None:
    conn().execute("UPDATE bots SET status='deleted',pid=NULL WHERE bot_id=?", (bid,))
    conn().execute("DELETE FROM bot_envvars WHERE bot_id=?", (bid,))
    conn().commit()


def bot_stats() -> dict:
    c = conn()
    return {
        "total":   c.execute("SELECT COUNT(*) FROM bots WHERE status!='deleted'").fetchone()[0],
        "running": c.execute("SELECT COUNT(*) FROM bots WHERE status='running'").fetchone()[0],
        "stopped": c.execute("SELECT COUNT(*) FROM bots WHERE status='stopped'").fetchone()[0],
        "error":   c.execute("SELECT COUNT(*) FROM bots WHERE status='error'").fetchone()[0],
    }


# ─── ENV VARS ────────────────────────────────────────────────────────────────

def set_env(bid: int, key: str, value: str) -> None:
    conn().execute(
        "INSERT INTO bot_envvars(bot_id,key,value) VALUES(?,?,?) "
        "ON CONFLICT(bot_id,key) DO UPDATE SET value=excluded.value",
        (bid, key, value),
    )
    conn().commit()


def get_envs(bid: int) -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM bot_envvars WHERE bot_id=? ORDER BY key", (bid,)
    ).fetchall()


def del_env(bid: int, key: str) -> None:
    conn().execute("DELETE FROM bot_envvars WHERE bot_id=? AND key=?", (bid, key))
    conn().commit()


def env_dict(bid: int) -> dict:
    return {r["key"]: r["value"] for r in get_envs(bid)}


# ─── ADMIN LOG & SYSTEM EVENTS ──────────────────────────────────────────────

def log_action(admin_id: int, action: str,
               target: Optional[int] = None, detail: str = "") -> None:
    conn().execute(
        "INSERT INTO admin_log(admin_id,action,target_id,detail) VALUES(?,?,?,?)",
        (admin_id, action, target, detail),
    )
    conn().commit()


def get_log(limit: int = 25) -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM admin_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()


def log_event(event_type: str, detail: str = "") -> None:
    conn().execute(
        "INSERT INTO system_events(event_type,detail) VALUES(?,?)",
        (event_type, detail),
    )
    conn().commit()


def recent_events(limit: int = 20) -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM system_events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()


def log_broadcast(admin_id: int, preview: str, sent: int, failed: int, pinned: bool) -> None:
    conn().execute(
        "INSERT INTO broadcasts(admin_id,preview,sent,failed,pinned) VALUES(?,?,?,?,?)",
        (admin_id, preview, sent, failed, int(pinned)),
    )
    conn().commit()


def broadcast_stats() -> dict:
    c = conn()
    total = c.execute("SELECT COUNT(*) FROM broadcasts").fetchone()[0]
    sent  = c.execute("SELECT COALESCE(SUM(sent),0) FROM broadcasts").fetchone()[0]
    return {"total": total, "sent": sent}


# ─── ACTIVITY ────────────────────────────────────────────────────────────────

def log_activity(uid: int, action: str) -> None:
    try:
        conn().execute(
            "INSERT INTO user_activity(user_id,action) VALUES(?,?)", (uid, action)
        )
        conn().commit()
    except Exception:
        pass


def recent_activity(uid: int, limit: int = 10) -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM user_activity WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (uid, limit),
    ).fetchall()


# ─── ANALYTICS HELPERS ───────────────────────────────────────────────────────

def growth_data(days: int = 7) -> list[dict]:
    c = conn()
    rows = c.execute(
        "SELECT date(joined_at) as d, COUNT(*) as cnt "
        "FROM users WHERE joined_at >= datetime('now', ? || ' days') "
        "GROUP BY d ORDER BY d",
        (f"-{days}",),
    ).fetchall()
    return [{"date": r["d"], "count": r["cnt"]} for r in rows]


def plan_distribution() -> dict:
    c = conn()
    rows = c.execute(
        "SELECT plan, COUNT(*) as cnt FROM users GROUP BY plan ORDER BY cnt DESC"
    ).fetchall()
    return {r["plan"]: r["cnt"] for r in rows}


def top_deployers(limit: int = 5) -> list[dict]:
    c = conn()
    rows = c.execute(
        "SELECT owner_id, COUNT(*) as cnt FROM bots WHERE status!='deleted' "
        "GROUP BY owner_id ORDER BY cnt DESC LIMIT ?",
        (limit,),
    ).fetchall()
    result = []
    for r in rows:
        u = get_user(r["owner_id"])
        name = u["full_name"] if u else str(r["owner_id"])
        result.append({"uid": r["owner_id"], "name": name, "count": r["cnt"]})
    return result
