import logging
import sqlite3
import json
import shutil
import os
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ============================================================
#                    GRAM MAX — BOT.PY
# ============================================================

BOT_TOKEN = "8724497887:AAE02WdKwwMWaXzXmRlsVUiYjPqjVfVR5LI"

ADMIN_ID = 8183652969

BOT_USERNAME = "GramMax1_Bot"

WEBAPP_URL = "https://85p46zhr2g-ai.github.io/crypto-max-app/"

DEFAULT_CHANNEL_URL = "https://t.me/CRYBTO_MAX_1"

DEFAULT_BOT_NAME = "GRAM MAX"

DEFAULT_WELCOME_IMAGE = "https://i.ibb.co/6PqZ8XK/welcome.jpg"

# الدعم
SUPPORT_USERNAME = "FastHelp3"

# محفظة الإيداع العامة للمشروع
DEFAULT_DEPOSIT_WALLET = (
    "UQBrfxfxzB5-op8FGLs-BxnZgOBv0CveJ8VJbC3Xc9pVXZ5X"
)

# ============================================================
#                         الأسعار
# ============================================================

CURRENCY = "GRAM"

TASK_REWARD = 0.01

# حسب النظام الذي حددته:
CHANNEL_ADD_PRICE = 1.00
BOT_ADD_PRICE = 0.30

# السحب لا يفتح قبل 10 مهام
WITHDRAWAL_REQUIRED_TASKS = 10

# ============================================================
#                       الاستثمار
# ============================================================

INVESTMENT_LEVELS = {
    1: {
        "amount": 1.0,
        "return": 1.15,
        "hours": 12,
    },
    2: {
        "amount": 2.0,
        "return": 2.30,
        "hours": 24,
    },
    3: {
        "amount": 5.0,
        "return": 5.70,
        "hours": 48,
    },
}

# ============================================================
#                         Logging
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ============================================================
#                       قاعدة البيانات
# ============================================================

DB_NAME = "gram_max.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def backup_database():
    """
    نسخ احتياطي قبل أي تعديل على قاعدة البيانات.
    """
    if not os.path.exists(DB_NAME):
        return

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{DB_NAME}.backup_{timestamp}"
        shutil.copy2(DB_NAME, backup_name)
        logger.info("Database backup created: %s", backup_name)
    except Exception as e:
        logger.error("Backup error: %s", e)


def column_exists(conn, table_name, column_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def add_column_if_missing(
    conn,
    table_name,
    column_name,
    definition
):
    if not column_exists(
        conn,
        table_name,
        column_name
    ):
        conn.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {definition}"
        )


def init_db():

    # نسخة احتياطية قبل التعديل
    backup_database()

    conn = get_connection()
    cursor = conn.cursor()

    # ========================================================
    # USERS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            referrals INTEGER DEFAULT 0,
            referrer_id INTEGER,
            wallet_address TEXT,
            language TEXT DEFAULT 'ar',
            notified INTEGER DEFAULT 0,
            is_new INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ========================================================
    # USER TASKS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id TEXT NOT NULL,
            reward REAL DEFAULT 0,
            completed_at TEXT,
            UNIQUE(user_id, task_id)
        )
    """)

    # ========================================================
    # SETTINGS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # ========================================================
    # DEPOSITS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            wallet_address TEXT,
            tx_hash TEXT,
            status TEXT DEFAULT 'pending',
            admin_note TEXT,
            created_at TEXT,
            processed_at TEXT
        )
    """)

    # ========================================================
    # WITHDRAWALS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            wallet_address TEXT,
            status TEXT DEFAULT 'pending',
            admin_note TEXT,
            created_at TEXT,
            processed_at TEXT
        )
    """)

    # ========================================================
    # INVESTMENTS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            level INTEGER NOT NULL,
            amount REAL NOT NULL,
            return_amount REAL NOT NULL,
            started_at TEXT,
            finish_at TEXT,
            status TEXT DEFAULT 'active'
        )
    """)

    # ========================================================
    # CHANNEL REQUESTS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_url TEXT NOT NULL,
            price REAL DEFAULT 1.0,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT
        )
    """)

    # ========================================================
    # BOT REQUESTS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bot_url TEXT NOT NULL,
            price REAL DEFAULT 0.30,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT
        )
    """)

    # ========================================================
    # TASK SOURCES
    # القنوات والبوتات المقبولة التي تظهر للناس كمهمات
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_name TEXT,
            owner_id INTEGER NOT NULL,
            reward REAL DEFAULT 0.01,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
    """)

    # ========================================================
    # MIGRATION
    # نحافظ على قاعدة البيانات القديمة
    # ========================================================

    add_column_if_missing(
        conn,
        "deposits",
        "tx_hash",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "deposits",
        "admin_note",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "withdrawals",
        "admin_note",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "withdrawals",
        "processed_at",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "channel_requests",
        "processed_at",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "bot_requests",
        "processed_at",
        "TEXT"
    )

    # ========================================================
    # DEFAULT SETTINGS
    # ========================================================

    defaults = {
        "channel_url": DEFAULT_CHANNEL_URL,
        "welcome_image": DEFAULT_WELCOME_IMAGE,
        "bot_name": DEFAULT_BOT_NAME,
        "deposit_wallet": DEFAULT_DEPOSIT_WALLET,
    }

    for key, value in defaults.items():

        cursor.execute(
            """
            INSERT OR IGNORE INTO settings
            (key, value)
            VALUES (?, ?)
            """,
            (key, value)
        )

    conn.commit()
    conn.close()


# ============================================================
#                         SETTINGS
# ============================================================

def get_setting(key, default=""):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT value
        FROM settings
        WHERE key = ?
        """,
        (key,)
    ).fetchone()

    conn.close()

    if row:
        return row["value"]

    return default


def set_setting(key, value):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO settings
        (key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
        """,
        (key, str(value))
    )

    conn.commit()
    conn.close()


# ============================================================
#                         USERS
# ============================================================

def get_user(user_id):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    if not row:

        conn.execute(
            """
            INSERT INTO users
            (
                user_id,
                balance,
                referrals,
                referrer_id,
                wallet_address,
                language,
                notified,
                is_new,
                created_at
            )
            VALUES
            (?, 0, 0, NULL, NULL, 'ar', 0, 1, ?)
            """,
            (
                user_id,
                now()
            )
        )

        conn.commit()

        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

    conn.close()

    return row


def get_balance(user_id):

    user = get_user(user_id)

    return float(
        user["balance"] or 0
    )


def update_balance(
    user_id,
    amount
):

    conn = get_connection()

    conn.execute(
        """
        UPDATE users
        SET balance = ROUND(balance + ?, 8)
        WHERE user_id = ?
        """,
        (
            amount,
            user_id
        )
    )

    conn.commit()
    conn.close()


def set_balance(
    user_id,
    amount
):

    conn = get_connection()

    conn.execute(
        """
        UPDATE users
        SET balance = ROUND(?, 8)
        WHERE user_id = ?
        """,
        (
            amount,
            user_id
        )
    )

    conn.commit()
    conn.close()


def mark_user_not_new(user_id):

    conn = get_connection()

    conn.execute(
        """
        UPDATE users
        SET is_new = 0
        WHERE user_id = ?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()


# ============================================================
#                         WALLET
# ============================================================

def save_wallet(
    user_id,
    wallet
):

    conn = get_connection()

    conn.execute(
        """
        UPDATE users
        SET wallet_address = ?
        WHERE user_id = ?
        """,
        (
            wallet,
            user_id
        )
    )

    conn.commit()
    conn.close()


def get_wallet(user_id):

    user = get_user(user_id)

    return user["wallet_address"] or ""


def valid_wallet(address):

    if not address:
        return False

    address = address.strip()

    return (
        address.startswith("EQ")
        or address.startswith("UQ")
    )


# ============================================================
#                         TASKS
# ============================================================

def get_completed_task_count(user_id):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM user_tasks
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    return int(row["total"])


def is_task_completed(
    user_id,
    task_id
):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT id
        FROM user_tasks
        WHERE user_id = ?
        AND task_id = ?
        """,
        (
            user_id,
            task_id
        )
    ).fetchone()

    conn.close()

    return row is not None


def complete_task(
    user_id,
    task_id,
    reward
):

    conn = get_connection()

    try:

        conn.execute(
            """
            INSERT INTO user_tasks
            (
                user_id,
                task_id,
                reward,
                completed_at
            )
            VALUES
            (?, ?, ?, ?)
            """,
            (
                user_id,
                task_id,
                reward,
                now()
            )
        )

        conn.execute(
            """
            UPDATE users
            SET balance = ROUND(balance + ?, 8)
            WHERE user_id = ?
            """,
            (
                reward,
                user_id
            )
        )

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        conn.rollback()

        return False

    finally:

        conn.close()


def get_task_sources():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM task_sources
        WHERE status = 'active'
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows


# ============================================================
#                    INVESTMENT
# ============================================================

def create_investment(
    user_id,
    level
):

    if level not in INVESTMENT_LEVELS:

        return False, "INVALID_LEVEL"

    info = INVESTMENT_LEVELS[level]

    amount = info["amount"]

    if get_balance(user_id) < amount:

        return False, "LOW_BALANCE"

    started = datetime.now()

    finish = (
        started +
        timedelta(
            hours=info["hours"]
        )
    )

    conn = get_connection()

    conn.execute(
        """
        UPDATE users
        SET balance = ROUND(balance - ?, 8)
        WHERE user_id = ?
        """,
        (
            amount,
            user_id
        )
    )

    conn.execute(
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
        VALUES
        (?, ?, ?, ?, ?, ?, 'active')
        """,
        (
            user_id,
            level,
            amount,
            info["return"],
            started.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            finish.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )

    conn.commit()
    conn.close()

    return True, "SUCCESS"


# ============================================================
#                     WELCOME
# ============================================================

def welcome_keyboard():

    channel_url = get_setting(
        "channel_url",
        DEFAULT_CHANNEL_URL
    )

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚀 فتح البوت",
                web_app=WebAppInfo(
                    url=WEBAPP_URL
                )
            )
        ],
        [
            InlineKeyboardButton(
                "📢 القناة الرسمية",
                url=channel_url
            )
        ],
        [
            InlineKeyboardButton(
                "🆘 الدعم",
                url=f"https://t.me/{SUPPORT_USERNAME}"
            )
        ]
    ])


async def send_welcome(
    update,
    context
):

    image = get_setting(
        "welcome_image",
        DEFAULT_WELCOME_IMAGE
    )

    bot_name = get_setting(
        "bot_name",
        DEFAULT_BOT_NAME
    )

    text = (
        f"👋 أهلاً وسهلاً بك في {bot_name}\n\n"
        "💰 اكسب GRAM من المهام\n"
        "📢 أضف قناتك أو بوتك\n"
        "🎁 احصل على المكافآت\n"
        "💸 اسحب بعد إكمال شروط السحب"
    )

    keyboard = welcome_keyboard()

    try:

        await update.message.reply_photo(
            photo=image,
            caption=text,
            reply_markup=keyboard
        )

    except Exception as e:

        logger.error(
            "Welcome image error: %s",
            e
        )

        await update.message.reply_text(
            text,
            reply_markup=keyboard
        )


# ============================================================
#                         START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    user = get_user(user_id)

    if int(user["is_new"] or 0) == 1:

        await send_welcome(
            update,
            context
        )

        mark_user_not_new(user_id)

        return

    await update.message.reply_text(
        "👋 أهلاً بك مجددًا في GRAM MAX",
        reply_markup=welcome_keyboard()
    )


# ============================================================
#                 VERIFY CHANNEL TASK
# ============================================================

async def verify_task(
    user_id,
    task_source_id,
    context
):

    conn = get_connection()

    task = conn.execute(
        """
        SELECT *
        FROM task_sources
        WHERE id = ?
        AND status = 'active'
        """,
        (
            task_source_id,
        )
    ).fetchone()

    conn.close()

    if not task:

        return False, "TASK_NOT_FOUND"

    task_id = f"source_{task_source_id}"

    if is_task_completed(
        user_id,
        task_id
    ):

        return False, "ALREADY_COMPLETED"

    url = task["source_url"].rstrip("/")

    username = url.split("/")[-1]

    if username.startswith("@"):

        username = username[1:]

    if username.startswith("+"):

        return False, "PRIVATE_CHANNEL"

    try:

        member = await context.bot.get_chat_member(
            chat_id=f"@{username}",
            user_id=user_id
        )

        if member.status not in [
            "member",
            "administrator",
            "creator"
        ]:

            return False, "NOT_SUBSCRIBED"

    except Exception as e:

        logger.error(
            "Verification error: %s",
            e
        )

        return False, "BOT_NOT_ADMIN"

    reward = float(
        task["reward"]
    )

    completed = complete_task(
        user_id,
        task_id,
        reward
    )

    if not completed:

        return False, "ALREADY_COMPLETED"

    return True, reward


# ============================================================
#                  WEB APP DATA HANDLER
# ============================================================

async def web_app_data_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_message:

        return

    if not update.effective_message.web_app_data:

        return

    user_id = update.effective_user.id

    get_user(user_id)

    raw = update.effective_message.web_app_data.data

    try:

        data = json.loads(raw)

    except Exception:

        await update.message.reply_text(
            "ERROR:INVALID_JSON"
        )

        return

    action = data.get(
        "action",
        ""
    )

    # ========================================================
    # GET DATA
    # ========================================================

    if action == "get_data":

        user = get_user(user_id)

        response = {
            "type": "DATA",
            "balance": float(
                user["balance"] or 0
            ),
            "wallet": user["wallet_address"] or "",
            "language": user["language"] or "ar",
            "referrals": int(
                user["referrals"] or 0
            ),
            "completed_tasks":
                get_completed_task_count(
                    user_id
                ),
            "withdrawal_required":
                WITHDRAWAL_REQUIRED_TASKS,
            "deposit_wallet":
                get_setting(
                    "deposit_wallet",
                    DEFAULT_DEPOSIT_WALLET
                ),
        }

        await update.message.reply_text(
            json.dumps(
                response,
                ensure_ascii=False
            )
        )

        return

    # ========================================================
    # LINK WALLET
    # ========================================================

    if action == "link_wallet":

        wallet = str(
            data.get(
                "wallet",
                data.get(
                    "address",
                    ""
                )
            )
        ).strip()

        if not valid_wallet(wallet):

            await update.message.reply_text(
                "WALLET_FAIL"
            )

            return

        save_wallet(
            user_id,
            wallet
        )

        await update.message.reply_text(
            f"WALLET_LINKED:{wallet}"
        )

        return

    # ========================================================
    # CHANGE LANGUAGE
    # ========================================================

    if action == "change_lang":

        language = data.get(
            "lang",
            "ar"
        )

        if language not in [
            "ar",
            "en",
            "ru"
        ]:

            language = "ar"

        conn = get_connection()

        conn.execute(
            """
            UPDATE users
            SET language = ?
            WHERE user_id = ?
            """,
            (
                language,
                user_id
            )
        )

        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"LANG_CHANGED:{language}"
        )

        return

    # ========================================================
    # VERIFY TASK
    # ========================================================

    if action == "verify_task":

        try:

            task_id = int(
                data.get(
                    "task_id"
                )
            )

        except Exception:

            await update.message.reply_text(
                "TASK_FAIL:INVALID_TASK"
            )

            return

        success, result = await verify_task(
            user_id,
            task_id,
            context
        )

        if success:

            await update.message.reply_text(
                json.dumps({
                    "type": "TASK_DONE",
                    "task_id": task_id,
                    "reward": result,
                    "balance":
                        get_balance(
                            user_id
                        ),
                    "completed_tasks":
                        get_completed_task_count(
                            user_id
                        )
                })
            )

        else:

            await update.message.reply_text(
                json.dumps({
                    "type": "TASK_FAIL",
                    "task_id": task_id,
                    "result": result,
                    "balance":
                        get_balance(
                            user_id
                        )
                })
            )

        return

    # ========================================================
    # INVEST
    # ========================================================

    if action == "invest_start":

        try:

            level = int(
                data.get(
                    "level",
                    0
                )
            )

        except Exception:

            await update.message.reply_text(
                "INVEST_FAIL:INVALID_LEVEL"
            )

            return

        success, result = create_investment(
            user_id,
            level
        )

        if success:

            await update.message.reply_text(
                json.dumps({
                    "type": "INVEST_SUCCESS",
                    "balance":
                        get_balance(
                            user_id
                        )
                })
            )

        else:

            await update.message.reply_text(
                f"INVEST_FAIL:{result}"
            )

        return

    # ========================================================
    # DEPOSIT
    # ========================================================

    if action == "create_deposit":

        try:

            amount = float(
                data.get(
                    "amount",
                    0
                )
            )

        except Exception:

            await update.message.reply_text(
                "DEPOSIT_FAIL:INVALID_AMOUNT"
            )

            return

        tx_hash = str(
            data.get(
                "tx_hash",
                ""
            )
        ).strip()

        if amount <= 0:

            await update.message.reply_text(
                "DEPOSIT_FAIL:INVALID_AMOUNT"
            )

            return

        if not tx_hash:

            await update.message.reply_text(
                "DEPOSIT_FAIL:TX_REQUIRED"
            )

            return

        deposit_wallet = get_setting(
            "deposit_wallet",
            DEFAULT_DEPOSIT_WALLET
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
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
            VALUES
            (?, ?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                amount,
                deposit_wallet,
                tx_hash,
                now()
            )
        )

        deposit_id = cursor.lastrowid

        conn.commit()
        conn.close()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ قبول وإضافة الرصيد",
                    callback_data=
                        f"deposit_approve:{deposit_id}"
                ),
                InlineKeyboardButton(
                    "❌ رفض",
                    callback_data=
                        f"deposit_reject:{deposit_id}"
                )
            ]
        ])

        try:

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💰 طلب إيداع جديد\n\n"
                    f"🆔 DEP-{deposit_id:06d}\n"
                    f"👤 المستخدم: {user_id}\n"
                    f"💰 المبلغ: {amount} GRAM\n"
                    f"🔗 TX: {tx_hash}\n"
                    f"📥 محفظة المشروع:\n"
                    f"{deposit_wallet}"
                ),
                reply_markup=keyboard
            )

        except Exception as e:

            logger.error(
                "Admin deposit message error: %s",
                e
            )

        await update.message.reply_text(
            f"DEPOSIT_PENDING:{deposit_id}"
        )

        return

    # ========================================================
    # WITHDRAW
    # ========================================================

    if action == "create_withdrawal":

        completed = get_completed_task_count(
            user_id
        )

        if completed < WITHDRAWAL_REQUIRED_TASKS:

            await update.message.reply_text(
                json.dumps({
                    "type": "WITHDRAW_FAIL",
                    "reason":
                        "TASKS_REQUIRED",
                    "required":
                        WITHDRAWAL_REQUIRED_TASKS,
                    "completed":
                        completed
                })
            )

            return

        try:

            amount = float(
                data.get(
                    "amount",
                    0
                )
            )

        except Exception:

            await update.message.reply_text(
                "WITHDRAW_FAIL:INVALID_AMOUNT"
            )

            return

        if amount <= 0:

            await update.message.reply_text(
                "WITHDRAW_FAIL:INVALID_AMOUNT"
            )

            return

        wallet = get_wallet(
            user_id
        )

        if not valid_wallet(wallet):

            await update.message.reply_text(
                "WITHDRAW_FAIL:NO_WALLET"
            )

            return

        current_balance = get_balance(
            user_id
        )

        if amount > current_balance:

            await update.message.reply_text(
                "WITHDRAW_FAIL:LOW_BALANCE"
            )

            return

        # يتم حجز المبلغ عند إنشاء الطلب.
        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET balance = ROUND(balance - ?, 8)
            WHERE user_id = ?
            """,
            (
                amount,
                user_id
            )
        )

        cursor.execute(
            """
            INSERT INTO withdrawals
            (
                user_id,
                amount,
                wallet_address,
                status,
                created_at
            )
            VALUES
            (?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                amount,
                wallet,
                now()
            )
        )

        withdrawal_id = cursor.lastrowid

        conn.commit()
        conn.close()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💸 تم الدفع",
                    callback_data=
                        f"withdraw_paid:{withdrawal_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ رفض وإرجاع الرصيد",
                    callback_data=
                        f"withdraw_reject:{withdrawal_id}"
                )
            ]
        ])

        try:

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💸 طلب سحب جديد\n\n"
                    f"🆔 WD-{withdrawal_id:06d}\n"
                    f"👤 المستخدم: {user_id}\n"
                    f"💰 المبلغ: {amount} GRAM\n"
                    f"👛 المحفظة:\n{wallet}\n\n"
                    "⚠️ الدفع يتم يدويًا."
                ),
                reply_markup=keyboard
            )

        except Exception as e:

            logger.error(
                "Admin withdrawal error: %s",
                e
            )

        await update.message.reply_text(
            f"WITHDRAW_PENDING:{withdrawal_id}"
        )

        return

    # ========================================================
    # ADD CHANNEL
    # ========================================================

    if action == "add_channel":

        channel_url = str(
            data.get(
                "channel_url",
                data.get(
                    "url",
                    ""
                )
            )
        ).strip()

        if not channel_url.startswith(
            "https://t.me/"
        ):

            await update.message.reply_text(
                "CHANNEL_FAIL:INVALID_URL"
            )

            return

        if get_balance(user_id) < CHANNEL_ADD_PRICE:

            await update.message.reply_text(
                "CHANNEL_FAIL:LOW_BALANCE"
            )

            return

        # الخصم فعلي من الرصيد
        update_balance(
            user_id,
            -CHANNEL_ADD_PRICE
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO channel_requests
            (
                user_id,
                channel_url,
                price,
                status,
                created_at
            )
            VALUES
            (?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                channel_url,
                CHANNEL_ADD_PRICE,
                now()
            )
        )

        request_id = cursor.lastrowid

        conn.commit()
        conn.close()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ قبول القناة",
                    callback_data=
                        f"channel_approve:{request_id}"
                ),
                InlineKeyboardButton(
                    "❌ رفض وإرجاع الرصيد",
                    callback_data=
                        f"channel_reject:{request_id}"
                )
            ]
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "📢 طلب إضافة قناة\n\n"
                f"🆔 CH-{request_id:06d}\n"
                f"👤 المستخدم: {user_id}\n"
                f"🔗 {channel_url}\n"
                f"💰 السعر: {CHANNEL_ADD_PRICE} GRAM"
            ),
            reply_markup=keyboard
        )

        await update.message.reply_text(
            f"CHANNEL_PENDING:{request_id}"
        )

        return

    # ========================================================
    # ADD BOT
    # ========================================================

    if action == "add_bot":

        bot_url = str(
            data.get(
                "bot_url",
                data.get(
                    "url",
                    ""
                )
            )
        ).strip()

        if not bot_url.startswith(
            "https://t.me/"
        ):

            await update.message.reply_text(
                "BOT_FAIL:INVALID_URL"
            )

            return

        if get_balance(user_id) < BOT_ADD_PRICE:

            await update.message.reply_text(
                "BOT_FAIL:LOW_BALANCE"
            )

            return

        update_balance(
            user_id,
            -BOT_ADD_PRICE
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO bot_requests
            (
                user_id,
                bot_url,
                price,
                status,
                created_at
            )
            VALUES
            (?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                bot_url,
                BOT_ADD_PRICE,
                now()
            )
        )

        request_id = cursor.lastrowid

        conn.commit()
        conn.close()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ قبول البوت",
                    callback_data=
                        f"bot_approve:{request_id}"
                ),
                InlineKeyboardButton(
                    "❌ رفض وإرجاع الرصيد",
                    callback_data=
                        f"bot_reject:{request_id}"
                )
            ]
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🤖 طلب إضافة بوت\n\n"
                f"🆔 BOT-{request_id:06d}\n"
                f"👤 المستخدم: {user_id}\n"
                f"🔗 {bot_url}\n"
                f"💰 السعر: {BOT_ADD_PRICE} GRAM"
            ),
            reply_markup=keyboard
        )

        await update.message.reply_text(
            f"BOT_PENDING:{request_id}"
        )

        return

    # ========================================================
    # SUPPORT
    # ========================================================

    if action == "support":

        text = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        if not text:

            await update.message.reply_text(
                "SUPPORT_FAIL:EMPTY"
            )

            return

        try:

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "🆘 رسالة دعم\n\n"
                    f"👤 المستخدم: {user_id}\n\n"
                    f"💬 {text}\n\n"
                    f"👤 الدعم المباشر:\n"
                    f"https://t.me/{SUPPORT_USERNAME}"
                )
            )

        except Exception:
            pass

        await update.message.reply_text(
            "SUPPORT_SENT"
        )

        return

    await update.message.reply_text(
        "ERROR:UNKNOWN_ACTION"
    )


# ============================================================
#                    ADMIN CALLBACKS
# ============================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "غير مسموح.",
            show_alert=True
        )

        return

    await query.answer()

    data = query.data

    # ========================================================
    # DEPOSIT APPROVE
    # ========================================================

    if data.startswith(
        "deposit_approve:"
    ):

        deposit_id = int(
            data.split(":")[1]
        )

        conn = get_connection()

        deposit = conn.execute(
            """
            SELECT *
            FROM deposits
            WHERE id = ?
            """,
            (
                deposit_id,
            )
        ).fetchone()

        if not deposit:

            conn.close()

            await query.edit_message_text(
                "❌ الإيداع غير موجود."
            )

            return

        if deposit["status"] != "pending":

            conn.close()

            await query.edit_message_text(
                "⚠️ هذا الإيداع تمت معالجته مسبقًا."
            )

            return

        conn.execute(
            """
            UPDATE deposits
            SET status = 'approved',
                processed_at = ?
            WHERE id = ?
            AND status = 'pending'
            """,
            (
                now(),
                deposit_id
            )
        )

        conn.execute(
            """
            UPDATE users
            SET balance =
                ROUND(balance + ?, 8)
            WHERE user_id = ?
            """,
            (
                deposit["amount"],
                deposit["user_id"]
            )
        )

        conn.commit()
        conn.close()

        await query.edit_message_text(
            (
                f"✅ تم قبول الإيداع\n\n"
                f"🆔 DEP-{deposit_id:06d}\n"
                f"👤 {deposit['user_id']}\n"
                f"💰 +{deposit['amount']} GRAM"
            )
        )

        try:

            await context.bot.send_message(
                chat_id=deposit["user_id"],
                text=(
                    "✅ تم قبول إيداعك\n\n"
                    f"💰 تمت إضافة "
                    f"{deposit['amount']} GRAM "
                    "إلى رصيدك."
                )
            )

        except Exception:
            pass

        return

    # ========================================================
    # DEPOSIT REJECT
    # ========================================================

    if data.startswith(
        "deposit_reject:"
    ):

        deposit_id = int(
            data.split(":")[1]
        )

        conn = get_connection()

        deposit = conn.execute(
            """
            SELECT *
            FROM deposits
            WHERE id = ?
            """,
            (
                deposit_id,
            )
        ).fetchone()

        if not deposit:

            conn.close()

            return

        if deposit["status"] != "pending":

            conn.close()

            await query.edit_message_text(
                "⚠️ تمت معالجة الطلب مسبقًا."
            )

            return

        conn.execute(
            """
            UPDATE deposits
            SET status = 'rejected',
                processed_at = ?
            WHERE id = ?
            """,
            (
                now(),
                deposit_id
            )
        )

        conn.commit()
        conn.close()

        await query.edit_message_text(
            f"❌ تم رفض DEP-{deposit_id:06d}"
        )

        try:

            await context.bot.send_message(
                chat_id=deposit["user_id"],
                text="❌ تم رفض طلب الإيداع."
            )

        except Exception:
            pass

        return

    # ========================================================
    # WITHDRAW PAID
    # ========================================================

    if data.startswith(
        "withdraw_paid:"
    ):

        withdrawal_id = int(
            data.split(":")[1]
        )

        conn = get_connection()

        withdrawal = conn.execute(
            """
            SELECT *
            FROM withdrawals
            WHERE id = ?
            """,
            (
                withdrawal_id,
            )
        ).fetchone()

        if not withdrawal:

            conn.close()

            return

        if withdrawal["status"] != "pending":

            conn.close()

            await query.edit_message_text(
                "⚠️ تمت معالجة طلب السحب مسبقًا."
            )

            return

        conn.execute(
            """
            UPDATE withdrawals
            SET status = 'paid',
                processed_at = ?
            WHERE id = ?
            AND status = 'pending'
            """,
            (
                now(),
                withdrawal_id
            )
        )

        conn.commit()
        conn.close()

        await query.edit_message_text(
            (
                f"💸 تم تسجيل الدفع\n\n"
                f"🆔 WD-{withdrawal_id:06d}\n"
                f"👤 {withdrawal['user_id']}\n"
                f"💰 {withdrawal['amount']} GRAM\n"
                f"👛 {withdrawal['wallet_address']}"
            )
        )

        try:

            await context.bot.send_message(
                chat_id=withdrawal["user_id"],
                text=(
                    f"✅ تم دفع طلب السحب "
                    f"WD-{withdrawal_id:06d} يدويًا."
                )
            )

        except Exception:
            pass

        return

    # ========================================================
    # WITHDRAW REJECT + REFUND
    # ========================================================

    if data.startswith(
        "withdraw_reject:"
    ):

        withdrawal_id = int(
            data.split(":")[1]
        )

        conn = get_connection()

        withdrawal = conn.execute(
            """
            SELECT *
            FROM withdrawals
            WHERE id = ?
            """,
            (
                withdrawal_id,
            )
        ).fetchone()

       
