# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║   ⚡  GADGET PREMIUM HOST  v5.0  ·  keyboards.py                          ║
# ║   All inline keyboards — admin, user, navigation, deploy, economy         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config


def _b(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.row(*[
            InlineKeyboardButton(text=t, callback_data=c) for t, c in row
        ])
    return builder.as_markup()


def _url_btn(text: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, url=url)


# ─── SUBSCRIBE GATE ─────────────────────────────────────────────────────────

def kb_gate(pub_ok: bool, prv_ok: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if not pub_ok:
        b.row(_url_btn(f"📢  Join {config.PUBLIC_CHANNEL_NAME}", config.PUBLIC_CHANNEL_LINK))
    if not prv_ok:
        b.row(_url_btn(f"🔒  Join {config.PRIVATE_CHANNEL_NAME}", config.PRIVATE_CHANNEL_LINK))
    b.row(InlineKeyboardButton(text="🔄  Verify Membership", callback_data="verify_sub"))
    return b.as_markup()


# ─── MAIN MENU ──────────────────────────────────────────────────────────────

def kb_main(uid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🤖  My Bots",       callback_data="my_bots"),
        InlineKeyboardButton(text="🚀  Deploy",         callback_data="deploy_menu"),
    )
    b.row(
        InlineKeyboardButton(text="🪙  Wallet",         callback_data="wallet"),
        InlineKeyboardButton(text="🎁  Daily",          callback_data="daily"),
    )
    b.row(
        InlineKeyboardButton(text="🔗  Referral",       callback_data="referral"),
        InlineKeyboardButton(text="💎  Plans",          callback_data="plans"),
    )
    b.row(
        InlineKeyboardButton(text="📊  Stats",          callback_data="my_stats"),
        InlineKeyboardButton(text="❓  Help",           callback_data="help"),
    )
    if uid == config.OWNER_ID or uid in config.CO_ADMINS:
        b.row(InlineKeyboardButton(
            text="👑  ═══ ADMIN PANEL ═══",
            callback_data="admin_home",
        ))
    return b.as_markup()


def kb_home() -> InlineKeyboardMarkup:
    return _b([("🏠  Main Menu", "home")])


def kb_cancel(back_data: str = "home") -> InlineKeyboardMarkup:
    return _b([("❌  Cancel", f"cancel_{back_data}")])


# ─── MY BOTS ────────────────────────────────────────────────────────────────

def kb_bots(bots: list, page: int = 0, per: int = 6) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    icons = {"running": "🟢", "stopped": "🔴", "error": "🟡"}
    start, end = page * per, page * per + per
    for bot in bots[start:end]:
        icon = icons.get(bot["status"], "⚪")
        b.row(InlineKeyboardButton(
            text=f"{icon}  {bot['bot_name']}  ·  #{bot['bot_id']}",
            callback_data=f"bot_{bot['bot_id']}",
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀  Prev", callback_data=f"bots_p_{page-1}"))
    if end < len(bots):
        nav.append(InlineKeyboardButton(text="Next  ▶", callback_data=f"bots_p_{page+1}"))
    if nav:
        b.row(*nav)
    b.row(
        InlineKeyboardButton(text="🚀  Deploy New", callback_data="deploy_menu"),
        InlineKeyboardButton(text="🏠  Menu",        callback_data="home"),
    )
    return b.as_markup()


# ─── BOT DETAIL ─────────────────────────────────────────────────────────────

def kb_bot(bid: int, status: str, auto_restart: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if status == "running":
        b.row(
            InlineKeyboardButton(text="⏹  Stop",       callback_data=f"bstop_{bid}"),
            InlineKeyboardButton(text="🔄  Restart",    callback_data=f"brestart_{bid}"),
        )
    else:
        b.row(InlineKeyboardButton(text="▶️  Start",    callback_data=f"bstart_{bid}"))

    b.row(
        InlineKeyboardButton(text="📜  Logs",          callback_data=f"blogs_{bid}"),
        InlineKeyboardButton(text="📊  Resources",     callback_data=f"bres_{bid}"),
    )
    b.row(
        InlineKeyboardButton(text="🌍  Env Vars",      callback_data=f"benv_{bid}"),
        InlineKeyboardButton(text="📅  Schedule",      callback_data=f"bsched_{bid}"),
    )
    b.row(
        InlineKeyboardButton(text="📥  Get File",      callback_data=f"bfile_{bid}"),
        InlineKeyboardButton(text="✏️  Rename",        callback_data=f"brename_{bid}"),
    )
    ar_text = "🔁 AutoRestart ✅" if auto_restart else "🔁 AutoRestart ❌"
    b.row(
        InlineKeyboardButton(text=ar_text,              callback_data=f"btogglear_{bid}"),
        InlineKeyboardButton(text="🗑  Delete",        callback_data=f"bdelete_{bid}"),
    )
    b.row(
        InlineKeyboardButton(text="◀  My Bots",       callback_data="my_bots"),
        InlineKeyboardButton(text="🏠  Menu",          callback_data="home"),
    )
    return b.as_markup()


def kb_logs(bid: int) -> InlineKeyboardMarkup:
    return _b(
        [("🔄  Refresh", f"blogs_{bid}"), ("📥  Download", f"bdllog_{bid}")],
        [("◀  Back",      f"bot_{bid}")],
    )


def kb_confirm_delete(bid: int) -> InlineKeyboardMarkup:
    return _b(
        [("✅  Confirm Delete", f"bconfirmdel_{bid}"), ("❌  Cancel", f"bot_{bid}")],
    )


def kb_env(bid: int, envs: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ev in envs:
        b.row(InlineKeyboardButton(
            text=f"🗑  {ev['key']}",
            callback_data=f"bdelenv_{bid}_{ev['key']}",
        ))
    b.row(InlineKeyboardButton(text="➕  Add Variable", callback_data=f"baddenv_{bid}"))
    b.row(InlineKeyboardButton(text="◀  Back",           callback_data=f"bot_{bid}"))
    return b.as_markup()


# ─── DEPLOY ──────────────────────────────────────────────────────────────────

def kb_deploy() -> InlineKeyboardMarkup:
    rows = [
        [("🐍  Upload .py",    "dep_file"), ("📦  Upload .zip",  "dep_zip")],
    ]
    if config.ENABLE_GIT_DEPLOY:
        rows.append([("🔗  Git Clone", "dep_git")])
    rows.append([("◀  Back", "home")])
    return _b(*rows)


# ─── WALLET ──────────────────────────────────────────────────────────────────

def kb_wallet() -> InlineKeyboardMarkup:
    return _b(
        [("🛒  Buy Slot", "buy_slot"), ("📜  History",    "coin_hist")],
        [("🏆  Leaderboard", "coin_lb"), ("🏠  Menu",     "home")],
    )


# ─── PLANS ───────────────────────────────────────────────────────────────────

def kb_plans() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="💬  Contact Owner to Upgrade",
        url=f"https://t.me/{config.OWNER_USERNAME.lstrip('@')}",
    ))
    b.row(InlineKeyboardButton(text="🏠  Menu", callback_data="home"))
    return b.as_markup()


# ─── ADMIN PANEL (ADVANCED) ─────────────────────────────────────────────────

def kb_admin() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🖥️  Server Monitor",  callback_data="adm_server"),
        InlineKeyboardButton(text="📊  Analytics",        callback_data="adm_analytics"),
    )
    b.row(
        InlineKeyboardButton(text="👥  User Manager",     callback_data="adm_users_0"),
        InlineKeyboardButton(text="🤖  Bot Manager",      callback_data="adm_allbots_0"),
    )
    b.row(
        InlineKeyboardButton(text="📢  Broadcast",        callback_data="adm_broadcast"),
        InlineKeyboardButton(text="💰  Economy",          callback_data="adm_economy"),
    )
    b.row(
        InlineKeyboardButton(text="🏆  Leaderboards",     callback_data="adm_leaderboard"),
        InlineKeyboardButton(text="📈  Growth Data",      callback_data="adm_growth"),
    )
    b.row(
        InlineKeyboardButton(text="📋  Admin Log",        callback_data="adm_log"),
        InlineKeyboardButton(text="📡  System Events",    callback_data="adm_events"),
    )
    b.row(
        InlineKeyboardButton(text="💾  Backup DB",        callback_data="adm_backup"),
        InlineKeyboardButton(text="🔍  Search User",      callback_data="adm_search"),
    )
    b.row(
        InlineKeyboardButton(text="🔒  Maint ON",         callback_data="adm_maint_on"),
        InlineKeyboardButton(text="🔓  Maint OFF",        callback_data="adm_maint_off"),
    )
    b.row(InlineKeyboardButton(text="🏠  Main Menu",      callback_data="home"))
    return b.as_markup()


def kb_admin_back() -> InlineKeyboardMarkup:
    return _b([("◀  Admin Panel", "admin_home")])


def kb_user_ctrl(uid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🚫  Ban",              callback_data=f"adm_ban_{uid}"),
        InlineKeyboardButton(text="✅  Unban",            callback_data=f"adm_unban_{uid}"),
    )
    b.row(
        InlineKeyboardButton(text="🆓  Free",             callback_data=f"adm_plan_{uid}_free"),
        InlineKeyboardButton(text="⭐  Starter",          callback_data=f"adm_plan_{uid}_starter"),
    )
    b.row(
        InlineKeyboardButton(text="🔥  Pro",              callback_data=f"adm_plan_{uid}_pro"),
        InlineKeyboardButton(text="💎  Elite",            callback_data=f"adm_plan_{uid}_elite"),
    )
    b.row(
        InlineKeyboardButton(text="👑  Ultimate",         callback_data=f"adm_plan_{uid}_ultimate"),
    )
    b.row(
        InlineKeyboardButton(text="🛑  Kill Bots",        callback_data=f"adm_killbots_{uid}"),
        InlineKeyboardButton(text="🗑  Del Files",        callback_data=f"adm_delfiles_{uid}"),
    )
    b.row(
        InlineKeyboardButton(text="📝  Note",             callback_data=f"adm_note_{uid}"),
        InlineKeyboardButton(text="🪙  Coins",            callback_data=f"adm_coins_{uid}"),
    )
    b.row(
        InlineKeyboardButton(text="🔲  Slots",            callback_data=f"adm_slots_{uid}"),
        InlineKeyboardButton(text="📨  Message",          callback_data=f"adm_msg_{uid}"),
    )
    b.row(
        InlineKeyboardButton(text="◀  User List",        callback_data="adm_users_0"),
        InlineKeyboardButton(text="🏠  Admin",            callback_data="admin_home"),
    )
    return b.as_markup()


def kb_admin_users(users: list, page: int = 0, per: int = 8) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    start, end = page * per, page * per + per
    for u in users[start:end]:
        banned = "🚫" if u["is_banned"] else ""
        plan_e = config.PLANS.get(u["plan"], config.PLANS["free"])["emoji"]
        name = (u["full_name"] or u["username"] or str(u["user_id"]))[:22]
        b.row(InlineKeyboardButton(
            text=f"{plan_e}{banned} {name}  ·  {u['user_id']}",
            callback_data=f"adm_view_{u['user_id']}",
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀  Prev", callback_data=f"adm_users_{page-1}"))
    if end < len(users):
        nav.append(InlineKeyboardButton(text="Next  ▶", callback_data=f"adm_users_{page+1}"))
    if nav:
        b.row(*nav)
    b.row(
        InlineKeyboardButton(text="🔍  Search", callback_data="adm_search"),
        InlineKeyboardButton(text="◀  Admin",   callback_data="admin_home"),
    )
    return b.as_markup()


def kb_admin_bots(bots: list, page: int = 0, per: int = 8) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    icons = {"running": "🟢", "stopped": "🔴", "error": "🟡"}
    start, end = page * per, page * per + per
    for bot in bots[start:end]:
        icon = icons.get(bot["status"], "⚪")
        name = bot["bot_name"][:20]
        b.row(InlineKeyboardButton(
            text=f"{icon}  {name}  ·  #{bot['bot_id']}  👤{bot['owner_id']}",
            callback_data=f"bot_{bot['bot_id']}",
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀  Prev", callback_data=f"adm_allbots_{page-1}"))
    if end < len(bots):
        nav.append(InlineKeyboardButton(text="Next  ▶", callback_data=f"adm_allbots_{page+1}"))
    if nav:
        b.row(*nav)
    b.row(InlineKeyboardButton(text="◀  Admin Panel", callback_data="admin_home"))
    return b.as_markup()


def kb_leaderboard() -> InlineKeyboardMarkup:
    return _b(
        [("🪙  Top Coins", "adm_lb_coins"), ("🔗  Top Referrers", "adm_lb_refs")],
        [("🤖  Top Deployers", "adm_lb_deploy")],
        [("◀  Admin Panel", "admin_home")],
    )
