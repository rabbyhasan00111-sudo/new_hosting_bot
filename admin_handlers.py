# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║   ⚡  GADGET PREMIUM HOST  v5.0  ·  admin_handlers.py                     ║
# ║   Advanced admin panel: server, analytics, users, broadcast, exec, more   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

from __future__ import annotations

import asyncio
import functools
import shutil
import time
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, FSInputFile, InlineKeyboardButton, Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database as db
import keyboards as kb
import process_manager as pm
import utils

router = Router()


# ─── STATES ──────────────────────────────────────────────────────────────────

class AdminState(StatesGroup):
    note        = State()
    give_coins  = State()
    give_slots  = State()
    send_msg    = State()
    exec_cmd    = State()
    broadcast   = State()
    search      = State()


# ─── HELPERS ─────────────────────────────────────────────────────────────────

async def _edit(cq: CallbackQuery, text: str, markup=None) -> None:
    try:
        await cq.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        try:
            await cq.message.answer(text, reply_markup=markup)
        except Exception:
            pass


def _require_admin(func):
    @functools.wraps(func)
    async def _wrap(cq: CallbackQuery, **kwargs):
        if not utils.is_admin(cq.from_user.id):
            await cq.answer("🚫  Admin only!", show_alert=True)
            return
        return await func(cq, **kwargs)
    return _wrap


def _require_owner(func):
    @functools.wraps(func)
    async def _wrap(msg: Message, **kwargs):
        if not utils.is_owner(msg.from_user.id):
            await msg.reply("🚫  <b>Owner only.</b>")
            return
        return await func(msg, **kwargs)
    return _wrap


# ─── ADMIN HOME ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_home")
async def cb_admin_home(cq: CallbackQuery):
    if not utils.is_admin(cq.from_user.id):
        await cq.answer("🚫  Admin only!", show_alert=True)
        return
    await cq.answer()
    await _edit(cq, _admin_home_text(), kb.kb_admin())


def _admin_home_text() -> str:
    us = db.user_stats()
    bs = db.bot_stats()
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    maint = "🔒 ON" if utils.is_maintenance() else "🔓 OFF"

    cpu_bar = utils.sparkbar(cpu, 100, 8)
    ram_bar = utils.sparkbar(ram, 100, 8)
    dsk_bar = utils.sparkbar(disk, 100, 8)

    return (
        "╔══════════════════════════════════════╗\n"
        "║   👑  G O D   M O D E   ·  v5.0     ║\n"
        "║   ⚡  ADVANCED  ADMIN  PANEL         ║\n"
        "╚══════════════════════════════════════╝\n"
        "\n"
        f"🤖  <b>{config.BOT_NAME}</b>  v{config.BOT_VERSION}\n"
        f"🔧  Maintenance: {maint}\n"
        "\n"
        f"{utils.divider()}\n"
        f"👥  Users:     <code>{us['total']}</code>  "
        f"(+{us['today']} today · {us['active_7d']} active)\n"
        f"💎  Premium:   <code>{us['premium']}</code>\n"
        f"🚫  Banned:    <code>{us['banned']}</code>\n"
        f"{utils.thin_divider()}\n"
        f"🤖  Bots:      <code>{bs['total']}</code> total\n"
        f"🟢  Running:   <code>{bs['running']}</code>  "
        f"🔴 Stopped: <code>{bs['stopped']}</code>  "
        f"🟡 Error: <code>{bs['error']}</code>\n"
        f"{utils.thin_divider()}\n"
        f"⚡  CPU:  {cpu_bar} <code>{cpu:.1f}%</code>\n"
        f"💾  RAM:  {ram_bar} <code>{ram:.1f}%</code>\n"
        f"💿  Disk: {dsk_bar} <code>{disk:.1f}%</code>\n"
        f"{utils.divider()}\n"
        f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    )


# ─── SERVER MONITOR ─────────────────────────────────────────────────────────

@router.message(Command("server"))
async def cmd_server(msg: Message):
    if not utils.is_admin(msg.from_user.id):
        return
    await msg.reply(_server_text(), reply_markup=_server_kb())


@router.callback_query(F.data == "adm_server")
@_require_admin
async def cb_server(cq: CallbackQuery):
    await cq.answer("Refreshing…")
    await _edit(cq, _server_text(), _server_kb())


def _server_text() -> str:
    cpu  = psutil.cpu_percent(interval=0.5)
    mem  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net  = psutil.net_io_counters()
    up   = time.time() - psutil.boot_time()
    load = psutil.getloadavg()

    temps: dict = {}
    with suppress(Exception):
        temps = psutil.sensors_temperatures() or {}
    temp_line = ""
    for chip_temps in temps.values():
        for t in chip_temps:
            if t.current:
                temp_line = f"🌡️  Temp:       <code>{t.current:.1f}°C</code>\n"
                break
        if temp_line:
            break

    cpu_bar  = utils.sparkbar(cpu, 100, 12)
    mem_bar  = utils.sparkbar(mem.percent, 100, 12)
    dsk_bar  = utils.sparkbar(disk.percent, 100, 12)

    pids  = len(psutil.pids())
    cores = psutil.cpu_count(logical=False) or "?"
    lcores= psutil.cpu_count() or "?"

    # Running bots
    running_bots = pm.running_count()

    return (
        "╔════════════════════════════════════╗\n"
        "║   🖥️   LIVE  SERVER  MONITOR       ║\n"
        "╚════════════════════════════════════╝\n"
        "\n"
        f"⚡  <b>CPU</b>\n"
        f"    {cpu_bar} <code>{cpu:.1f}%</code>\n"
        f"    Cores: <code>{cores}p / {lcores}l</code>  "
        f"Load: <code>{load[0]:.2f} {load[1]:.2f} {load[2]:.2f}</code>\n"
        "\n"
        f"💾  <b>RAM</b>\n"
        f"    {mem_bar} <code>{utils.fmt_bytes(mem.used)}/{utils.fmt_bytes(mem.total)}</code>\n"
        f"    Available: <code>{utils.fmt_bytes(mem.available)}</code>\n"
        "\n"
        f"💿  <b>DISK</b>\n"
        f"    {dsk_bar} <code>{disk.percent:.1f}%</code>\n"
        f"    Free: <code>{utils.fmt_bytes(disk.free)}</code>\n"
        "\n"
        f"{utils.divider()}\n"
        f"⏱   Uptime:      <code>{utils.fmt_uptime(up)}</code>\n"
        f"🔢  Processes:   <code>{pids}</code>\n"
        f"🤖  Bot Procs:   <code>{running_bots}</code>\n"
        f"📤  Net ↑:       <code>{utils.fmt_bytes(net.bytes_sent)}</code>\n"
        f"📥  Net ↓:       <code>{utils.fmt_bytes(net.bytes_recv)}</code>\n"
        + temp_line
        + f"{utils.divider()}\n"
        f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    )


def _server_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔄  Refresh",    callback_data="adm_server"))
    b.row(InlineKeyboardButton(text="◀  Admin Panel", callback_data="admin_home"))
    return b.as_markup()


# ─── ANALYTICS ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_analytics")
@_require_admin
async def cb_analytics(cq: CallbackQuery):
    await cq.answer()
    us  = db.user_stats()
    bs  = db.bot_stats()
    eco = db.economy_stats()
    bcs = db.broadcast_stats()
    ref_count = db.conn().execute("SELECT COUNT(*) FROM referrals").fetchone()[0]

    plans = db.plan_distribution()
    plan_lines = []
    for p, cnt in plans.items():
        emoji = config.PLANS.get(p, {}).get("emoji", "•")
        plan_lines.append(f"    {emoji} {p}: <code>{cnt}</code>")

    text = (
        "╔════════════════════════════════════╗\n"
        "║   📊  ANALYTICS  DASHBOARD         ║\n"
        "╚════════════════════════════════════╝\n"
        "\n"
        f"{utils.section('User Metrics', '👥')}\n"
        f"   Total:       <code>{us['total']}</code>\n"
        f"   New Today:   <code>{us['today']}</code>\n"
        f"   Active 24h:  <code>{us['active_24h']}</code>\n"
        f"   Active 7d:   <code>{us['active_7d']}</code>\n"
        f"   Active 30d:  <code>{us['active_30d']}</code>\n"
        f"   Premium:     <code>{us['premium']}</code>\n"
        f"   Banned:      <code>{us['banned']}</code>\n"
        "\n"
        f"{utils.section('Plan Distribution', '💎')}\n"
        + "\n".join(plan_lines) + "\n"
        "\n"
        f"{utils.section('Bot Metrics', '🤖')}\n"
        f"   Total:       <code>{bs['total']}</code>\n"
        f"   Running:     <code>{bs['running']}</code>\n"
        f"   Stopped:     <code>{bs['stopped']}</code>\n"
        f"   Error:       <code>{bs['error']}</code>\n"
        "\n"
        f"{utils.section('Economy', '🪙')}\n"
        f"   In Circ:     <code>{utils.fmt_number(eco['total_coins'])}</code>\n"
        f"   Distributed: <code>{utils.fmt_number(eco['total_earned'])}</code>\n"
        f"   Transactions:<code>{utils.fmt_number(eco['tx_count'])}</code>\n"
        f"   Slots Sold:  <code>{eco['slots_bought']}</code>\n"
        "\n"
        f"{utils.section('Referrals & Broadcasts', '📢')}\n"
        f"   Referrals:   <code>{ref_count}</code>\n"
        f"   Broadcasts:  <code>{bcs['total']}</code>  ({utils.fmt_number(bcs['sent'])} msgs)\n"
        "\n"
        f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>"
    )
    await _edit(cq, text, kb.kb_admin_back())


# ─── GROWTH DATA ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_growth")
@_require_admin
async def cb_growth(cq: CallbackQuery):
    await cq.answer()
    data = db.growth_data(14)
    if not data:
        await _edit(cq, "📈 <b>No growth data yet.</b>", kb.kb_admin_back())
        return
    lines = ["📈 <b>User Growth  (14 days)</b>\n", f"{utils.divider()}\n"]
    max_cnt = max(d["count"] for d in data) or 1
    for d in data:
        bar = utils.bar(d["count"], max_cnt, 12, "▓", "░")
        lines.append(f"<code>{d['date'][5:]}</code>  {bar}  +{d['count']}")
    total = sum(d["count"] for d in data)
    avg = total / len(data) if data else 0
    lines.append(f"\n📊 Total: <code>{total}</code>  Avg: <code>{avg:.1f}/day</code>")
    await _edit(cq, "\n".join(lines), kb.kb_admin_back())


# ─── LEADERBOARDS ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_leaderboard")
@_require_admin
async def cb_leaderboard(cq: CallbackQuery):
    await cq.answer()
    await _edit(cq, "🏆 <b>Leaderboards</b>\n\nChoose a category:", kb.kb_leaderboard())


@router.callback_query(F.data == "adm_lb_coins")
@_require_admin
async def cb_lb_coins(cq: CallbackQuery):
    await cq.answer()
    tops = db.top_coins(10)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = ["🪙 <b>Top Coin Holders</b>\n"]
    for i, r in enumerate(tops):
        name = (r["full_name"] or r["username"] or str(r["user_id"]))[:20]
        lines.append(f"{medals[i]}  {name} — <code>{r['coins']:,}</code>")
    await _edit(cq, "\n".join(lines), kb.kb_admin_back())


@router.callback_query(F.data == "adm_lb_refs")
@_require_admin
async def cb_lb_refs(cq: CallbackQuery):
    await cq.answer()
    tops = db.top_referrers(10)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = ["🔗 <b>Top Referrers</b>\n"]
    for i, r in enumerate(tops):
        name = (r["full_name"] or r["username"] or str(r["user_id"]))[:20]
        lines.append(f"{medals[i]}  {name} — <code>{r['rc']}</code> refs")
    if not tops:
        lines.append("<i>No referrals yet.</i>")
    await _edit(cq, "\n".join(lines), kb.kb_admin_back())


@router.callback_query(F.data == "adm_lb_deploy")
@_require_admin
async def cb_lb_deploy(cq: CallbackQuery):
    await cq.answer()
    tops = db.top_deployers(10)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = ["🤖 <b>Top Deployers</b>\n"]
    for i, d in enumerate(tops):
        lines.append(f"{medals[i]}  {d['name'][:20]} — <code>{d['count']}</code> bots")
    if not tops:
        lines.append("<i>No deployments yet.</i>")
    await _edit(cq, "\n".join(lines), kb.kb_admin_back())


# ─── USER LIST & SEARCH ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_users_"))
@_require_admin
async def cb_user_list(cq: CallbackQuery):
    await cq.answer()
    page  = int(cq.data.split("_")[-1])
    users = db.all_users()
    text  = f"👥 <b>All Users  ({len(users)})</b>"
    await _edit(cq, text, kb.kb_admin_users(users, page))


@router.callback_query(F.data == "adm_search")
@_require_admin
async def cb_search_prompt(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(AdminState.search)
    await cq.message.answer(
        "🔍 <b>Search User</b>\n\nSend user ID, username, or name:",
        reply_markup=kb.kb_cancel("admin_home"),
    )


@router.message(AdminState.search, F.text)
async def handle_search(msg: Message, state: FSMContext):
    query = msg.text.strip()
    await state.clear()
    results = db.search_users(query)
    if not results:
        await msg.reply("❌  No users found.")
        return
    lines = [f"🔍 <b>Results ({len(results)})</b>\n"]
    for r in results:
        plan_e = config.PLANS.get(r["plan"], config.PLANS["free"])["emoji"]
        lines.append(
            f"{plan_e}  <code>{r['user_id']}</code>  "
            f"{r['full_name'] or '?'}  @{r['username'] or 'N/A'}"
        )
    b = InlineKeyboardBuilder()
    if len(results) == 1:
        b.row(InlineKeyboardButton(
            text="👁  View Profile",
            callback_data=f"adm_view_{results[0]['user_id']}",
        ))
    b.row(InlineKeyboardButton(text="◀  Admin", callback_data="admin_home"))
    await msg.reply("\n".join(lines), reply_markup=b.as_markup())


# ─── USER PROFILE ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_view_"))
@_require_admin
async def cb_view_user(cq: CallbackQuery):
    await cq.answer()
    uid = int(cq.data.split("_")[-1])
    await _show_profile(cq, uid)


async def _show_profile(target, uid: int) -> None:
    row = db.get_user(uid)
    if not row:
        txt = f"❌ User <code>{uid}</code> not found."
        if isinstance(target, CallbackQuery):
            await _edit(target, txt, kb.kb_admin_back())
        else:
            await target.reply(txt)
        return

    bots = db.get_user_bots(uid)
    running = [b for b in bots if b["status"] == "running"]
    pids = ", ".join(str(b["pid"]) for b in running if b["pid"]) or "—"
    used, mx = db.get_slot_counts(uid)
    refs = db.referral_count(uid)
    tot_up = sum(b["total_uptime"] or 0 for b in bots)

    text = (
        "╔══════════════════════════════════╗\n"
        f"║  👤  USER PROFILE                ║\n"
        "╚══════════════════════════════════╝\n"
        "\n"
        f"👤  <b>{row['full_name']}</b>  @{row['username'] or 'N/A'}\n"
        f"🆔  <code>{row['user_id']}</code>\n"
        "\n"
        f"{utils.divider()}\n"
        f"📋  Plan:          {utils.plan_label(row['plan'])}\n"
        f"🚫  Banned:        {'⚠️ Yes' if row['is_banned'] else '✅ No'}\n"
        + (f"📋  Ban Reason:    <i>{row['ban_reason']}</i>\n" if row['is_banned'] else "")
        + f"🪙  Coins:         <code>{row['coins']:,}</code>\n"
        f"💰  Total Earned:  <code>{row['total_earned']:,}</code>\n"
        f"🔲  Slots:         <code>{used}/{mx}</code>  (+{row['bonus_slots']} bonus)\n"
        f"🔗  Referrals:     <code>{refs}</code>\n"
        f"🔥  Streak:        <code>{row['daily_streak']} days</code>\n"
        f"💬  Messages:      <code>{row['message_count']}</code>\n"
        f"{utils.thin_divider()}\n"
        f"🤖  Bots:          <code>{len(bots)}</code>  "
        f"(🟢 {len(running)} running)\n"
        f"⏱   Total Uptime:  <code>{utils.fmt_uptime(tot_up)}</code>\n"
        f"🔢  PIDs:          <code>{pids}</code>\n"
        f"{utils.thin_divider()}\n"
        + (f"📝  Note: <i>{row['admin_note']}</i>\n" if row['admin_note'] else "")
        + f"📅  Joined:   <code>{utils.fmt_ts(row['joined_at'])}</code>\n"
        f"👁   Last Seen: <code>{utils.fmt_ts(row['last_seen'])}</code>"
    )
    markup = kb.kb_user_ctrl(uid)
    if isinstance(target, CallbackQuery):
        await _edit(target, text, markup)
    else:
        await target.reply(text, reply_markup=markup)


# ─── /user ───────────────────────────────────────────────────────────────────

@router.message(Command("user"))
async def cmd_user(msg: Message):
    if not utils.is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.reply("Usage: <code>/user &lt;user_id&gt;</code>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await msg.reply("❌ Invalid ID.")
        return
    await _show_profile(msg, uid)


# ─── BAN / UNBAN ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_ban_"))
@_require_admin
async def cb_ban(cq: CallbackQuery):
    uid = int(cq.data.split("_")[-1])
    db.ban_user(uid, "Banned by admin")
    db.log_action(cq.from_user.id, "BAN", uid)
    await pm.kill_all_for_user(uid)
    await cq.answer(f"✅  User {uid} banned & bots killed!", show_alert=True)
    await _show_profile(cq, uid)


@router.callback_query(F.data.startswith("adm_unban_"))
@_require_admin
async def cb_unban(cq: CallbackQuery):
    uid = int(cq.data.split("_")[-1])
    db.unban_user(uid)
    db.log_action(cq.from_user.id, "UNBAN", uid)
    await cq.answer(f"✅  User {uid} unbanned!", show_alert=True)
    await _show_profile(cq, uid)


# ─── SET PLAN ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_plan_"))
@_require_admin
async def cb_set_plan(cq: CallbackQuery):
    parts = cq.data.split("_")
    uid, plan = int(parts[2]), parts[3]
    if plan not in config.PLANS:
        await cq.answer("Invalid plan.", show_alert=True)
        return
    db.set_plan(uid, plan)
    db.log_action(cq.from_user.id, f"SET_PLAN:{plan}", uid)
    await cq.answer(f"✅  {utils.plan_label(plan)} → {uid}!", show_alert=True)
    bot_obj = cq.bot
    with suppress(Exception):
        await bot_obj.send_message(
            uid,
            f"🎉 <b>Plan Upgraded!</b>\n\n"
            f"Your new plan: {utils.plan_label(plan)}\n"
            f"Slots: <code>{utils.plan_slots(plan)}</code>\n\n"
            f"Enjoy! {utils.plan_emoji(plan)} 🚀"
        )


# ─── KILL BOTS / DELETE FILES ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_killbots_"))
@_require_admin
async def cb_kill(cq: CallbackQuery):
    uid   = int(cq.data.split("_")[-1])
    count = await pm.kill_all_for_user(uid)
    db.log_action(cq.from_user.id, "KILL_BOTS", uid, f"count={count}")
    await cq.answer(f"🛑  Killed {count} bot(s)!", show_alert=True)


@router.callback_query(F.data.startswith("adm_delfiles_"))
@_require_admin
async def cb_delfiles(cq: CallbackQuery):
    uid = int(cq.data.split("_")[-1])
    await pm.kill_all_for_user(uid)
    pm.delete_user_files(uid)
    db.log_action(cq.from_user.id, "DELETE_FILES", uid)
    await cq.answer(f"🗑  All files deleted for {uid}!", show_alert=True)


# ─── NOTE ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_note_"))
@_require_admin
async def cb_note_prompt(cq: CallbackQuery, state: FSMContext):
    uid = int(cq.data.split("_")[-1])
    await cq.answer()
    await state.set_state(AdminState.note)
    await state.update_data(target=uid)
    await cq.message.answer(
        f"📝 Send admin note for <code>{uid}</code>:",
        reply_markup=kb.kb_cancel("admin_home"),
    )


@router.message(AdminState.note, F.text)
async def handle_note(msg: Message, state: FSMContext):
    data = await state.get_data()
    uid  = data["target"]
    db.set_note(uid, msg.text.strip()[:500])
    db.log_action(msg.from_user.id, "NOTE", uid)
    await state.clear()
    await msg.reply(f"✅  Note saved for <code>{uid}</code>.")


# ─── GIVE COINS ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_coins_"))
@_require_admin
async def cb_coins_prompt(cq: CallbackQuery, state: FSMContext):
    uid = int(cq.data.split("_")[-1])
    await cq.answer()
    await state.set_state(AdminState.give_coins)
    await state.update_data(target=uid)
    row = db.get_user(uid)
    bal = row["coins"] if row else 0
    await cq.message.answer(
        f"🪙 Give/deduct coins for <code>{uid}</code>\n"
        f"Current: <code>{bal:,}</code>\n\nSend amount (negative to deduct):",
        reply_markup=kb.kb_cancel("admin_home"),
    )


@router.message(AdminState.give_coins, F.text)
async def handle_give_coins(msg: Message, state: FSMContext):
    data = await state.get_data()
    uid  = data["target"]
    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.reply("❌ Enter an integer.")
        return
    db.add_coins(uid, amount, f"admin_gift by {msg.from_user.id}")
    db.log_action(msg.from_user.id, f"COINS:{amount:+}", uid)
    row = db.get_user(uid)
    await state.clear()
    await msg.reply(
        f"{'🪙 Gave' if amount > 0 else '💸 Deducted'} "
        f"<code>{abs(amount)}</code> coins\n"
        f"New balance: <code>{row['coins']:,}</code>"
    )
    with suppress(Exception):
        await msg.bot.send_message(
            uid,
            f"{'🪙 +' if amount > 0 else '💸 −'}"
            f"<b>{abs(amount):,} coins</b> by admin!\n"
            f"Balance: <code>{row['coins']:,}</code>"
        )


# ─── SEND MESSAGE ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_msg_"))
@_require_admin
async def cb_msg_prompt(cq: CallbackQuery, state: FSMContext):
    uid = int(cq.data.split("_")[-1])
    await cq.answer()
    await state.set_state(AdminState.send_msg)
    await state.update_data(target=uid)
    await cq.message.answer(
        f"📨 Send message to <code>{uid}</code>:",
        reply_markup=kb.kb_cancel("admin_home"),
    )


@router.message(AdminState.send_msg, F.text)
async def handle_send_msg(msg: Message, state: FSMContext):
    data = await state.get_data()
    uid  = data["target"]
    await state.clear()
    try:
        await msg.bot.send_message(
            uid, f"📨 <b>Message from Admin:</b>\n\n{msg.text}"
        )
        await msg.reply(f"✅  Delivered to <code>{uid}</code>.")
    except Exception as e:
        await msg.reply(f"❌  Failed: <code>{e}</code>")


# ─── SLOTS ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_slots_"))
@_require_admin
async def cb_slots_prompt(cq: CallbackQuery, state: FSMContext):
    uid = int(cq.data.split("_")[-1])
    await cq.answer()
    row = db.get_user(uid)
    cur_bonus = row["bonus_slots"] if row else 0
    await cq.message.answer(
        f"🔲 Set bonus slots for <code>{uid}</code>\n"
        f"Current bonus: <code>{cur_bonus}</code>\n\nSend new count:",
        reply_markup=kb.kb_cancel("admin_home"),
    )
    await state.set_state(AdminState.give_slots)
    await state.update_data(target=uid)


@router.message(AdminState.give_slots, F.text)
async def handle_give_slots(msg: Message, state: FSMContext):
    data = await state.get_data()
    uid  = data["target"]
    try:
        n = int(msg.text.strip())
    except ValueError:
        await msg.reply("❌ Enter an integer.")
        return
    db.set_bonus_slots(uid, max(0, n))
    db.log_action(msg.from_user.id, f"SET_SLOTS:{n}", uid)
    await state.clear()
    await msg.reply(f"✅  Bonus slots → <code>{n}</code> for <code>{uid}</code>.")


# ─── MAINTENANCE ─────────────────────────────────────────────────────────────

@router.message(Command("maintenance"))
async def cmd_maintenance(msg: Message):
    if not utils.is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
        await msg.reply("Usage: <code>/maintenance on|off</code>")
        return
    on = parts[1].lower() == "on"
    utils.set_maintenance(on)
    db.log_action(msg.from_user.id, f"MAINTENANCE:{'ON' if on else 'OFF'}")
    db.log_event("MAINTENANCE", "ON" if on else "OFF")
    await msg.reply(f"🔧 Maintenance {'🔒 ON' if on else '🔓 OFF'}")


@router.callback_query(F.data == "adm_maint_on")
@_require_admin
async def cb_maint_on(cq: CallbackQuery):
    utils.set_maintenance(True)
    db.log_action(cq.from_user.id, "MAINTENANCE:ON")
    db.log_event("MAINTENANCE", "ON")
    await cq.answer("🔒 Maintenance ON!", show_alert=True)
    await _edit(cq, _admin_home_text(), kb.kb_admin())


@router.callback_query(F.data == "adm_maint_off")
@_require_admin
async def cb_maint_off(cq: CallbackQuery):
    utils.set_maintenance(False)
    db.log_action(cq.from_user.id, "MAINTENANCE:OFF")
    db.log_event("MAINTENANCE", "OFF")
    await cq.answer("🔓 Maintenance OFF!", show_alert=True)
    await _edit(cq, _admin_home_text(), kb.kb_admin())


# ─── BROADCAST ───────────────────────────────────────────────────────────────

@router.message(Command("broadcast"))
async def cmd_broadcast(msg: Message, state: FSMContext):
    if not utils.is_admin(msg.from_user.id):
        return
    await state.set_state(AdminState.broadcast)
    await msg.reply(
        "📢 <b>Broadcast</b>\n\nSend the message to broadcast to all users.\n"
        "Add <code>[PIN]</code> at the end to pin it.",
        reply_markup=kb.kb_cancel("admin_home"),
    )


@router.callback_query(F.data == "adm_broadcast")
@_require_admin
async def cb_broadcast(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(AdminState.broadcast)
    await cq.message.answer(
        "📢 <b>Broadcast</b>\n\nSend the message to broadcast to all users.\n"
        "Add <code>[PIN]</code> at the end to pin it.",
        reply_markup=kb.kb_cancel("admin_home"),
    )


@router.message(AdminState.broadcast, F.text)
async def handle_broadcast(msg: Message, state: FSMContext):
    await state.clear()
    text = msg.text.strip()
    pin = False
    if text.upper().endswith("[PIN]"):
        pin = True
        text = text[:-5].strip()

    ids = db.all_user_ids()
    sm = await msg.reply(f"📢 Broadcasting to <code>{len(ids)}</code> users…")
    sent = failed = 0
    for uid in ids:
        try:
            m = await msg.bot.send_message(uid, f"📢 <b>Announcement</b>\n\n{text}")
            sent += 1
            if pin:
                with suppress(Exception):
                    await msg.bot.pin_chat_message(uid, m.message_id, disable_notification=True)
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(config.BROADCAST_DELAY)

    db.log_broadcast(msg.from_user.id, text[:100], sent, failed, pin)
    db.log_action(msg.from_user.id, "BROADCAST", detail=f"sent={sent} fail={failed}")
    await sm.edit_text(
        f"📢 <b>Broadcast Complete!</b>\n\n"
        f"✅ Sent: <code>{sent}</code>\n"
        f"❌ Failed: <code>{failed}</code>\n"
        f"📌 Pinned: {'Yes' if pin else 'No'}"
    )


# ─── ADMIN LOG ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_log")
@_require_admin
async def cb_log(cq: CallbackQuery):
    await cq.answer()
    logs = db.get_log(25)
    lines = [f"📋 <b>Admin Log  (last {len(logs)})</b>\n"]
    for l in logs:
        lines.append(
            f"• <code>{l['created_at'][5:16]}</code>  "
            f"<b>{l['action']}</b>"
            + (f"  → {l['target_id']}" if l['target_id'] else "")
            + (f"  <i>{l['detail'][:40]}</i>" if l['detail'] else "")
        )
    await _edit(cq, "\n".join(lines) if lines else "No logs.", kb.kb_admin_back())


# ─── SYSTEM EVENTS ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_events")
@_require_admin
async def cb_events(cq: CallbackQuery):
    await cq.answer()
    events = db.recent_events(20)
    type_icon = {
        "BOT_START": "▶️", "BOT_STOP": "⏹", "BOT_DEPLOY": "🚀",
        "BOT_RESTART": "🔄", "RESOURCE_ALERT": "🔥", "BOT_CRASH": "💀",
        "MAINTENANCE": "🔧",
    }
    lines = [f"📡 <b>System Events  (last {len(events)})</b>\n"]
    for e in events:
        icon = type_icon.get(e["event_type"], "•")
        lines.append(
            f"{icon}  <code>{e['created_at'][5:16]}</code>  "
            f"<b>{e['event_type']}</b>"
            + (f"  <i>{e['detail'][:50]}</i>" if e["detail"] else "")
        )
    await _edit(cq, "\n".join(lines), kb.kb_admin_back())


# ─── ALL BOTS ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_allbots_"))
@_require_admin
async def cb_all_bots(cq: CallbackQuery):
    await cq.answer()
    page = int(cq.data.split("_")[-1])
    bots = db.get_all_active_bots()
    bs   = db.bot_stats()
    text = (
        f"🤖 <b>All Active Bots  ({bs['total']})</b>\n"
        f"🟢 {bs['running']}  🔴 {bs['stopped']}  🟡 {bs['error']}"
    )
    await _edit(cq, text, kb.kb_admin_bots(bots, page))


# ─── BACKUP ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_backup")
@_require_admin
async def cb_backup(cq: CallbackQuery):
    await cq.answer("Creating backup…")
    Path(config.BACKUPS_DIR).mkdir(parents=True, exist_ok=True)
    fname = f"gph_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    dest  = Path(config.BACKUPS_DIR) / fname
    shutil.copy2(config.DB_PATH, dest)
    db.log_action(cq.from_user.id, "DB_BACKUP")
    await cq.message.answer_document(
        FSInputFile(dest, filename=fname),
        caption=f"💾 <b>DB Backup</b>\n<code>{fname}</code>",
    )


# ─── ECONOMY PANEL ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_economy")
@_require_admin
async def cb_economy(cq: CallbackQuery):
    await cq.answer()
    eco = db.economy_stats()
    text = (
        "╔════════════════════════════════════╗\n"
        "║   💰  ECONOMY  CONTROL  CENTER     ║\n"
        "╚════════════════════════════════════╝\n"
        "\n"
        f"🪙  In Circulation:    <code>{utils.fmt_number(eco['total_coins'])}</code>\n"
        f"💸  Ever Distributed:  <code>{utils.fmt_number(eco['total_earned'])}</code>\n"
        f"📊  Transactions:      <code>{utils.fmt_number(eco['tx_count'])}</code>\n"
        f"🛒  Slots Purchased:   <code>{eco['slots_bought']}</code>\n"
        f"\n{utils.thin_divider()}\n"
        f"💡 <b>Earn Rates:</b>\n"
        f"   Daily base:      <code>+{config.DAILY_BASE_COINS}</code>\n"
        f"   Streak bonus:    <code>+{config.DAILY_STREAK_BONUS}/day</code>  "
        f"(cap {config.MAX_STREAK_BONUS})\n"
        f"   7-day bonus:     <code>+{config.WEEKLY_BONUS_COINS}</code>\n"
        f"   30-day bonus:    <code>+{config.MONTHLY_BONUS_COINS}</code>\n"
        f"   Referral:        <code>+{config.REFERRAL_COINS}</code>\n"
        f"\n🛒 Slot cost: <code>{config.COIN_PER_SLOT}</code> coins"
    )
    await _edit(cq, text, kb.kb_admin_back())


# ─── /exec (OWNER ONLY) ─────────────────────────────────────────────────────

@router.message(Command("exec"))
@_require_owner
async def cmd_exec(msg: Message, state: FSMContext):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await state.set_state(AdminState.exec_cmd)
        await msg.reply(
            "💻 <b>Shell Execute</b>\n\n"
            "Send the shell command to run.\n"
            "⚠️ <b>Owner only. Use with caution!</b>",
            reply_markup=kb.kb_cancel("admin_home"),
        )
        return
    await _run_exec(msg, parts[1].strip())


@router.message(AdminState.exec_cmd, F.text)
async def handle_exec(msg: Message, state: FSMContext):
    await state.clear()
    await _run_exec(msg, msg.text.strip())


async def _run_exec(msg: Message, cmd: str) -> None:
    sm = await msg.reply(f"⏳ Executing…\n<code>{cmd[:100]}</code>")
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=config.EXEC_TIMEOUT)
        output = out.decode(errors="replace")[-3500:]
        ok = proc.returncode == 0
        await sm.edit_text(
            f"{'✅' if ok else '❌'}  <b>Exit: {proc.returncode}</b>\n\n"
            f"<pre>{output or '(no output)'}</pre>"
        )
    except asyncio.TimeoutError:
        await sm.edit_text(f"❌ Timeout ({config.EXEC_TIMEOUT}s)")
    except Exception as e:
        await sm.edit_text(f"❌ Error: <code>{e}</code>")
    db.log_action(msg.from_user.id, "EXEC", detail=cmd[:200])


# ─── COMMANDS ────────────────────────────────────────────────────────────────

@router.message(Command("addcoins"))
async def cmd_addcoins(msg: Message):
    if not utils.is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply("Usage: <code>/addcoins &lt;uid&gt; &lt;amount&gt;</code>")
        return
    try:
        uid, n = int(parts[1]), int(parts[2])
    except ValueError:
        await msg.reply("❌ Invalid args.")
        return
    db.add_coins(uid, n, f"admin_cmd by {msg.from_user.id}")
    db.log_action(msg.from_user.id, f"ADDCOINS:{n}", uid)
    row = db.get_user(uid)
    await msg.reply(f"🪙  Done. Balance: <code>{row['coins']:,}</code>")


@router.message(Command("setslots"))
async def cmd_setslots(msg: Message):
    if not utils.is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply("Usage: <code>/setslots &lt;uid&gt; &lt;n&gt;</code>")
        return
    try:
        uid, n = int(parts[1]), int(parts[2])
    except ValueError:
        await msg.reply("❌ Invalid args.")
        return
    db.set_bonus_slots(uid, max(0, n))
    db.log_action(msg.from_user.id, f"SETSLOTS:{n}", uid)
    await msg.reply(f"✅  Bonus slots → <code>{n}</code> for <code>{uid}</code>.")


@router.message(Command("setplan"))
async def cmd_setplan(msg: Message):
    if not utils.is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply(
            "Usage: <code>/setplan &lt;uid&gt; &lt;plan&gt;</code>\n"
            f"Plans: {', '.join(config.PLANS.keys())}"
        )
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await msg.reply("❌ Invalid UID.")
        return
    plan = parts[2].lower()
    if plan not in config.PLANS:
        await msg.reply(f"❌ Invalid. Use: {', '.join(config.PLANS.keys())}")
        return
    db.set_plan(uid, plan)
    db.log_action(msg.from_user.id, f"SETPLAN:{plan}", uid)
    await msg.reply(f"✅  {utils.plan_label(plan)} for <code>{uid}</code>.")


@router.message(Command("finduser"))
async def cmd_finduser(msg: Message):
    if not utils.is_admin(msg.from_user.id):
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply("Usage: <code>/finduser &lt;query&gt;</code>")
        return
    results = db.search_users(parts[1].strip())
    if not results:
        await msg.reply("❌  No users found.")
        return
    lines = [f"🔍 <b>Results ({len(results)})</b>\n"]
    for r in results:
        lines.append(
            f"• <code>{r['user_id']}</code>  "
            f"{r['full_name'] or '?'}  @{r['username'] or 'N/A'}  "
            f"{utils.plan_label(r['plan'])}"
        )
    b = InlineKeyboardBuilder()
    if len(results) == 1:
        b.row(InlineKeyboardButton(
            text="👁  View Profile",
            callback_data=f"adm_view_{results[0]['user_id']}",
        ))
    await msg.reply("\n".join(lines), reply_markup=b.as_markup() if len(results) == 1 else None)


@router.message(Command("about"))
async def cmd_about(msg: Message):
    us = db.user_stats()
    bs = db.bot_stats()
    await msg.reply(
        f"╔══════════════════════════════════╗\n"
        f"║   ⚡  {config.BOT_NAME}          ║\n"
        f"╚══════════════════════════════════╝\n"
        "\n"
        f"🏷  Version:  <b>v{config.BOT_VERSION}</b>\n"
        f"👑  Owner:    {config.OWNER_USERNAME}\n"
        f"👥  Users:    <code>{us['total']}</code>\n"
        f"🤖  Bots:     <code>{bs['total']}</code> total, "
        f"<code>{bs['running']}</code> running\n\n"
        "<i>Premium Python bot hosting on Telegram.</i>"
    )
