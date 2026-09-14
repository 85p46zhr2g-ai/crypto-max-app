import logging
import sqlite3
import json
import os
import shutil
from datetime import datetime, timedelta
from urllib.parse import urlparse

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ============================================================
# GRAM MAX
# ============================================================

# مهم:
# ضع التوكن الجديد في Replit Secrets باسم BOT_TOKEN
BOT_TOKEN = os.getenv("8724497887:AAE02WdKwwMWaXzXmRlsVUiYjPqjVfVR5LI")

ADMIN_ID = 8183652969

BOT_USERNAME = "GramMax1_Bot"

WEBAPP_URL = "https://85p46zhr2g-ai.github.io/crypto-max-app/"

DEFAULT_CHANNEL_URL = "https://t.me/CRYBTO_MAX_1"

DEFAULT_BOT_NAME = "GRAM MAX"

DEFAULT_WELCOME_IMAGE = "https://i.ibb.co/6PqZ8XK/welcome.jpg"

SUPPORT_URL = "https://t.me/FastHelp3"

PROJECT_DEPOSIT_WALLET = (
    "UQBrfxfxzB5-op8FGLs-BxnZgOBv0CveJ8VJbC3Xc9pVXZ5X"
)

TASK_REWARD = 0.01

CHANNEL_ADD_PRICE_GRAM = 1.00
BOT_ADD_PRICE_GRAM = 0.30

MIN_TASKS_FOR_WITHDRAWAL = 5
WITHDRAWAL_FEE_PERCENT = 1.0

REFERRAL_PERCENT = 5.0

DB_FILE = "gram_max.db"

# ============================================================
# الاستثمار
# ============================================================

INVESTMENT_LEVELS = {
    1: {
        "amount": 1.0,
        "return": 1.15,
        "hours": 12,
        "name": "المستوى 1",
    },
    2: {
        "amount": 2.0,
        "return": 2.30,
        "hours": 24,
        "name": "المستوى 2",
    },
    3: {
        "amount": 5.0,
        "return": 5.70,
        "hours": 48,
        "name": "المستوى 3",
    },
    4: {
        "amount": 7.0,
        "return": 8.30,
        "hours": 72,
        "name": "المستوى 4",
    },
    5: {
        "amount": 10.0,
        "return": 13.0,
        "hours": 120,
        "name": "المستوى 5",
    },
}

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("GRAM_MAX")


# ============================================================
# Database
# ============================================================

def db():
    connection = sqlite3.connect(
        DB_FILE,
        check_same_thread=False,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    return connection


def backup_database():

    if not os.path.exists(DB_FILE):
        return

    try:

        backup_name = (
            "gram_max_backup_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".db"
        )

        shutil.copy2(
            DB_FILE,
            backup_name,
        )

        logger.info(
            "Database backup created: %s",
            backup_name,
        )

    except Exception as e:

        logger.error(
            "Database backup failed: %s",
            e,
        )


# ============================================================
# Migration
# ============================================================

def add_column_if_missing(
    connection,
    table_name,
    column_name,
    column_definition,
):

    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing = [
        row["name"]
        for row in columns
    ]

    if column_name not in existing:

        connection.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )


# ============================================================
# Init DB
# ============================================================

def init_db():

    connection = db()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referrer_id INTEGER,
            wallet_address TEXT,
            language TEXT DEFAULT 'ar',
            notified INTEGER DEFAULT 0,
            is_new INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id TEXT NOT NULL,
            reward REAL DEFAULT 0,
            completed_at TEXT,
            UNIQUE(user_id, task_id)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            wallet_address TEXT,
            tx_hash TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT,
            admin_note TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            fee REAL DEFAULT 0,
            payout_amount REAL DEFAULT 0,
            wallet_address TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT,
            admin_note TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            level INTEGER,
            amount REAL,
            return_amount REAL,
            started_at TEXT,
            finish_at TEXT,
            status TEXT DEFAULT 'active'
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_url TEXT,
            price REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bot_url TEXT,
            price REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
        """
    )

    # --------------------------------------------------------
    # Migrations
    # --------------------------------------------------------

    add_column_if_missing(
        connection,
        "deposits",
        "tx_hash",
        "TEXT",
    )

    add_column_if_missing(
        connection,
        "deposits",
        "admin_note",
        "TEXT",
    )

    add_column_if_missing(
        connection,
        "withdrawals",
        "fee",
        "REAL DEFAULT 0",
    )

    add_column_if_missing(
        connection,
        "withdrawals",
        "payout_amount",
        "REAL DEFAULT 0",
    )

    add_column_if_missing(
        connection,
        "withdrawals",
        "admin_note",
        "TEXT",
    )

    defaults = {
        "channel_url": DEFAULT_CHANNEL_URL,
        "welcome_image": DEFAULT_WELCOME_IMAGE,
        "bot_name": DEFAULT_BOT_NAME,
        "deposit_wallet": PROJECT_DEPOSIT_WALLET,
        "support_url": SUPPORT_URL,
        "treasury_gram": "0",
    }

    for key, value in defaults.items():

        connection.execute(
            """
            INSERT OR IGNORE INTO settings
            (key, value)
            VALUES (?, ?)
            """,
            (
                key,
                value,
            ),
        )

    connection.commit()
    connection.close()


# ============================================================
# Settings
# ============================================================

def get_setting(
    key,
    default=None,
):

    connection = db()

    row = connection.execute(
        """
        SELECT value
        FROM settings
        WHERE key = ?
        """,
        (key,),
    ).fetchone()

    connection.close()

    if row:
        return row["value"]

    return default


def set_setting(
    key,
    value,
):

    connection = db()

    connection.execute(
        """
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES (?, ?)
        """,
        (
            key,
            str(value),
        ),
    )

    connection.commit()
    connection.close()


# ============================================================
# Treasury
# ============================================================

def get_treasury_balance():

    value = get_setting(
        "treasury_gram",
        "0",
    )

    try:
        return float(value or 0)
    except Exception:
        return 0.0


def update_treasury(amount):

    current = get_treasury_balance()

    new_balance = current + float(amount)

    set_setting(
        "treasury_gram",
        f"{new_balance:.8f}",
    )

    return new_balance


# ============================================================
# User
# ============================================================

def get_user(user_id):

    connection = db()

    row = connection.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    connection.close()

    return row


def ensure_user(
    user_id,
    referrer_id=None,
):

    connection = db()

    row = connection.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    if row is None:

        safe_referrer = None

        if referrer_id:

            try:
                referrer_id = int(referrer_id)

                if (
                    referrer_id != int(user_id)
                    and connection.execute(
                        """
                        SELECT user_id
                        FROM users
                        WHERE user_id = ?
                        """,
                        (referrer_id,),
                    ).fetchone()
                ):
                    safe_referrer = referrer_id

            except Exception:
                safe_referrer = None

        connection.execute(
            """
            INSERT INTO users
            (
                user_id,
                balance,
                referrals,
                referrer_id,
                language,
                notified,
                is_new,
                created_at
            )
            VALUES (?, 0, 0, ?, 'ar', 0, 1, ?)
            """,
            (
                user_id,
                safe_referrer,
                datetime.now().isoformat(),
            ),
        )

        if safe_referrer:

            connection.execute(
                """
                UPDATE users
                SET referrals = referrals + 1
                WHERE user_id = ?
                """,
                (safe_referrer,),
            )

    connection.commit()

    row = connection.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    connection.close()

    return row


# ============================================================
# Balance
# ============================================================

def get_balance(user_id):

    user = get_user(user_id)

    if not user:
        return 0.0

    return float(
        user["balance"] or 0
    )


def update_balance(
    user_id,
    amount,
):

    connection = db()

    connection.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE user_id = ?
        """,
        (
            float(amount),
            user_id,
        ),
    )

    connection.commit()
    connection.close()


# ============================================================
# Wallet
# ============================================================

def valid_wallet(address):

    if not address:
        return False

    address = address.strip()

    if not (
        address.startswith("EQ")
        or address.startswith("UQ")
    ):
        return False

    if len(address) != 48:
        return False

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789_-"
    )

    return all(
        character in allowed
        for character in address
    )


def save_wallet(
    user_id,
    address,
):

    connection = db()

    connection.execute(
        """
        UPDATE users
        SET wallet_address = ?
        WHERE user_id = ?
        """,
        (
            address,
            user_id,
        ),
    )

    connection.commit()
    connection.close()


def delete_wallet(user_id):

    connection = db()

    connection.execute(
        """
        UPDATE users
        SET wallet_address = NULL
        WHERE user_id = ?
        """,
        (user_id,),
    )

    connection.commit()
    connection.close()


def get_wallet(user_id):

    user = get_user(user_id)

    if not user:
        return ""

    return user["wallet_address"] or ""


# ============================================================
# Tasks
# ============================================================

TASKS = {

    "task1": {
        "name": "CRYPTO MAX",
        "url": "https://t.me/CRYBTO_MAX_1",
        "reward": 0.01,
    },

    "task2": {
        "name": "OLKA AD",
        "url": "https://t.me/olka_ad",
        "reward": 0.01,
    },
}


def completed_tasks(user_id):

    connection = db()

    rows = connection.execute(
        """
        SELECT task_id
        FROM user_tasks
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (user_id,),
    ).fetchall()

    connection.close()

    return [
        row["task_id"]
        for row in rows
    ]


def completed_task_count(user_id):

    connection = db()

    row = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM user_tasks
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    connection.close()

    return int(
        row["count"] or 0
    )


# ============================================================
# Telegram Channel Helpers
# ============================================================

def extract_channel_username(url):

    if not url:
        return None

    try:

        parsed = urlparse(
            url.strip()
        )

        host = (
            parsed.netloc
            or ""
        ).lower()

        host = host.split(":")[0]

        if host not in (
            "t.me",
            "www.t.me",
        ):
            return None

        path = parsed.path.strip("/")

        if not path:
            return None

        if path.startswith("+"):
            return None

        if "/" in path:
            path = path.split("/")[0]

        return "@" + path.lstrip("@")

    except Exception:

        return None


async def check_channel_membership(
    bot,
    user_id,
    channel_url,
):

    username = extract_channel_username(
        channel_url
    )

    if not username:

        return (
            None,
            "❌ لا يمكن تحديد القناة من الرابط.",
        )

    try:

        member = await bot.get_chat_member(
            chat_id=username,
            user_id=user_id,
        )

        status = member.status

        if status in (
            "creator",
            "administrator",
            "member",
        ):

            return True, None

        if (
            status == "restricted"
            and getattr(
                member,
                "is_member",
                False,
            )
        ):

            return True, None

        return (
            False,
            "❌ لم يتم العثور على اشتراكك.",
        )

    except Exception as e:

        logger.exception(
            "Membership check error: %s",
            e,
        )

        return (
            None,
            "⚠️ تعذر التحقق حالياً. تأكد أن البوت موجود في القناة ولديه الصلاحية المطلوبة.",
        )


async def is_user_subscribed_to_official_channel(
    bot,
    user_id,
):

    channel_url = get_setting(
        "channel_url",
        DEFAULT_CHANNEL_URL,
    )

    return await check_channel_membership(
        bot,
        user_id,
        channel_url,
    )


# ============================================================
# Investment
# ============================================================

def get_unlocked_level(user_id):

    unlocked = 1

    connection = db()

    for level in range(
        1,
        len(INVESTMENT_LEVELS),
    ):

        next_level = level + 1

        row = connection.execute(
            """
            SELECT id
            FROM investments
            WHERE user_id = ?
            AND level = ?
            AND status = 'completed'
            LIMIT 1
            """,
            (
                user_id,
                level,
            ),
        ).fetchone()

        if row:
            unlocked = next_level
        else:
            break

    connection.close()

    return min(
        unlocked,
        len(INVESTMENT_LEVELS),
    )


def process_finished_investments(user_id):

    connection = db()

    now = datetime.now()

    rows = connection.execute(
        """
        SELECT *
        FROM investments
        WHERE user_id = ?
        AND status = 'active'
        """,
        (user_id,),
    ).fetchall()

    paid = []

    for row in rows:

        try:

            finish_time = datetime.fromisoformat(
                row["finish_at"]
            )

        except Exception:
            continue

        if now >= finish_time:

            cursor = connection.execute(
                """
                UPDATE investments
                SET status = 'completed'
                WHERE id = ?
                AND status = 'active'
                """,
                (row["id"],),
            )

            if cursor.rowcount != 1:
                continue

            connection.execute(
                """
                UPDATE users
                SET balance = balance + ?
                WHERE user_id = ?
                """,
                (
                    float(
                        row["return_amount"]
                    ),
                    user_id,
                ),
            )

            paid.append(
                float(
                    row["return_amount"]
                )
            )

    connection.commit()
    connection.close()

    return paid


def has_active_investment(user_id):

    connection = db()

    row = connection.execute(
        """
        SELECT id
        FROM investments
        WHERE user_id = ?
        AND status = 'active'
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    connection.close()

    return row is not None


def create_investment(
    user_id,
    level,
    amount,
):

    if level not in INVESTMENT_LEVELS:

        return (
            False,
            "❌ المستوى غير صحيح.",
        )

    process_finished_investments(
        user_id
    )

    if has_active_investment(
        user_id
    ):

        return (
            False,
            "⚠️ لديك استثمار نشط حالياً.",
        )

    unlocked = get_unlocked_level(
        user_id
    )

    if level > unlocked:

        return (
            False,
            f"🔒 المستوى {level} مغلق حالياً.",
        )

    data = INVESTMENT_LEVELS[level]

    expected_amount = float(
        data["amount"]
    )

    try:
        amount = float(amount)
    except Exception:
        return False, "❌ مبلغ الاستثمار غير صحيح."

    if abs(
        amount - expected_amount
    ) > 0.000001:

        return (
            False,
            "❌ مبلغ الاستثمار غير صحيح.",
        )

    return_amount = float(
        data["return"]
    )

    hours = int(
        data["hours"]
    )

    started = datetime.now()

    finish = (
        started
        + timedelta(hours=hours)
    )

    connection = db()

    try:

        active = connection.execute(
            """
            SELECT id
            FROM investments
            WHERE user_id = ?
            AND status = 'active'
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        if active:

            connection.close()

            return (
                False,
                "⚠️ لديك استثمار نشط حالياً.",
            )

        cursor = connection.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
            AND balance >= ?
            """,
            (
                expected_amount,
                user_id,
                expected_amount,
            ),
        )

        if cursor.rowcount != 1:

            connection.rollback()
            connection.close()

            return (
                False,
                "❌ رصيدك غير كافٍ.",
            )

        connection.execute(
            """
            INSERT INTO investments
            (
                user_id,
                level,
                amount,
                return_amount,
                started_at,
                finish_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'active')
            """,
            (
                user_id,
                level,
                expected_amount,
                return_amount,
                started.isoformat(),
                finish.isoformat(),
            ),
        )

        connection.commit()

    except Exception:

        connection.rollback()
        connection.close()

        logger.exception(
            "Investment error"
        )

        return (
            False,
            "❌ حدث خطأ أثناء تشغيل الاستثمار.",
        )

    connection.close()

    return (
        True,
        (
            f"✅ تم تشغيل الاستثمار.\n\n"
            f"📈 المستوى: {level}\n"
            f"💰 المبلغ: {expected_amount:.2f} GRAM\n"
            f"🎁 العائد: {return_amount:.2f} GRAM\n"
            f"⏱️ المدة: {hours} ساعة"
        ),
    )


# ============================================================
# Welcome
# ============================================================

def subscription_keyboard(channel_url):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 الاشتراك بالقناة الرسمية",
                    url=channel_url,
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ تحقق من الاشتراك",
                    callback_data="check_subscription",
                )
            ],
        ]
    )


async def send_subscription_required(
    update,
    context,
):

    image = get_setting(
        "welcome_image",
        DEFAULT_WELCOME_IMAGE,
    )

    channel_url = get_setting(
        "channel_url",
        DEFAULT_CHANNEL_URL,
    )

    text = (
        "👋 أهلاً بك في GRAM MAX\n\n"
        "🔐 قبل الدخول إلى البوت يجب الاشتراك "
        "في القناة الرسمية.\n\n"
        "📢 اشترك بالقناة ثم اضغط:\n"
        "«✅ تحقق من الاشتراك»"
    )

    keyboard = subscription_keyboard(
        channel_url
    )

    target = (
        update.callback_query.message
        if update.callback_query
        else update.message
    )

    if not target:
        return

    try:

        if update.callback_query:

            await target.reply_photo(
                photo=image,
                caption=text,
                reply_markup=keyboard,
            )

        else:

            await target.reply_photo(
                photo=image,
                caption=text,
                reply_markup=keyboard,
            )

    except Exception:

        await target.reply_text(
            text,
            reply_markup=keyboard,
        )


async def send_welcome(
    update,
    context,
    notify_admin=True,
):

    user = update.effective_user

    if not user:
        return

    args = context.args

    referrer_id = None

    if args:

        try:
            referrer_id = int(
                args[0]
            )
        except Exception:
            referrer_id = None

    ensure_user(
        user.id,
        referrer_id,
    )

    subscribed, error = (
        await is_user_subscribed_to_official_channel(
            context.bot,
            user.id,
        )
    )

    if subscribed is not True:

        await send_subscription_required(
            update,
            context,
        )

        return

    image = get_setting(
        "welcome_image",
        DEFAULT_WELCOME_IMAGE,
    )

    channel_url = get_setting(
        "channel_url",
        DEFAULT_CHANNEL_URL,
    )

    support_url = get_setting(
        "support_url",
        SUPPORT_URL,
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🚀 فتح البوت",
                    web_app=WebAppInfo(
                        url=WEBAPP_URL
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "🏢 القناة الرسمية",
                    url=channel_url,
                ),
                InlineKeyboardButton(
                    "🆘 الدعم",
                    url=support_url,
                ),
            ],
        ]
    )

    text = (
        "🎉 أهلاً وسهلاً بك في GRAM MAX\n\n"
        f"👤 {user.full_name}\n\n"
        "💰 نفّذ المهام واحصل على المكافآت.\n"
        "📈 استخدم نظام الاستثمار.\n"
        "💳 اربط محفظتك وأدر السحب.\n\n"
        "🚀 اضغط «فتح البوت» للبدء."
    )

    target = (
        update.callback_query.message
        if update.callback_query
        else update.message
    )

    if target:

        try:

            await target.reply_photo(
                photo=image,
                caption=text,
                reply_markup=keyboard,
            )

        except Exception:

            await target.reply_text(
                text,
                reply_markup=keyboard,
            )

    if notify_admin:

        existing = get_user(
            user.id
        )

        if (
            existing
            and int(
                existing["notified"] or 0
            ) == 0
        ):

            try:

                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        "👤 مستخدم جديد\n\n"
                        f"ID: `{user.id}`\n"
                        f"الاسم: {user.full_name}\n"
                        f"Username: @{user.username or 'بدون'}"
                    ),
                    parse_mode="Markdown",
                )

                connection = db()

                connection.execute(
                    """
                    UPDATE users
                    SET notified = 1,
                        is_new = 0
                    WHERE user_id = ?
                    """,
                    (user.id,),
                )

                connection.commit()
                connection.close()

            except Exception as e:

                logger.error(
                    "Admin notification error: %s",
                    e,
                )


# ============================================================
# /start
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await send_welcome(
        update,
        context,
    )


# ============================================================
# Admin
# ============================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    treasury = get_treasury_balance()

    await update.message.reply_text(
        "🛠 لوحة الإدارة\n\n"
        "/user USER_ID\n"
        "/add_balance USER_ID AMOUNT\n"
        "/remove_balance USER_ID AMOUNT\n"
        "/set_channel LINK\n"
        "/set_welcome_image URL\n"
        "/set_bot_name NAME\n"
        "/treasury\n"
        "/set_treasury AMOUNT\n\n"
        f"🏦 محفظة المشروع:\n"
        f"{get_setting('deposit_wallet')}\n\n"
        f"💰 خزينة المشروع:\n"
        f"{treasury:.8f} GRAM\n\n"
        f"🎯 شرط السحب: {MIN_TASKS_FOR_WITHDRAWAL} مهام\n"
        f"💸 رسوم السحب: {WITHDRAWAL_FEE_PERCENT}%\n"
        f"👥 الإحالة: {REFERRAL_PERCENT}%"
    )


async def treasury_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🏦 خزينة GRAM MAX\n\n"
        f"💰 {get_treasury_balance():.8f} GRAM"
    )


# ============================================================
# User Admin Command
# ============================================================

async def user_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "الاستخدام:\n/user USER_ID"
        )

        return

    try:
        user_id = int(
            context.args[0]
        )
    except Exception:

        await update.message.reply_text(
            "❌ USER_ID غير صحيح."
        )

        return

    user = get_user(
        user_id
    )

    if not user:

        await update.message.reply_text(
            "❌ المستخدم غير موجود."
        )

        return

    await update.message.reply_text(
        "👤 معلومات المستخدم\n\n"
        f"🆔 ID: {user_id}\n"
        f"💰 الرصيد: {float(user['balance'] or 0):.8f} GRAM\n"
        f"👥 الإحالات: {int(user['referrals'] or 0)}\n"
        f"🎯 المهام: {completed_task_count(user_id)}\n"
        f"📈 المستوى المفتوح: {get_unlocked_level(user_id)}\n"
        f"👛 المحفظة: {user['wallet_address'] or 'غير مربوطة'}\n"
        f"🌐 اللغة: {user['language'] or 'ar'}"
    )


# ============================================================
# Balance Admin
# ============================================================

async def add_balance_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 2:

        await update.message.reply_text(
            "الاستخدام:\n/add_balance USER_ID AMOUNT"
        )

        return

    try:

        user_id = int(
            context.args[0]
        )

        amount = float(
            context.args[1]
        )

    except Exception:

        await update.message.reply_text(
            "❌ البيانات غير صحيحة."
        )

        return

    if amount <= 0:

        await update.message.reply_text(
            "❌ المبلغ يجب أن يكون أكبر من صفر."
        )

        return

    ensure_user(
        user_id
    )

    update_balance(
        user_id,
        amount,
    )

    await update.message.reply_text(
        f"✅ تمت إضافة {amount:.8f} GRAM."
    )


async def remove_balance_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 2:

        await update.message.reply_text(
            "الاستخدام:\n/remove_balance USER_ID AMOUNT"
        )

        return

    try:

        user_id = int(
            context.args[0]
        )

        amount = float(
            context.args[1]
        )

    except Exception:

        await update.message.reply_text(
            "❌ البيانات غير صحيحة."
        )

        return

    if amount <= 0:

        await update.message.reply_text(
            "❌ المبلغ غير صحيح."
        )

        return

    connection = db()

    cursor = connection.execute(
        """
        UPDATE users
        SET balance = balance - ?
        WHERE user_id = ?
        AND balance >= ?
        """,
        (
            amount,
            user_id,
            amount,
        ),
    )

    if cursor.rowcount != 1:

        connection.rollback()
        connection.close()

        await update.message.reply_text(
            "❌ الرصيد غير كافٍ."
        )

        return

    connection.commit()
    connection.close()

    await update.message.reply_text(
        f"✅ تم خصم {amount:.8f} GRAM."
    )


# ============================================================
# Settings Admin
# ============================================================

async def set_channel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "الاستخدام:\n/set_channel https://t.me/channel"
        )

        return

    url = context.args[0]

    if not extract_channel_username(url):

        await update.message.reply_text(
            "❌ رابط القناة غير صحيح."
        )

        return

    set_setting(
        "channel_url",
        url,
    )

    await update.message.reply_text(
        "✅ تم تحديث القناة الرسمية."
    )


async def set_welcome_image_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/set_welcome_image URL"
        )
        return

    set_setting(
        "welcome_image",
        context.args[0],
    )

    await update.message.reply_text(
        "✅ تم تحديث صورة الترحيب."
    )


async def set_bot_name_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/set_bot_name NAME"
        )
        return

    name = " ".join(
        context.args
    )

    set_setting(
        "bot_name",
        name,
    )

    await update.message.reply_text(
        "✅ تم تحديث اسم البوت."
    )


async def set_treasury_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:

        await update.message.reply_text(
            "الاستخدام:\n/set_treasury AMOUNT"
        )

        return

    try:
        amount = float(
            context.args[0]
        )
    except Exception:

        await update.message.reply_text(
            "❌ المبلغ غير صحيح."
        )

        return

    if amount < 0:

        await update.message.reply_text(
            "❌ لا يمكن وضع مبلغ سالب."
        )

        return

    set_setting(
        "treasury_gram",
        f"{amount:.8f}",
    )

    await update.message.reply_text(
        f"✅ الخزينة أصبحت {amount:.8f} GRAM."
    )


# ============================================================
# Mini App - GET DATA
# ============================================================

async def send_mini_data(
    update,
    user,
):

    process_finished_investments(
        user.id
    )

    current = get_user(
        user.id
    )

    tasks = completed_tasks(
        user.id
    )

    active_investment = None

    connection = db()

    active_row = connection.execute(
        """
        SELECT *
        FROM investments
        WHERE user_id = ?
        AND status = 'active'
        ORDER BY id DESC
        LIMIT 1
        """,
        (user.id,),
    ).fetchone()

    connection.close()

    if active_row:

        active_investment = {
            "id": active_row["id"],
            "level": active_row["level"],
            "amount": active_row["amount"],
            "return_amount": active_row["return_amount"],
            "started_at": active_row["started_at"],
            "finish_at": active_row["finish_at"],
        }

    subscribed, subscription_error = (
        await is_user_subscribed_to_official_channel(
            update.get_bot(),
            user.id,
        )
    )

    result = {

        "type": "data",

        "balance": float(
            current["balance"] or 0
        ),

        "referrals": int(
            current["referrals"] or 0
        ),

        "wallet": current[
            "wallet_address"
        ] or "",

        "language": current[
            "language"
        ] or "ar",

        "telegram_user": {
            "id": user.id,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "full_name": user.full_name or "",
            "username": user.username or "",
            "photo_url": "",
        },

        "completed_tasks": tasks,

        "completed_task_count": len(tasks),

        "min_tasks_for_withdrawal":
            MIN_TASKS_FOR_WITHDRAWAL,

        "withdrawal_fee_percent":
            WITHDRAWAL_FEE_PERCENT,

        "referral_percent":
            REFERRAL_PERCENT,

        "unlocked_investment_level":
            get_unlocked_level(user.id),

        "investment_levels":
            INVESTMENT_LEVELS,

        "active_investment":
            active_investment,

        "official_channel_subscribed":
            subscribed is True,

        "subscription_check_error":
            subscription_error,

        "project_deposit_wallet":
            get_setting(
                "deposit_wallet",
                PROJECT_DEPOSIT_WALLET,
            ),

        "support_url":
            get_setting(
                "support_url",
                SUPPORT_URL,
            ),

        "channel_url":
            get_setting(
                "channel_url",
                DEFAULT_CHANNEL_URL,
            ),

        "bot_name":
            get_setting(
                "bot_name",
                DEFAULT_BOT_NAME,
            ),
    }

    await update.message.reply_text(
        "DATA:"
        + json.dumps(
            result,
            ensure_ascii=False,
        )
    )


# ============================================================
# Mini App Handler
# ============================================================

async def web_app_data_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user:
        return

    ensure_user(
        user.id
    )

    try:

        data = json.loads(
            update.effective_message
            .web_app_data
            .data
        )

    except Exception:

        await update.message.reply_text(
            "❌ البيانات المرسلة غير صحيحة."
        )

        return

    action = data.get(
        "action"
    )

    # --------------------------------------------------------
    # الاشتراك الرسمي
    # --------------------------------------------------------

    subscribed, subscription_error = (
        await is_user_subscribed_to_official_channel(
            context.bot,
            user.id,
        )
    )

    if action != "get_data":

        if subscribed is not True:

            if subscribed is False:

                await update.message.reply_text(
                    "❌ يجب الاشتراك بالقناة الرسمية أولاً."
                )

            else:

                await update.message.reply_text(
                    "⚠️ تعذر التحقق من الاشتراك حالياً."
                )

            return

    # --------------------------------------------------------
    # GET DATA
    # --------------------------------------------------------

    if action == "get_data":

        await send_mini_data(
            update,
            user,
        )

        return

    # --------------------------------------------------------
    # LINK WALLET
    # --------------------------------------------------------

    if action in (
        "link_wallet",
        "change_wallet",
    ):

        address = str(
            data.get(
                "address",
                "",
            )
        ).strip()

        if not valid_wallet(
            address
        ):

            await update.message.reply_text(
                "WALLET_ERROR:"
                + json.dumps(
                    {
                        "success": False,
                        "message":
                            "❌ عنوان محفظة TON غير صحيح.",
                    },
                    ensure_ascii=False,
                )
            )

            return

        save_wallet(
            user.id,
            address,
        )

        await update.message.reply_text(
            "WALLET_SUCCESS:"
            + json.dumps(
                {
                    "success": True,
                    "wallet": address,
                    "message":
                        "✅ تم حفظ محفظة TON بنجاح.",
                },
                ensure_ascii=False,
            )
        )

        return

    # --------------------------------------------------------
    # DELETE WALLET
    # --------------------------------------------------------

    if action == "unlink_wallet":

        delete_wallet(
            user.id
        )

        await update.message.reply_text(
            "WALLET_UNLINKED:"
            + json.dumps(
                {
                    "success": True,
                    "message":
                        "✅ تم حذف المحفظة من قاعدة البيانات.",
                },
                ensure_ascii=False,
            )
        )

        return

    # --------------------------------------------------------
    # CHANGE LANGUAGE
    # --------------------------------------------------------

    if action == "change_lang":

        language = data.get(
            "lang",
            "ar",
        )

        if language not in (
            "ar",
            "en",
            "ru",
        ):

            language = "ar"

        connection = db()

        connection.execute(
            """
            UPDATE users
            SET language = ?
            WHERE user_id = ?
            """,
            (
                language,
                user.id,
            ),
        )

        connection.commit()
        connection.close()

        await update.message.reply_text(
            "LANGUAGE_SAVED"
        )

        return

    # --------------------------------------------------------
    # VERIFY TASK
    # --------------------------------------------------------

    if action == "verify_task":

        task_id = data.get(
            "task_id"
        )

        if task_id not in TASKS:

            await update.message.reply_text(
                "VERIFY_ERROR:"
                + json.dumps(
                    {
                        "success": False,
                        "message":
                            "❌ المهمة غير موجودة.",
                    },
                    ensure_ascii=False,
                )
            )

            return

        connection = db()

        existing = connection.execute(
            """
            SELECT id
            FROM user_tasks
            WHERE user_id = ?
            AND task_id = ?
            LIMIT 1
            """,
            (
                user.id,
                task_id,
            ),
        ).fetchone()

        connection.close()

        if existing:

            await update.message.reply_text(
                "VERIFY_ALREADY:"
                + json.dumps(
                    {
                        "success": False,
                        "message":
                            "⚠️ هذه المهمة مكتملة مسبقاً.",
                    },
                    ensure_ascii=False,
                )
            )

            return

        task = TASKS[
            task_id
        ]

        subscribed, verification_error = (
            await check_channel_membership(
                context.bot,
                user.id,
                task["url"],
            )
        )

        if subscribed is None:

            await update.message.reply_text(
                "VERIFY_ERROR:"
                + json.dumps(
                    {
                        "success": False,
                        "message":
                            verification_error,
                    },
                    ensure_ascii=False,
                )
            )

            return

        if subscribed is False:

            await update.message.reply_text(
                "VERIFY_FAILED:"
                + json.dumps(
                    {
                        "success": False,
                        "message":
                            "❌ لم يتم العثور على اشتراكك. اشترك بالقناة ثم حاول مرة أخرى.",
                    },
                    ensure_ascii=False,
                )
            )

            return

        reward = float(
            task["reward"]
        )

        connection = db()

        try:

            cursor = connection.execute(
                """
                INSERT INTO user_tasks
                (
                    user_id,
                    task_id,
                    reward,
                    completed_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user.id,
                    task_id,
                    reward,
                    datetime.now().isoformat(),
                ),
            )

            if cursor.rowcount != 1:

                connection.rollback()
                connection.close()

                await update.message.reply_text(
                    "VERIFY_ERROR:"
                    + json.dumps(
                        {
                            "success": False,
                            "message":
                                "❌ تعذر تسجيل المهمة.",
                        },
                        ensure_ascii=False,
                    )
                )

                return

            connection.execute(
                """
                UPDATE users
                SET balance = balance + ?
                WHERE user_id = ?
                """,
                (
                    reward,
                    user.id,
                ),
            )

            connection.commit()

        except sqlite3.IntegrityError:

            connection.rollback()
            connection.close()

            await update.message.reply_text(
                "VERIFY_ALREADY:"
                + json.dumps(
                    {
                        "success": False,
                        "message":
                            "⚠️ هذه المهمة مكتملة مسبقاً.",
                    },
                    ensure_ascii=False,
                )
            )

            return

        except Exception:

            connection.rollback()
            connection.close()

            logger.exception(
                "Task completion error"
            )

            await update.message.reply_text(
                "VERIFY_ERROR:"
                + json.dumps(
                    {
                        "success": False,
                        "message":
                            "❌ حدث خطأ ولم تتم إضافة المكافأة.",
                    },
                    ensure_ascii=False,
                )
            )

            return

        connection.close()

        await update.message.reply_text(
            "VERIFY_SUCCESS:"
            + json.dumps(
                {
                    "success": True,
                    "task_id": task_id,
                    "reward": reward,
                    "message":
                        "✅ تم التحقق بنجاح.",
                },
                ensure_ascii=False,
            )
        )

        return

    # --------------------------------------------------------
    # INVEST
    # --------------------------------------------------------

    if action == "invest_start":

        try:

            level = int(
                data.get("level")
            )

            amount = float(
                data.get("amount")
            )

        except Exception:

            await update.message.reply_text(
                "❌ بيانات الاستثمار غير صحيحة."
            )

            return

        success, message = create_investment(
            user.id,
            level,
            amount,
        )

        if success:

            await update.message.reply_text(
                "INVEST_SUCCESS\n"
                + message
            )

        else:

            await update.message.reply_text(
                "INVEST_ERROR\n"
                + message
            )

        return

    # --------------------------------------------------------
    # DEPOSIT
    # --------------------------------------------------------

    if action == "create_deposit":

        try:

            amount = float(
                data.get("amount")
            )

        except Exception:

            await update.message.reply_text(
                "DEPOSIT_ERROR:❌ مبلغ الإيداع غير صحيح."
            )

            return

        if amount <= 0:

            await update.message.reply_text(
                "DEPOSIT_ERROR:❌ المبلغ يجب أن يكون أكبر من صفر."
            )

            return

        tx_hash = str(
            data.get(
                "tx_hash",
                "",
            )
        ).strip()

        if len(tx_hash) < 10:

            await update.message.reply_text(
                "DEPOSIT_ERROR:❌ Tx Hash غير صحيح."
            )

            return

        project_wallet = get_setting(
            "deposit_wallet",
            PROJECT_DEPOSIT_WALLET,
        )

        connection = db()

        existing_tx = connection.execute(
            """
            SELECT id
            FROM deposits
            WHERE tx_hash = ?
            LIMIT 1
            """,
            (tx_hash,),
        ).fetchone()

        if existing_tx:

            connection.close()

            await update.message.reply_text(
                "DEPOSIT_ERROR:⚠️ هذا Tx Hash مسجل مسبقاً."
            )

            return

        cursor = connection.execute(
            """
            INSERT INTO deposits
            (
                user_id,
                amount,
                wallet_address,
                tx_hash,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                user.id,
                amount,
                project_wallet,
                tx_hash,
                datetime.now().isoformat(),
            ),
        )

        deposit_id = cursor.lastrowid

        connection.commit()
        connection.close()

        request_number = (
            f"DEP-{deposit_id:06d}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ تأكيد الإيداع",
                        callback_data=(
                            f"dep_approve_{deposit_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        "❌ رفض",
                        callback_data=(
                            f"dep_reject_{deposit_id}"
                        ),
                    ),
                ]
            ]
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "💰 إيداع جديد\n\n"
                f"🔢 الطلب: {request_number}\n"
                f"👤 المستخدم: `{user.id}`\n"
                f"💵 المبلغ: {amount:.8f} GRAM\n\n"
                f"🏦 محفظة المشروع:\n"
                f"{project_wallet}\n\n"
                f"🔗 Tx Hash:\n"
                f"{tx_hash}\n\n"
                "⚠️ لا يتم إضافة الرصيد إلا بعد التأكد والموافقة."
            ),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        await update.message.reply_text(
            "DEPOSIT_PENDING:"
            + json.dumps(
                {
                    "request": request_number,
                    "wallet": project_wallet,
                    "amount": amount,
                },
                ensure_ascii=False,
            )
        )

        return

    # --------------------------------------------------------
    # WITHDRAW
    # --------------------------------------------------------

    if action == "create_withdrawal":

        try:

            amount = float(
                data.get("amount")
            )

        except Exception:

            await update.message.reply_text(
                "WITHDRAW_ERROR:❌ مبلغ السحب غير صحيح."
            )

            return

        if amount <= 0:

            await update.message.reply_text(
                "WITHDRAW_ERROR:❌ المبلغ يجب أن يكون أكبر من صفر."
            )

            return

        task_count = completed_task_count(
            user.id
        )

        if task_count < MIN_TASKS_FOR_WITHDRAWAL:

            remaining = (
                MIN_TASKS_FOR_WITHDRAWAL
                - task_count
            )

            await update.message.reply_text(
                "WITHDRAW_ERROR:"
                + json.dumps(
                    {
                        "message":
                            f"❌ يجب إكمال {MIN_TASKS_FOR_WITHDRAWAL} مهام. المتبقي: {remaining}",
                    },
                    ensure_ascii=False,
                )
            )

            return

        wallet = get_wallet(
            user.id
        )

        if not valid_wallet(wallet):

            await update.message.reply_text(
                "WITHDRAW_ERROR:❌ يجب ربط محفظة TON أولاً."
            )

            return

        fee = (
            amount
            * WITHDRAWAL_FEE_PERCENT
            / 100
        )

        payout_amount = (
            amount - fee
        )

        if payout_amount <= 0:

            await update.message.reply_text(
                "WITHDRAW_ERROR:❌ المبلغ غير صالح."
            )

            return

        connection = db()

        try:

            cursor = connection.execute(
                """
                UPDATE users
                SET balance = balance - ?
                WHERE user_id = ?
                AND balance >= ?
                """,
                (
                    amount,
                    user.id,
                    amount,
                ),
            )

            if cursor.rowcount != 1:

                connection.rollback()
                connection.close()

                await update.message.reply_text(
                    "WITHDRAW_ERROR:❌ رصيدك غير كافٍ."
                )

                return

            cursor = connection.execute(
                """
                INSERT INTO withdrawals
                (
                    user_id,
                    amount,
                    fee,
                    payout_amount,
                    wallet_address,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    user.id,
                    amount,
                    fee,
                    payout_amount,
                    wallet,
                    datetime.now().isoformat(),
                ),
            )

            withdrawal_id = cursor.lastrowid

            connection.commit()

        except Exception:

            connection.rollback()
            connection.close()

            logger.exception(
                "Withdrawal error"
            )

            await update.message.reply_text(
                "WITHDRAW_ERROR:❌ حدث خطأ أثناء إنشاء طلب السحب."
            )

            return

        connection.close()

        request_number = (
            f"WD-{withdrawal_id:06d}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💸 تم الدفع",
                        callback_data=(
                            f"wd_paid_{withdrawal_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        "❌ رفض وإرجاع",
                        callback_data=(
                            f"wd_reject_{withdrawal_id}"
                        ),
                    ),
                ]
            ]
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "💵 طلب سحب جديد\n\n"
                f"🔢 الطلب: {request_number}\n"
                f"👤 المستخدم: `{user.id}`\n"
                f"💰 المبلغ: {amount:.8f} GRAM\n"
                f"💸 الرسوم: {fee:.8f} GRAM\n"
                f"💵 الصافي: {payout_amount:.8f} GRAM\n\n"
                f"👛 المحفظة:\n{wallet}\n\n"
                "⚠️ تم حجز المبلغ من رصيد المستخدم."
            ),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        await update.message.reply_text(
            "WITHDRAW_PENDING:"
            + json.dumps(
                {
                    "request": request_number,
                    "amount": amount,
                    "fee": fee,
                    "payout": payout_amount,
                },
                ensure_ascii=False,
            )
        )

        return

    # --------------------------------------------------------
    # SUPPORT
    # --------------------------------------------------------

    if action == "support":

        await update.message.reply_text(
            "SUPPORT_URL:"
            + get_setting(
                "support_url",
                SUPPORT_URL,
            )
        )

        return

    # --------------------------------------------------------
    # ADD CHANNEL
    # --------------------------------------------------------

    if action == "add_channel":

        channel_url = str(
            data.get(
                "channel_url",
                "",
            )
        ).strip()

        if not channel_url.startswith(
            "https://t.me/"
        ):

            await update.message.reply_text(
                "❌ رابط القناة غير صحيح."
            )

            return

        price = CHANNEL_ADD_PRICE_GRAM

        connection = db()

        cursor = connection.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
            AND balance >= ?
            """,
            (
                price,
                user.id,
                price,
            ),
        )

        if cursor.rowcount != 1:

            connection.rollback()
            connection.close()

            await update.message.reply_text(
                f"❌ رصيدك غير كافٍ.\nالمطلوب: {price:.2f} GRAM"
            )

            return

        cursor = connection.execute(
            """
            INSERT INTO channel_requests
            (
                user_id,
                channel_url,
                price,
                status,
                created_at
            )
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (
                user.id,
                channel_url,
                price,
                datetime.now().isoformat(),
            ),
        )

        request_id = cursor.lastrowid

        connection.commit()
        connection.close()

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ قبول القناة",
                        callback_data=(
                            f"ch_approve_{request_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        "❌ رفض وإرجاع",
                        callback_data=(
                            f"ch_reject_{request_id}"
                        ),
                    ),
                ]
            ]
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "📢 طلب إضافة قناة\n\n"
                f"🔢 CH-{request_id:06d}\n"
                f"👤 `{user.id}`\n"
                f"🔗 {channel_url}\n"
                f"💰 السعر: {price:.2f} GRAM"
            ),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        await update.message.reply_text(
            "CHANNEL_PENDING"
        )

        return

    # --------------------------------------------------------
    # ADD BOT
    # --------------------------------------------------------

    if action == "add_bot":

        bot_url = str(
            data.get(
                "bot_url",
                "",
            )
        ).strip()

        if not bot_url.startswith(
            "https://t.me/"
        ):

            await update.message.reply_text(
                "❌ رابط البوت غير صحيح."
            )

            return

        price = BOT_ADD_PRICE_GRAM

        connection = db()

        cursor = connection.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
            AND balance >= ?
            """,
            (
                price,
                user.id,
                price,
            ),
        )

        if cursor.rowcount != 1:

            connection.rollback()
            connection.close()

            await update.message.reply_text(
                f"❌ رصيدك غير كافٍ.\nالمطلوب: {price:.2f} GRAM"
            )

            return

        cursor = connection.execute(
            """
            INSERT INTO bot_requests
            (
                user_id,
                bot_url,
                price,
                status,
                created_at
            )
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (
                user.id,
                bot_url,
                price,
                datetime.now().isoformat(),
            ),
        )

        request_id = cursor.lastrowid

        connection.commit()
        connection.close()

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ قبول البوت",
                        callback_data=(
                            f"bot_approve_{request_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        "❌ رفض وإرجاع",
                        callback_data=(
                            f"bot_reject_{request_id}"
                        ),
                    ),
                ]
            ]
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🤖 طلب إضافة بوت\n\n"
                f"🔢 BOT-{request_id:06d}\n"
                f"👤 `{user.id}`\n"
                f"🔗 {bot_url}\n"
                f"💰 السعر: {price:.2f} GRAM"
            ),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        await update.message.reply_text(
            "BOT_PENDING"
        )

        return

    await update.message.reply_text(
        "❌ الأمر غير معروف."
    )


# ============================================================
# Callback Handler
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query.data == "check_subscription":

        await query.answer(
            "⏳ جاري التحقق..."
        )

        user_id = query.from_user.id

        ensure_user(
            user_id
        )

        subscribed, error = (
            await is_user_subscribed_to_official_channel(
                context.bot,
                user_id,
            )
        )

        if subscribed is True:

            image = get_setting(
                "welcome_image",
                DEFAULT_WELCOME_IMAGE,
            )

            channel_url = get_setting(
                "channel_url",
                DEFAULT_CHANNEL_URL,
            )

            support_url = get_setting(
                "support_url",
                SUPPORT_URL,
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🚀 فتح البوت",
                            web_app=WebAppInfo(
                                url=WEBAPP_URL
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🏢 القناة الرسمية",
                            url=channel_url,
                        ),
                        InlineKeyboardButton(
                            "🆘 الدعم",
                            url=support_url,
                        ),
                    ],
                ]
            )

            try:
                await query.message.delete()
            except Exception:
                pass

            try:

                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=image,
                    caption=(
                        "✅ تم التحقق بنجاح!\n\n"
                        "🎉 أهلاً بك في GRAM MAX.\n\n"
                        "🚀 اضغط «فتح البوت» للبدء."
                    ),
                    reply_markup=keyboard,
                )

            except Exception:

                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "✅ تم التحقق بنجاح!\n\n"
                        "🚀 اضغط «فتح البوت» للبدء."
                    ),
                    reply_markup=keyboard,
                )

            return

        if subscribed is False:

            await query.answer(
                "❌ لم يتم العثور على اشتراكك.",
                show_alert=True,
            )

            return

        await query.answer(
            "⚠️ تعذر التحقق حالياً.",
            show_alert=True,
        )

        return

    # --------------------------------------------------------
    # Admin only
    # --------------------------------------------------------

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "❌ غير مسموح.",
            show_alert=True,
        )

        return

    await query.answer()

    data = query.data

    # ========================================================
    # DEPOSIT APPROVE
    # ========================================================

    if data.startswith("dep_approve_"):

        deposit_id = int(
            data.split("_")[-1]
        )

        connection = db()

        row = connection.execute(
            """
            SELECT *
            FROM deposits
            WHERE id = ?
            """,
            (deposit_id,),
        ).fetchone()

        if not row:

            connection.close()

            await query.edit_message_text(
                "❌ طلب الإيداع غير موجود."
            )

            return

        if row["status"] != "pending":

            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        cursor = connection.execute(
            """
            UPDATE deposits
            SET status = 'approved',
                processed_at = ?
            WHERE id = ?
            AND status = 'pending'
            """,
            (
                datetime.now().isoformat(),
                deposit_id,
            ),
        )

        if cursor.rowcount != 1:

            connection.rollback()
            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        connection.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (
                float(row["amount"]),
                int(row["user_id"]),
            ),
        )

        connection.commit()
        connection.close()

        treasury = update_treasury(
            float(row["amount"])
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n"
            "✅ تم تأكيد الإيداع.\n"
            f"🏦 الخزينة: {treasury:.8f} GRAM"
        )

        try:

            await context.bot.send_message(
                chat_id=int(row["user_id"]),
                text=(
                    "✅ تم تأكيد الإيداع.\n\n"
                    f"💰 تمت إضافة "
                    f"{float(row['amount']):.8f} GRAM."
                ),
            )

        except Exception:
            pass

        return

    # ========================================================
    # DEPOSIT REJECT
    # ========================================================

    if data.startswith("dep_reject_"):

        deposit_id = int(
            data.split("_")[-1]
        )

        connection = db()

        row = connection.execute(
            """
            SELECT *
            FROM deposits
            WHERE id = ?
            """,
            (deposit_id,),
        ).fetchone()

        if not row:

            connection.close()
            return

        if row["status"] != "pending":

            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        connection.execute(
            """
            UPDATE deposits
            SET status = 'rejected',
                processed_at = ?
            WHERE id = ?
            AND status = 'pending'
            """,
            (
                datetime.now().isoformat(),
                deposit_id,
            ),
        )

        connection.commit()
        connection.close()

        await query.edit_message_text(
            query.message.text
            + "\n\n❌ تم رفض الإيداع."
        )

        try:

            await context.bot.send_message(
                chat_id=int(row["user_id"]),
                text=(
                    "❌ تم رفض طلب الإيداع.\n\n"
                    "لم تتم إضافة أي رصيد."
                ),
            )

        except Exception:
            pass

        return

    # ========================================================
    # WITHDRAW PAID
    # ========================================================

    if data.startswith("wd_paid_"):

        withdrawal_id = int(
            data.split("_")[-1]
        )

        connection = db()

        row = connection.execute(
            """
            SELECT *
            FROM withdrawals
            WHERE id = ?
            """,
            (withdrawal_id,),
        ).fetchone()

        if not row:

            connection.close()
            return

        if row["status"] != "pending":

            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        cursor = connection.execute(
            """
            UPDATE withdrawals
            SET status = 'paid',
                processed_at = ?
            WHERE id = ?
            AND status = 'pending'
            """,
            (
                datetime.now().isoformat(),
                withdrawal_id,
            ),
        )

        if cursor.rowcount != 1:

            connection.rollback()
            connection.close()
            return

        connection.commit()
        connection.close()

        # رسوم السحب تدخل الخزينة
        update_treasury(
            float(row["fee"])
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n💸 تم تسجيل السحب كمدفوع."
        )

        try:

            await context.bot.send_message(
                chat_id=int(row["user_id"]),
                text=(
                    "💸 تم دفع طلب السحب.\n\n"
                    f"💰 المبلغ المدفوع: "
                    f"{float(row['payout_amount']):.8f} GRAM\n"
                    f"💸 الرسوم: "
                    f"{float(row['fee']):.8f} GRAM"
                ),
            )

        except Exception:
            pass

        return

    # ========================================================
    # WITHDRAW REJECT
    # ========================================================

    if data.startswith("wd_reject_"):

        withdrawal_id = int(
            data.split("_")[-1]
        )

        connection = db()

        row = connection.execute(
            """
            SELECT *
            FROM withdrawals
            WHERE id = ?
            """,
            (withdrawal_id,),
        ).fetchone()

        if not row:

            connection.close()
            return

        if row["status"] != "pending":

            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        cursor = connection.execute(
            """
            UPDATE withdrawals
            SET status = 'rejected',
                processed_at = ?
            WHERE id = ?
            AND status = 'pending'
            """,
            (
                datetime.now().isoformat(),
                withdrawal_id,
            ),
        )

        if cursor.rowcount != 1:

            connection.rollback()
            connection.close()
            return

        connection.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (
                float(row["amount"]),
                int(row["user_id"]),
            ),
        )

        connection.commit()
        connection.close()

        await query.edit_message_text(
            query.message.text
            + "\n\n❌ تم رفض السحب وإرجاع الرصيد."
        )

        try:

            await context.bot.send_message(
                chat_id=int(row["user_id"]),
                text=(
                    "❌ تم رفض طلب السحب.\n\n"
                    f"↩️ تمت إعادة "
                    f"{float(row['amount']):.8f} GRAM."
                ),
            )

        except Exception:
            pass

        return

    # ========================================================
    # CHANNEL APPROVE
    # ========================================================

    if data.startswith("ch_approve_"):

        request_id = int(
            data.split("_")[-1]
        )

        connection = db()

        row = connection.execute(
            """
            SELECT *
            FROM channel_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()

        if not row:

            connection.close()
            return

        if row["status"] != "pending":

            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        connection.execute(
            """
            UPDATE channel_requests
            SET status = 'approved'
            WHERE id = ?
            AND status = 'pending'
            """,
            (request_id,),
        )

        connection.commit()
        connection.close()

        update_treasury(
            float(row["price"])
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n✅ تم قبول القناة."
        )

        try:

            await context.bot.send_message(
                chat_id=int(row["user_id"]),
                text="✅ تم قبول طلب إضافة القناة.",
            )

        except Exception:
            pass

        return

    # ========================================================
    # CHANNEL REJECT
    # ========================================================

    if data.startswith("ch_reject_"):

        request_id = int(
            data.split("_")[-1]
        )

        connection = db()

        row = connection.execute(
            """
            SELECT *
            FROM channel_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()

        if not row:

            connection.close()
            return

        if row["status"] != "pending":

            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        connection.execute(
            """
            UPDATE channel_requests
            SET status = 'rejected'
            WHERE id = ?
            AND status = 'pending'
            """,
            (request_id,),
        )

        connection.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (
                float(row["price"]),
                int(row["user_id"]),
            ),
        )

        connection.commit()
        connection.close()

        await query.edit_message_text(
            query.message.text
            + "\n\n❌ تم رفض القناة وإرجاع الرصيد."
        )

        try:

            await context.bot.send_message(
                chat_id=int(row["user_id"]),
                text=(
                    "❌ تم رفض طلب إضافة القناة.\n\n"
                    f"↩️ تمت إعادة "
                    f"{float(row['price']):.8f} GRAM."
                ),
            )

        except Exception:
            pass

        return

    # ========================================================
    # BOT APPROVE
    # ========================================================

    if data.startswith("bot_approve_"):

        request_id = int(
            data.split("_")[-1]
        )

        connection = db()

        row = connection.execute(
            """
            SELECT *
            FROM bot_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()

        if not row:

            connection.close()
            return

        if row["status"] != "pending":

            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        connection.execute(
            """
            UPDATE bot_requests
            SET status = 'approved'
            WHERE id = ?
            AND status = 'pending'
            """,
            (request_id,),
        )

        connection.commit()
        connection.close()

        update_treasury(
            float(row["price"])
        )

        await query.edit_message_text(
            query.message.text
            + "\n\n✅ تم قبول البوت."
        )

        try:

            await context.bot.send_message(
                chat_id=int(row["user_id"]),
                text="✅ تم قبول طلب إضافة البوت.",
            )

        except Exception:
            pass

        return

    # ========================================================
    # BOT REJECT
    # ========================================================

    if data.startswith("bot_reject_"):

        request_id = int(
            data.split("_")[-1]
        )

        connection = db()

        row = connection.execute(
            """
            SELECT *
            FROM bot_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()

        if not row:

            connection.close()
            return

        if row["status"] != "pending":

            connection.close()

            await query.answer(
                "⚠️ تمت معالجة الطلب مسبقاً.",
                show_alert=True,
            )

            return

        connection.execute(
            """
            UPDATE bot_requests
            SET status = 'rejected'
            WHERE id = ?
            AND status = 'pending'
            """,
            (request_id,),
        )

        connection.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (
                float(row["price"]),
                int(row["user_id"]),
            ),
        )

        connection.commit()
        connection.close()

        await query.edit_message_text(
            query.message.text
            + "\n\n❌ تم رفض البوت وإرجاع الرصيد."
        )

        try:

            await context.bot.send_message(
                chat_id=int(row["user_id"]),
                text=(
                    "❌ تم رفض طلب إضافة البوت.\n\n"
                    f"↩️ تمت إعادة "
                    f"{float(row['price']):.8f} GRAM."
                ),
            )

        except Exception:
            pass

        return


# ============================================================
# Main
# ============================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN غير موجود. "
            "ضع التوكن الجديد في Replit Secrets باسم BOT_TOKEN."
        )

    if os.path.exists(DB_FILE):

        backup_database()

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "treasury",
            treasury_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "set_treasury",
            set_treasury_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "user",
            user_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "add_balance",
            add_balance_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "remove_balance",
            remove_balance_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "set_channel",
            set_channel_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "set_welcome_image",
            set_welcome_image_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "set_bot_name",
            set_bot_name_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            web_app_data_handler,
        )
    )

    print("===================================")
    print("GRAM MAX BOT STARTED")
    print(
        "Withdrawal tasks:",
        MIN_TASKS_FOR_WITHDRAWAL,
    )
    print(
        "Withdrawal fee:",
        WITHDRAWAL_FEE_PERCENT,
        "%",
    )
    print(
        "Referral:",
        REFERRAL_PERCENT,
        "%",
    )
    print(
        "Investment levels:",
        len(INVESTMENT_LEVELS),
    )
    print(
        "Real Telegram verification: ENABLED"
    )
    print(
        "Wallet DB management: ENABLED"
    )
    print(
        "Server-side withdrawal deduction: ENABLED"
    )
    print(
        "Database migration: ENABLED"
    )
    print("===================================")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
