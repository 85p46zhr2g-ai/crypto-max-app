import logging
import sqlite3
import json
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
# ===================== إعدادات البوت =========================
# ============================================================

# ⚠️ ضع التوكن الجديد هنا بعد تغييره من BotFather
BOT_TOKEN = "8724497887:AAE02WdKwwMWaXzXmRlsVUiYjPqjVfVR5LI"

# ID الأدمن
ADMIN_ID = 8183652969

# اسم مستخدم البوت بدون @
BOT_USERNAME = "GramMax1_Bot"

# رابط الـ Mini App
WEBAPP_URL = "https://85p46zhr2g-ai.github.io/crypto-max-app/"

# القناة الرسمية
DEFAULT_CHANNEL_URL = "https://t.me/CRYBTO_MAX_1"

# اسم البوت الظاهر للمستخدم
DEFAULT_BOT_NAME = "GRAM MAX"

# صورة الترحيب
DEFAULT_WELCOME_IMAGE = "https://i.ibb.co/6PqZ8XK/welcome.jpg"

# مكافأة المهمة
TASK_REWARD = 0.01

# أسعار إضافة قناة / بوت
CHANNEL_ADD_PRICE_USD = 1.00
BOT_ADD_PRICE_USD = 0.30

# عملة المستخدم الداخلية
CURRENCY = "GRAM"

# ============================================================
# ======================= Logging =============================
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ============================================================
# ======================== قاعدة البيانات ======================
# ============================================================

DB_NAME = "gram_max.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # المستخدمين
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

    # المهام
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

    # الإعدادات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # طلبات الإيداع
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            wallet_address TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT
        )
    """)

    # طلبات السحب
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            wallet_address TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT
        )
    """)

    # الاستثمارات
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

    # طلبات إضافة القنوات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_url TEXT NOT NULL,
            price REAL DEFAULT 1.0,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    # طلبات إضافة البوتات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bot_url TEXT NOT NULL,
            price REAL DEFAULT 0.30,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    # حفظ الإعدادات الافتراضية
    defaults = {
        "channel_url": DEFAULT_CHANNEL_URL,
        "welcome_image": DEFAULT_WELCOME_IMAGE,
        "bot_name": DEFAULT_BOT_NAME,
    }

    for key, value in defaults.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO settings (key, value)
            VALUES (?, ?)
            """,
            (key, value)
        )

    conn.commit()
    conn.close()


# ============================================================
# ======================= Settings ============================
# ============================================================

def get_setting(key, default=""):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    )

    result = cursor.fetchone()
    conn.close()

    return result["value"] if result else default


def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO settings (key, value)
        VALUES (?, ?)
        """,
        (key, value)
    )

    conn.commit()
    conn.close()


# ============================================================
# ======================= المستخدمين ==========================
# ============================================================

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    if not row:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """
            INSERT INTO users
            (
                user_id,
                balance,
                referrals,
                wallet_address,
                language,
                notified,
                is_new,
                created_at
            )
            VALUES (?, 0, 0, NULL, 'ar', 0, 1, ?)
            """,
            (user_id, now)
        )

        conn.commit()

        cursor.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )

        row = cursor.fetchone()

    conn.close()
    return row


def mark_user_not_new(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET is_new = 0
        WHERE user_id = ?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()


def update_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE user_id = ?
        """,
        (amount, user_id)
    )

    conn.commit()
    conn.close()


def set_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET balance = ?
        WHERE user_id = ?
        """,
        (amount, user_id)
    )

    conn.commit()
    conn.close()


def get_balance(user_id):
    user = get_user(user_id)
    return float(user["balance"] or 0)


# ============================================================
# ======================== المحفظة =============================
# ============================================================

def save_wallet(user_id, wallet_address):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET wallet_address = ?
        WHERE user_id = ?
        """,
        (wallet_address, user_id)
    )

    conn.commit()
    conn.close()


def get_wallet(user_id):
    user = get_user(user_id)
    return user["wallet_address"]


def valid_wallet(address):
    if not address:
        return False

    address = address.strip()

    return (
        address.startswith("EQ")
        or address.startswith("UQ")
    )


# ============================================================
# ========================= المهام =============================
# ============================================================

CHANNEL_TASKS = {
    "task1": {
        "channel_id": "@CRYBTO_MAX_1",
        "channel_url": "https://t.me/CRYBTO_MAX_1",
        "name": "📢 CRYPTO MAX",
        "reward": 0.01,
    },
    "task2": {
        "channel_id": "@olka_ad",
        "channel_url": "https://t.me/olka_ad",
        "name": "📢 OLKA AD",
        "reward": 0.01,
    },
}


def is_task_completed(user_id, task_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM user_tasks
        WHERE user_id = ? AND task_id = ?
        """,
        (user_id, task_id)
    )

    result = cursor.fetchone()
    conn.close()

    return result is not None


def mark_task_completed(user_id, task_id, reward):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
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
                user_id,
                task_id,
                reward,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        conn.commit()

    except sqlite3.IntegrityError:
        pass

    conn.close()


def get_completed_tasks(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT task_id
        FROM user_tasks
        WHERE user_id = ?
        """,
        (user_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    return [row["task_id"] for row in rows]


# ============================================================
# ====================== الاستثمار =============================
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


def create_investment(user_id, level, amount):
    if level not in INVESTMENT_LEVELS:
        return False, "INVALID_LEVEL"

    level_data = INVESTMENT_LEVELS[level]

    if amount < level_data["amount"]:
        return False, "LOW_AMOUNT"

    balance = get_balance(user_id)

    if balance < amount:
        return False, "LOW_BALANCE"

    started = datetime.now()
    finish = started + timedelta(hours=level_data["hours"])

    # خصم الاستثمار
    update_balance(user_id, -amount)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
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
            amount,
            level_data["return"],
            started.strftime("%Y-%m-%d %H:%M:%S"),
            finish.strftime("%Y-%m-%d %H:%M:%S"),
        )
    )

    conn.commit()
    conn.close()

    return True, "SUCCESS"


# ============================================================
# ========================= الترحيب =============================
# ============================================================

async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    user = get_user(user_id)

    bot_name = get_setting(
        "bot_name",
        DEFAULT_BOT_NAME
    )

    welcome_image = get_setting(
        "welcome_image",
        DEFAULT_WELCOME_IMAGE
    )

    channel_url = get_setting(
        "channel_url",
        DEFAULT_CHANNEL_URL
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 فتح البوت",
                web_app={"url": WEBAPP_URL}
            )
        ],
        [
            InlineKeyboardButton(
                "📢 القناة الرسمية",
                url=channel_url
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"👋 أهلاً وسهلاً بك في بوت {bot_name}\n\n"
        f"🎉 أهلاً بك معنا!\n"
        f"استمتع بالخدمات والمهام والمميزات الموجودة داخل البوت."
    )

    # إرسال الصورة
    try:
        await update.message.reply_photo(
            photo=welcome_image,
            caption=welcome_text,
            reply_markup=reply_markup
        )

    except Exception as error:
        logger.error(
            "Welcome image error: %s",
            error
        )

        # إذا فشلت الصورة، لا يتوقف البوت
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )

    # تعليم المستخدم أنه دخل سابقاً
    mark_user_not_new(user_id)

    # إشعار الأدمن
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🔔 مستخدم جديد\n\n"
                f"👤 {user_name}\n"
                f"🆔 {user_id}"
            )
        )

    except Exception as error:
        logger.error(
            "Admin notification error: %s",
            error
        )


# ============================================================
# =========================== /start ===========================
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    user = get_user(user_id)

    is_new = int(user["is_new"] or 0)

    # المستخدم الجديد
    if is_new == 1:
        await send_welcome(
            update,
            context
        )
        return

    # المستخدم القديم
    channel_url = get_setting(
        "channel_url",
        DEFAULT_CHANNEL_URL
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 فتح البوت",
                web_app={"url": WEBAPP_URL}
            )
        ],
        [
            InlineKeyboardButton(
                "📢 القناة الرسمية",
                url=channel_url
            )
        ]
    ]

    await update.message.reply_text(
        (
            f"👋 أهلاً بك مجدداً {user_name}!\n\n"
            "استخدم الزر أدناه لفتح التطبيق:"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# ======================= التحقق من المهام =====================
# ============================================================

async def verify_task(
    user_id,
    task_id,
    context
):
    if task_id not in CHANNEL_TASKS:
        return False, "INVALID_TASK"

    if is_task_completed(
        user_id,
        task_id
    ):
        return True, "ALREADY"

    task = CHANNEL_TASKS[task_id]

    try:
        member = await context.bot.get_chat_member(
            chat_id=task["channel_id"],
            user_id=user_id
        )

        if member.status in [
            "member",
            "administrator",
            "creator"
        ]:
            reward = float(task["reward"])

            mark_task_completed(
                user_id,
                task_id,
                reward
            )

            update_balance(
                user_id,
                reward
            )

            return True, "SUCCESS"

        return False, "NOT_SUBSCRIBED"

    except Exception as error:
        logger.error(
            "Task verification error: %s",
            error
        )

        return False, "ERROR"


# ============================================================
# ======================= Web App Data =========================
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

    raw_data = update.effective_message.web_app_data.data

    try:
        data = json.loads(raw_data)
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
    # جلب البيانات
    # ========================================================

    if action == "get_data":

        user = get_user(user_id)

        balance = float(
            user["balance"] or 0
        )

        referrals = int(
            user["referrals"] or 0
        )

        wallet = (
            user["wallet_address"]
            or ""
        )

        language = (
            user["language"]
            or "ar"
        )

        completed = get_completed_tasks(
            user_id
        )

        response = {
            "type": "DATA",
            "balance": balance,
            "referrals": referrals,
            "wallet": wallet,
            "language": language,
            "completed_tasks": completed,
        }

        await update.message.reply_text(
            json.dumps(
                response,
                ensure_ascii=False
            )
        )

        return

    # ========================================================
    # ربط المحفظة
    # ========================================================

    if action == "link_wallet":

        address = str(
            data.get(
                "address",
                ""
            )
        ).strip()

        if not valid_wallet(address):
            await update.message.reply_text(
                "WALLET_FAIL"
            )
            return

        save_wallet(
            user_id,
            address
        )

        # إشعار الأدمن
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "👛 تم ربط محفظة جديدة\n\n"
                    f"🆔 المستخدم: {user_id}\n"
                    f"💳 المحفظة: {address}"
                )
            )
        except Exception:
            pass

        await update.message.reply_text(
            f"WALLET_LINKED:{address}"
        )

        return

    # ========================================================
    # تغيير اللغة
    # ========================================================

    if action == "change_lang":

        lang = data.get(
            "lang",
            "ar"
        )

        if lang not in [
            "ar",
            "en",
            "ru"
        ]:
            lang = "ar"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET language = ?
            WHERE user_id = ?
            """,
            (
                lang,
                user_id
            )
        )

        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"LANG_CHANGED:{lang}"
        )

        return

    # ========================================================
    # التحقق من المهمة
    # ========================================================

    if action == "verify_task":

        task_id = data.get(
            "task_id",
            ""
        )

        success, result = await verify_task(
            user_id,
            task_id,
            context
        )

        balance = get_balance(
            user_id
        )

        if success:

            await update.message.reply_text(
                json.dumps(
                    {
                        "type": "TASK_DONE",
                        "task_id": task_id,
                        "result": result,
                        "balance": balance,
                    }
                )
            )

        else:

            await update.message.reply_text(
                json.dumps(
                    {
                        "type": "TASK_FAIL",
                        "task_id": task_id,
                        "result": result,
                        "balance": balance,
                    }
                )
            )

        return

    # ========================================================
    # بدء الاستثمار
    # ========================================================

    if action == "invest_start":

        try:
            level = int(
                data.get(
                    "level",
                    1
                )
            )

            amount = float(
                data.get(
                    "amount",
                    0
                )
            )

        except Exception:
            await update.message.reply_text(
                "INVEST_FAIL:INVALID_DATA"
            )
            return

        success, result = create_investment(
            user_id,
            level,
            amount
        )

        if success:

            balance = get_balance(
                user_id
            )

            await update.message.reply_text(
                json.dumps(
                    {
                        "type": "INVEST_SUCCESS",
                        "level": level,
                        "balance": balance,
                    }
                )
            )

        else:

            await update.message.reply_text(
                f"INVEST_FAIL:{result}"
            )

        return

    # ========================================================
    # إيداع
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

        if amount <= 0:
            await update.message.reply_text(
                "DEPOSIT_FAIL:INVALID_AMOUNT"
            )
            return

        wallet = get_wallet(
            user_id
        )

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
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
                status,
                created_at
            )
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                amount,
                wallet,
                now
            )
        )

        deposit_id = cursor.lastrowid

        conn.commit()
        conn.close()

        # إشعار الأدمن
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💰 طلب إيداع جديد\n\n"
                    f"🆔 الطلب: #{deposit_id}\n"
                    f"👤 المستخدم: {user_id}\n"
                    f"💰 المبلغ: {amount} GRAM\n"
                    f"💳 المحفظة: {wallet or 'غير مربوطة'}"
                )
            )
        except Exception:
            pass

        await update.message.reply_text(
            f"DEPOSIT_CREATED:{deposit_id}"
        )

        return

    # ========================================================
    # سحب
    # ========================================================

    if action == "create_withdrawal":

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

        balance = get_balance(
            user_id
        )

        if amount > balance:
            await update.message.reply_text(
                "WITHDRAW_FAIL:LOW_BALANCE"
            )
            return

        wallet = get_wallet(
            user_id
        )

        if not wallet:
            await update.message.reply_text(
                "WITHDRAW_FAIL:NO_WALLET"
            )
            return

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        conn = get_connection()
        cursor = conn.cursor()

        # حجز المبلغ
        cursor.execute(
            """
            UPDATE users
            SET balance = balance - ?
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
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                amount,
                wallet,
                now
            )
        )

        withdrawal_id = cursor.lastrowid

        conn.commit()
        conn.close()

        # إشعار الأدمن
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💵 طلب سحب جديد\n\n"
                    f"🆔 الطلب: #{withdrawal_id}\n"
                    f"👤 المستخدم: {user_id}\n"
                    f"💰 المبلغ: {amount} GRAM\n"
                    f"💳 المحفظة: {wallet}"
                )
            )
        except Exception:
            pass

        await update.message.reply_text(
            f"WITHDRAW_CREATED:{withdrawal_id}"
        )

        return

    # ========================================================
    # طلب إضافة قناة
    # ========================================================

    if action == "add_channel":

        channel_url = str(
            data.get(
                "channel_url",
                ""
            )
        ).strip()

        if not channel_url.startswith(
            "https://t.me/"
        ):
            await update.message.reply_text(
                "CHANNEL_FAIL:INVALID_URL"
            )
            return

        balance = get_balance(
            user_id
        )

        price = CHANNEL_ADD_PRICE_USD

        if balance < price:
            await update.message.reply_text(
                "CHANNEL_FAIL:LOW_BALANCE"
            )
            return

        # الخصم بعد قبول الطلب
        update_balance(
            user_id,
            -price
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
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                channel_url,
                price,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        request_id = cursor.lastrowid

        conn.commit()
        conn.close()

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "📢 طلب إضافة قناة جديد\n\n"
                    f"🆔 الطلب: #{request_id}\n"
                    f"👤 المستخدم: {user_id}\n"
                    f"🔗 القناة: {channel_url}\n"
                    f"💵 السعر: ${price}"
                )
            )
        except Exception:
            pass

        await update.message.reply_text(
            f"CHANNEL_CREATED:{request_id}"
        )

        return

    # ========================================================
    # طلب إضافة بوت
    # ========================================================

    if action == "add_bot":

        bot_url = str(
            data.get(
                "bot_url",
                ""
            )
        ).strip()

        if not bot_url.startswith(
            "https://t.me/"
        ):
            await update.message.reply_text(
                "BOT_FAIL:INVALID_URL"
            )
            return

        balance = get_balance(
            user_id
        )

        price = BOT_ADD_PRICE_USD

        if balance < price:
            await update.message.reply_text(
                "BOT_FAIL:LOW_BALANCE"
            )
            return

        update_balance(
            user_id,
            -price
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
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                bot_url,
                price,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        request_id = cursor.lastrowid

        conn.commit()
        conn.close()

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "🤖 طلب إضافة بوت جديد\n\n"
                    f"🆔 الطلب: #{request_id}\n"
                    f"👤 المستخدم: {user_id}\n"
                    f"🔗 البوت: {bot_url}\n"
                    f"💵 السعر: ${price}"
                )
            )
        except Exception:
            pass

        await update.message.reply_text(
            f"BOT_CREATED:{request_id}"
        )

        return

    # ========================================================
    # دعم
    # ========================================================

    if action == "support":

        message = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        if not message:
            await update.message.reply_text(
                "SUPPORT_FAIL:EMPTY"
            )
            return

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "🆘 رسالة دعم جديدة\n\n"
                    f"👤 المستخدم: {user_id}\n\n"
                    f"💬 الرسالة:\n{message}"
                )
            )
        except Exception:
            pass

        await update.message.reply_text(
            "SUPPORT_SENT"
        )

        return

    # ========================================================
    # إجراء غير معروف
    # ========================================================

    await update.message.reply_text(
        "ERROR:UNKNOWN_ACTION"
    )


# ============================================================
# ====================== أوامر الأدمن =========================
# ============================================================

async def set_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "استخدم:\n/set_channel https://t.me/..."
        )
        return

    url = context.args[0]

    if not url.startswith(
        "https://t.me/"
    ):
        await update.message.reply_text(
            "❌ الرابط غير صحيح."
        )
        return

    set_setting(
        "channel_url",
        url
    )

    await update.message.reply_text(
        "✅ تم تحديث القناة الرسمية."
    )


async def set_welcome_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "استخدم:\n/set_welcome_image https://..."
        )
        return

    url = context.args[0]

    if not url.startswith(
        "http"
    ):
        await update.message.reply_text(
            "❌ رابط الصورة غير صحيح."
        )
        return

    set_setting(
        "welcome_image",
        url
    )

    await update.message.reply_text(
        "✅ تم تحديث صورة الترحيب."
    )


async def set_bot_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "استخدم:\n/set_bot_name GRAM MAX"
        )
        return

    name = " ".join(
        context.args
    )

    set_setting(
        "bot_name",
        name
    )

    await update.message.reply_text(
        f"✅ تم تحديث اسم البوت إلى: {name}"
    )


async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    text = (
        "👑 لوحة الأدمن\n\n"
        "الأوامر:\n\n"
        "/set_channel [الرابط]\n"
        "/set_welcome_image [الرابط]\n"
        "/set_bot_name [الاسم]\n\n"
        f"📢 القناة:\n"
        f"{get_setting('channel_url', DEFAULT_CHANNEL_URL)}\n\n"
        f"🖼 الصورة:\n"
        f"{get_setting('welcome_image', DEFAULT_WELCOME_IMAGE)}\n\n"
        f"🤖 الاسم:\n"
        f"{get_setting('bot_name', DEFAULT_BOT_NAME)}"
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# ============================ MAIN ===========================
# ============================================================

def main():

    init_db()

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # لوحة الأدمن
    application.add_handler(
        CommandHandler(
            "admin",
            admin_panel
        )
    )

    # إعداد القناة
    application.add_handler(
        CommandHandler(
            "set_channel",
            set_channel
        )
    )

    # إعداد صورة الترحيب
    application.add_handler(
        CommandHandler(
            "set_welcome_image",
            set_welcome_image
        )
    )

    # إعداد اسم البوت
    application.add_handler(
        CommandHandler(
            "set_bot_name",
            set_bot_name
        )
    )

    # استقبال بيانات الـMini App
    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            web_app_data_handler
        )
    )

    print("===================================")
    print("       GRAM MAX BOT")
    print("       BOT IS RUNNING")
    print("===================================")

    application.run_polling()


if __name__ == "__main__":
    main()
