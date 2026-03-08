# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║   ⚡  GADGET PREMIUM HOST  v5.0  ·  utils.py                              ║
# ║   Helpers: formatting, bars, syntax guard, rate limiter, dashboards       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

from __future__ import annotations

import ast
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import config


# ─── TEXT FORMATTING ─────────────────────────────────────────────────────────

def bar(cur, total, length: int = 12, fill: str = "█", empty: str = "░") -> str:
    if total <= 0:
        total = 1
    pct = min(cur / total, 1.0)
    done = int(length * pct)
    return fill * done + empty * (length - done)


def pbar(cur, total, length: int = 10) -> str:
    return f"[{bar(cur, total, length)}]"


def sparkbar(cur, total, length: int = 8) -> str:
    """Fancy spark-style bar using Unicode blocks."""
    if total <= 0:
        total = 1
    pct = min(cur / total, 1.0)
    blocks = "░▏▎▍▌▋▊▉█"
    full = int(length * pct)
    frac = (length * pct) - full
    idx = int(frac * (len(blocks) - 1))
    return "█" * full + (blocks[idx] if full < length else "") + "░" * max(0, length - full - 1)


def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def fmt_uptime(secs: float) -> str:
    secs = int(secs)
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def fmt_ts(ts: Optional[str], fmt: str = "%Y-%m-%d %H:%M") -> str:
    if not ts:
        return "Never"
    try:
        return datetime.fromisoformat(ts).strftime(fmt)
    except Exception:
        return str(ts)[:16]


def fmt_number(n: int) -> str:
    """Pretty format numbers: 1234 -> 1,234"""
    return f"{n:,}"


def plan_label(plan: str) -> str:
    return config.PLANS.get(plan, config.PLANS["free"])["label"]


def plan_emoji(plan: str) -> str:
    return config.PLANS.get(plan, config.PLANS["free"])["emoji"]


def plan_slots(plan: str) -> int:
    return config.PLANS.get(plan, config.PLANS["free"])["slots"]


def status_icon(status: str) -> str:
    return {"running": "🟢", "stopped": "🔴", "error": "🟡", "deleted": "⬛"}.get(status, "⚪")


def status_label(status: str) -> str:
    return {
        "running": "🟢 Running",
        "stopped": "🔴 Stopped",
        "error":   "🟡 Error",
        "deleted": "⬛ Deleted",
    }.get(status, "⚪ Unknown")


# ─── VISUAL ELEMENTS ────────────────────────────────────────────────────────

def box(title: str, width: int = 36) -> str:
    inner = width - 4
    t = title[:inner]
    pad = inner - len(t)
    left = pad // 2
    right = pad - left
    return (
        f"╔{'═' * (width - 2)}╗\n"
        f"║{' ' * left}  {t}  {' ' * right}║\n"
        f"╚{'═' * (width - 2)}╝"
    )


def divider(width: int = 34) -> str:
    return "━" * width


def thin_divider(width: int = 34) -> str:
    return "─" * width


def double_divider(width: int = 34) -> str:
    return "═" * width


def section(title: str, emoji: str = "📋") -> str:
    return f"\n{emoji} <b>{title}</b>\n{thin_divider(30)}"


# ─── SYNTAX GUARD ───────────────────────────────────────────────────────────

def syntax_check(source: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(source)
        warnings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in ("system", "popen", "exec"):
                    warnings.append(f"⚠️ Possible dangerous call: <code>{func.attr}</code>")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("ctypes", "subprocess"):
                        warnings.append(f"⚠️ Sensitive import: <code>{alias.name}</code>")
        warn_block = ("\n\n" + "\n".join(warnings)) if warnings else ""
        return True, warn_block
    except SyntaxError as e:
        snippet = (e.text or "").rstrip()
        pointer = " " * max(0, (e.offset or 1) - 1) + "^"
        return False, (
            "🛡️ <b>Syntax Guard: REJECTED</b>\n\n"
            f"🔍 <b>Line {e.lineno}:</b> <code>{e.msg}</code>\n"
            f"<pre>{snippet}\n{pointer}</pre>\n"
            "<i>Fix the error and re-upload.</i>"
        )
    except Exception as e:
        return False, f"⚠️ <b>Parse Error:</b> <code>{e}</code>"


# ─── MAINTENANCE ─────────────────────────────────────────────────────────────

def is_maintenance() -> bool:
    return Path(config.MAINTENANCE_FILE).exists()


def set_maintenance(on: bool) -> None:
    p = Path(config.MAINTENANCE_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    if on:
        p.write_text(datetime.now().isoformat())
    else:
        p.unlink(missing_ok=True)


def maintenance_since() -> Optional[str]:
    p = Path(config.MAINTENANCE_FILE)
    if not p.exists():
        return None
    try:
        return p.read_text().strip()
    except Exception:
        return "unknown"


# ─── ADMIN CHECK ─────────────────────────────────────────────────────────────

def is_owner(uid: int) -> bool:
    return uid == config.OWNER_ID


def is_admin(uid: int) -> bool:
    return uid == config.OWNER_ID or uid in config.CO_ADMINS


# ─── SAFE FILENAME ──────────────────────────────────────────────────────────

def safe_name(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name)


# ─── RATE LIMITER ────────────────────────────────────────────────────────────

_cooldowns: dict[int, float] = {}


def is_rate_limited(uid: int, cooldown: float = config.USER_CMD_COOLDOWN) -> bool:
    now = time.time()
    last = _cooldowns.get(uid, 0)
    if now - last < cooldown:
        return True
    _cooldowns[uid] = now
    return False


# ─── DASHBOARD BUILDER ──────────────────────────────────────────────────────

def build_dashboard(uid: int, full_name: str) -> str:
    import database as db
    row      = db.get_user(uid)
    used, mx = db.get_slot_counts(uid)
    refs     = db.referral_count(uid)
    plan     = row["plan"] if row else "free"
    coins    = row["coins"] if row else 0
    streak   = row["daily_streak"] if row else 0
    bots_row = db.get_user_bots(uid)
    running  = sum(1 for b in bots_row if b["status"] == "running")
    slot_bar = sparkbar(used, mx)
    streak_bar = sparkbar(streak % 7, 7, 6)

    return (
        "╔══════════════════════════════════╗\n"
        f"║   ⚡  <b>{config.BOT_NAME}</b>\n"
        f"║       v{config.BOT_VERSION}  ·  Premium Hosting\n"
        "╚══════════════════════════════════╝\n"
        "\n"
        f"👋  Welcome back, <b>{full_name}</b>!\n"
        "\n"
        f"{divider()}\n"
        f"📋  Plan:        {plan_label(plan)}\n"
        f"🤖  Slots:       {slot_bar} <code>{used}/{mx}</code>\n"
        f"🟢  Running:     <code>{running}</code> bot(s)\n"
        f"🪙  Coins:       <code>{fmt_number(coins)}</code>\n"
        f"🔥  Streak:      {streak_bar} <code>{streak}d</code>\n"
        f"🔗  Referrals:   <code>{refs}</code>\n"
        f"{divider()}\n"
        f"<i>Deploy · Manage · Earn  🚀</i>\n"
        f"<i>⏰ {datetime.now().strftime('%H:%M · %d %b %Y')}</i>"
    )
