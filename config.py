# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║   ⚡  G A D G E T   P R E M I U M   H O S T   v5.0  ·  config.py        ║
# ║   Owner : SHUVO HASSAN  (@shuvohassan00)                                  ║
# ║   Engine: aiogram 3.x · asyncio · SQLite (WAL) · psutil                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

import os

# ── IDENTITY ──────────────────────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN", "8581813381:AAFZdh0f5u_BnFTE62jPGX5-GQPccnv54Jo")   # ← SET VIA ENV!
BOT_NAME        = "⚡ GADGET PREMIUM HOST"
BOT_VERSION     = "5.0"
BOT_USERNAME    = "gadget_hosting_bot"

# ── OWNER ─────────────────────────────────────────────────────────────────────
OWNER_ID        = int(os.getenv("OWNER_ID", "7857957075"))
OWNER_USERNAME  = "@shuvohassan00"

# ── CO-ADMINS (partial admin rights, no /exec) ───────────────────────────────
CO_ADMINS: list[int] = [int(x) for x in os.getenv("CO_ADMINS", "7857957075").split(",") if x.strip()]

# ── FORCE SUBSCRIBE ──────────────────────────────────────────────────────────
PUBLIC_CHANNEL_ID    = os.getenv("PUBLIC_CHANNEL_ID", "@gadgetpremiumzone")
PUBLIC_CHANNEL_LINK  = "https://t.me/gadgetpremiumzone"
PUBLIC_CHANNEL_NAME  = "Gadget Premium Zone"

PRIVATE_CHANNEL_ID   = int(os.getenv("PRIVATE_CHANNEL_ID", "-1002429023073"))
PRIVATE_CHANNEL_LINK = "https://t.me/+HSqmdVuHFr84MzRl"
PRIVATE_CHANNEL_NAME = "Gadget VIP Lounge"

# ── STORAGE PATHS ─────────────────────────────────────────────────────────────
DB_PATH         = "data/gadget.db"
BOTS_DIR        = "data/user_bots"
LOGS_DIR        = "data/logs"
BACKUPS_DIR     = "data/backups"
TEMP_DIR        = "data/temp"
MAX_FILE_SIZE   = 10 * 1024 * 1024     # 10 MB

# ── PLANS ─────────────────────────────────────────────────────────────────────
PLANS: dict[str, dict] = {
    "free":     {"slots": 1,   "label": "🆓 Free",       "emoji": "🆓",  "color": "⬜"},
    "starter":  {"slots": 3,   "label": "⭐ Starter",     "emoji": "⭐",  "color": "🟡"},
    "pro":      {"slots": 8,   "label": "🔥 Pro",         "emoji": "🔥",  "color": "🟠"},
    "elite":    {"slots": 20,  "label": "💎 Elite",       "emoji": "💎",  "color": "🔵"},
    "ultimate": {"slots": 999, "label": "👑 Ultimate",    "emoji": "👑",  "color": "🟣"},
}

# ── ECONOMY ───────────────────────────────────────────────────────────────────
REFERRAL_COINS       = 75
DAILY_BASE_COINS     = 25
DAILY_STREAK_BONUS   = 5
MAX_STREAK_BONUS     = 50
COIN_PER_SLOT        = 150
WEEKLY_BONUS_COINS   = 200
MONTHLY_BONUS_COINS  = 1000

# ── PROCESS MANAGEMENT ───────────────────────────────────────────────────────
EXEC_TIMEOUT        = 30
GIT_TIMEOUT         = 120
PIP_TIMEOUT         = 180
MAX_AUTO_RESTART    = 5
RESTART_COOLDOWN    = 90
LOG_TAIL_BYTES      = 20480
MAX_LOG_LINES       = 100
WATCHDOG_INTERVAL   = 15

# ── RATE LIMITS ──────────────────────────────────────────────────────────────
BROADCAST_DELAY     = 0.035
USER_CMD_COOLDOWN   = 2

# ── ALERTS ───────────────────────────────────────────────────────────────────
CPU_ALERT_PCT       = 88.0
RAM_ALERT_PCT       = 88.0
DISK_ALERT_PCT      = 90.0
ALERT_COOLDOWN      = 600

# ── FEATURES ─────────────────────────────────────────────────────────────────
ENABLE_ZIP_DEPLOY      = True
ENABLE_GIT_DEPLOY      = True
ENABLE_AUTO_RESTART    = True
ENABLE_COINS           = True
ENABLE_DAILY           = True
ENABLE_SCHEDULED_BOTS  = True
ENABLE_REFERRALS       = True
ENABLE_LEADERBOARD     = True
MAINTENANCE_FILE       = "data/.maintenance"

# ── PAGINATION ───────────────────────────────────────────────────────────────
USERS_PER_PAGE      = 8
BOTS_PER_PAGE       = 6
LOGS_PER_PAGE       = 15

# ── AUTO-PIP ─────────────────────────────────────────────────────────────────
AUTO_PIP_ON_DEPLOY  = True

# ── WELCOME ──────────────────────────────────────────────────────────────────
WELCOME_GIF_URL     = ""   # optional Telegram file_id or URL for welcome animation
