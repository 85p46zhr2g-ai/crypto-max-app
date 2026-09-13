import sqlite3
import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ضع توكن البوت هنا
BOT_TOKEN = "ضع_توكن_البوت_هنا"

MIN_DEPOSIT = 0.10
MIN_WITHDRAWAL = 1.00

logging.basicConfig(level=logging.INFO)

# قاعدة البيانات
db = sqlite3.connect("gram_max_demo.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    transaction_type TEXT,
    amount REAL,
    status TEXT,
    created_at TEXT
)
""")

db.commit()


def create_user(user_id, username):
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,)
    )

    if cursor.fetchone() is None:
        cursor.execute("""
        INSERT INTO users
        (user_id, username, balance, referrals, created_at)
        VALUES (?, ?, 0, 0, ?)
        """, (
            user_id,
            username or "",
            datetime.now().isoformat(timespec="seconds"),
        ))
        db.commit()


def get_user(user_id):
    cursor.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )
    return cursor.fetchone()


def save_transaction(user_id, transaction_type, amount, status):
    cursor.execute("""
    INSERT INTO transactions
    (user_id, transaction_type, amount, status, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        transaction_type,
        amount,
        status,
        datetime.now().isoformat(timespec="seconds"),
    ))
    db.commit()


# القائمة الرئيسية
MAIN_KEYBOARD = [
    ["💰 الاستثمار", "➕ الإيداع"],
    ["👥 دعوة الأصدقاء", "📊 المستويات"],
    ["📈 الإحصائيات", "💵 السحب"],
    ["🎁 المكافآت", "🆘 الدعم"],
    ["⚙️ الإعدادات"],
]


def main_keyboard():
    return ReplyKeyboardMarkup(
        MAIN_KEYBOARD,
        resize_keyboard=True
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        [["⬅️ القائمة الرئيسية"]],
        resize_keyboard=True
    )


# أمر Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username)

    context.user_data.clear()

    await update.message.reply_text(
        "🤖 أهلًا بك في GRAM MAX\n\n"
        "⚠️ هذه نسخة تجريبية فقط.\n"
        "لا توجد إيداعات أو سحوبات حقيقية.\n"
        "لا ترسل أي أموال إلى أي عنوان.\n\n"
        "اختر من القائمة:",
        reply_markup=main_keyboard()
    )


# الاستثمار
async def investment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 الاستثمار التجريبي\n\n"
        "المستوى 1: 1 GRAM — مدة تجريبية 12 ساعة\n"
        "المستوى 2: 2 GRAM — مدة تجريبية 24 ساعة\n"
        "المستوى 3: 5 GRAM — مدة تجريبية 3 أيام\n"
        "المستوى 4: 7 GRAM — مدة تجريبية 48 ساعة\n"
        "المستوى 5: 10 GRAM — مدة تجريبية 5 أيام\n\n"
        "هذه الأرقام للعرض والمحاكاة فقط.",
        reply_markup=back_keyboard()
    )


# الإيداع التجريبي
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_for_deposit"] = True
    context.user_data["waiting_for_withdrawal"] = False

    await update.message.reply_text(
        "➕ الإيداع التجريبي\n\n"
        f"الحد الأدنى للإيداع: {MIN_DEPOSIT:.2f} GRAM\n\n"
        "أرسل المبلغ الذي تريد إضافته.\n"
        "مثال: 1",
        reply_markup=back_keyboard()
    )


# السحب التجريبي
async def withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    context.user_data["waiting_for_withdrawal"] = True
    context.user_data["waiting_for_deposit"] = False

    await update.message.reply_text(
        "💵 السحب التجريبي\n\n"
        f"رصيدك الحالي: {user[2]:.2f} GRAM\n"
        f"الحد الأدنى للسحب: {MIN_WITHDRAWAL:.2f} GRAM\n\n"
        "أرسل المبلغ المطلوب.\n"
        "لن يتم تحويل أي أموال حقيقية.",
        reply_markup=back_keyboard()
    )


# الإحصائيات
async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    await update.message.reply_text(
        "📈 الإحصائيات\n\n"
        f"💰 الرصيد التجريبي: {user[2]:.2f} GRAM\n"
        f"👥 عدد الإحالات: {user[3]}\n"
        "🔄 الاستثمارات النشطة: 0\n"
        "✅ الاستثمارات المنتهية: 0",
        reply_markup=back_keyboard()
    )


# المستويات
async def levels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 المستويات\n\n"
        "✅ المستوى 1 — متاح تجريبيًا\n"
        "🔒 المستوى 2 — يحتاج رصيدًا تجريبيًا\n"
        "🔒 المستوى 3 — يحتاج رصيدًا تجريبيًا\n"
        "🔒 المستوى 4 — يحتاج رصيدًا تجريبيًا\n"
        "🔒 المستوى 5 — يحتاج رصيدًا تجريبيًا",
        reply_markup=back_keyboard()
    )


# الإحالات
async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    bot_username = context.bot.username or "YourBot"

    link = f"https://t.me/{bot_username}?start=ref_{user[0]}"

    await update.message.reply_text(
        "👥 دعوة الأصدقاء\n\n"
        f"رابط الإحالة التجريبي:\n{link}\n\n"
        f"عدد الإحالات: {user[3]}\n"
        "الإحالات هنا تجريبية فقط ولا توجد عمولات مالية.",
        reply_markup=back_keyboard()
    )


# المكافآت
async def rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎁 المكافآت\n\n"
        "🎉 مكافأة التسجيل: تجريبية\n"
        "👥 مكافآت الإحالات: تجريبية\n"
        "⭐ مكافآت إضافية: تجريبية\n\n"
        "لا يمكن تحويل المكافآت إلى أموال.",
        reply_markup=back_keyboard()
    )


# الدعم
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 الدعم\n\n"
        "هذه نسخة تجريبية من البوت.\n"
        "لا توجد عمليات تحويل أو سحب حقيقية.\n"
        "لا ترسل أموالًا إلى أي عنوان.",
        reply_markup=back_keyboard()
    )


# الإعدادات
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ الإعدادات\n\n"
        "🔔 الإشعارات: مفعلة\n"
        "🌐 اللغة: العربية\n"
        "ℹ️ نوع الحساب: تجريبي",
        reply_markup=back_keyboard()
    )


# معالجة الأرقام للإيداع والسحب
async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")

    try:
        amount = float(text)
    except ValueError:
        return

    user_id = update.effective_user.id

    # إيداع تجريبي
    if context.user_data.get("waiting_for_deposit"):
        context.user_data["waiting_for_deposit"] = False

        if amount < MIN_DEPOSIT:
            await update.message.reply_text(
                f"❌ الحد الأدنى للإيداع هو {MIN_DEPOSIT:.2f} GRAM"
            )
            return

        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        db.commit()

        save_transaction(
            user_id,
            "demo_deposit",
            amount,
            "completed"
        )

        await update.message.reply_text(
            f"✅ تمت إضافة {amount:.2f} GRAM إلى رصيدك التجريبي.\n"
            "لا يوجد أي تحويل حقيقي.",
            reply_markup=main_keyboard()
        )
        return

    # سحب تجريبي
    if context.user_data.get("waiting_for_withdrawal"):
        context.user_data["waiting_for_withdrawal"] = False

        user = get_user(user_id)
        balance = user[2]

        if amount < MIN_WITHDRAWAL:
            await update.message.reply_text(
                f"❌ الحد الأدنى للسحب هو {MIN_WITHDRAWAL:.2f} GRAM"
            )
            return

        if amount > balance:
            await update.message.reply_text(
                "❌ رصيدك التجريبي غير كافٍ."
            )
            return

        cursor.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (amount, user_id)
        )
        db.commit()

        save_transaction(
            user_id,
            "demo_withdrawal",
            amount,
            "pending"
        )

        await update.message.reply_text(
            f"✅ تم تسجيل طلب سحب تجريبي بقيمة {amount:.2f} GRAM.\n"
            "الحالة: قيد الاختبار.\n"
            "لن يتم إرسال أي أموال.",
            reply_markup=main_keyboard()
        )


# معالجة أزرار القائمة
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💰 الاستثمار":
        await investment(update, context)

    elif text == "➕ الإيداع":
        await deposit(update, context)

    elif text == "👥 دعوة الأصدقاء":
        await referrals(update, context)

    elif text == "📊 المستويات":
        await levels(update, context)

    elif text == "📈 الإحصائيات":
        await statistics(update, context)

    elif text == "💵 السحب":
        await withdrawal(update, context)

    elif text == "🎁 المكافآت":
        await rewards(update, context)

    elif text == "🆘 الدعم":
        await support(update, context)

    elif text == "⚙️ الإعدادات":
        await settings(update, context)

    elif text == "⬅️ القائمة الرئيسية":
        context.user_data.clear()

        await update.message.reply_text(
            "اختر من القائمة الرئيسية:",
            reply_markup=main_keyboard()
        )

    else:
        await handle_number(update, context)


# تشغيل البوت
def main():
    if BOT_TOKEN == "ضع_توكن_البوت_هنا":
        print("ضع توكن البوت أولًا داخل BOT_TOKEN")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            button_handler
        )
    )

    print("GRAM MAX Demo is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
