import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# ⚠️ التوكن الخاص بك
BOT_TOKEN = "8724497887:AAGhZ-bTsoHkRcPBiUXlzSisEz08RklX3Bw"

# ⚠️ معرفك الرقمي كمدير
ADMIN_ID = 8183652969

# ⚠️ عنوان محفظتك
WALLET_ADDRESS = "UQBrfxfxzB5-op8FGLs-BxnZg0Bv0CveJ8VJbC3Xc9pVXZ5X"

# إعدادات التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==================== قاعدة البيانات ====================
def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            referrals INTEGER DEFAULT 0
        )
    """)
    # جدول الاستثمارات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            profit REAL,
            start_time TEXT,
            end_time TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    # جدول طلبات السحب
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            wallet_address TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    conn.commit()
    conn.close()

# دوال مساعدة
def get_user(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, referrals FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (user_id, balance, referrals) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        result = (0, 0)
    conn.close()
    return result

def update_balance(user_id, amount):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ==================== أوامر المستخدم ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)
    keyboard = [
        ["💰 الاستثمار", "👥 دعوة الأصدقاء"],
        ["📊 المستويات", "📈 الإحصائيات"],
        ["💵 السحب", "🎁 المكافآت"],
        ["🆘 الدعم", "⚙️ الإعدادات"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "مرحباً بك في بوت GRAM MAX! 🤖\nاختر من القائمة أدناه:",
        reply_markup=reply_markup
    )

async def invest_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💰 **قسم الاستثمار**\n\n"
        "اختر المستوى المناسب لك:\n"
        "1️⃣ المستوى 1: 1 GRAM ➜ 1.15 GRAM (12 ساعة)\n"
        "2️⃣ المستوى 2: 2 GRAM ➜ 2.20 GRAM (24 ساعة)\n"
        "3️⃣ المستوى 3: 5 GRAM ➜ 5.70 GRAM (48 ساعة)\n"
        "4️⃣ المستوى 4: 7 GRAM ➜ 8.30 GRAM (3 أيام)\n"
        "5️⃣ المستوى 5: 10 GRAM ➜ 13 GRAM (5 أيام)\n\n"
        "للبدء، قم بتحويل المبلغ إلى المحفظة التالية:\n"
        f"`{WALLET_ADDRESS}`\n\n"
        "بعد التحويل، اضغط على زر (✅ لقد قمت بالتحويل) وسيتم مراجعة طلبك."
    )
    keyboard = [[InlineKeyboardButton("✅ لقد قمت بالتحويل", callback_data="confirm_payment")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

# ==================== لوحة تحكم المشرف ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("عذراً، هذا الأمر للمشرف فقط.")
        return
    await update.message.reply_text("👑 **لوحة تحكم المشرف**\n\nالأوامر المتاحة:\n/pending_investments - عرض الاستثمارات المعلقة\n/pending_withdrawals - عرض طلبات السحب المعلقة")

async def pending_investments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, profit, end_time FROM investments WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("لا توجد استثمارات معلقة حالياً.")
        return
    for row in rows:
        inv_id, user_id, amount, profit, end_time = row
        text = f"📌 استثمار رقم: {inv_id}\n👤 المستخدم: `{user_id}`\n💰 المبلغ: {amount}\n📈 الربح: {profit}\n⏰ وقت الانتهاء: {end_time}"
        keyboard = [[
            InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_inv_{inv_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_inv_{inv_id}")
        ]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==================== معالجة الأزرار ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💰 الاستثمار":
        await invest_menu(update, context)
    elif text == "💵 السحب":
        await update.message.reply_text("💵 قسم السحب قيد التطوير حالياً.")
    elif text == "👥 دعوة الأصدقاء":
        await update.message.reply_text("👥 رابط الإحالة الخاص بك: (قيد التطوير)")
    else:
        await update.message.reply_text(f"لقد ضغطت على: {text}\n(هذا القسم قيد التطوير)")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "confirm_payment":
        await query.edit_message_text("✅ تم استلام طلبك! سيتم مراجعته من قبل الإدارة قريباً.")
        # إشعار المشرف
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب استثمار جديد من المستخدم `{query.from_user.id}`. يرجى مراجعة المحفظة.")
    elif data.startswith("confirm_inv_"):
        inv_id = int(data.split("_")[2])
        conn = sqlite3.connect("gram_max.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, profit FROM investments WHERE id = ?", (inv_id,))
        row = cursor.fetchone()
        if row:
            user_id, profit = row
            update_balance(user_id, profit)
            cursor.execute("UPDATE investments SET status = 'completed' WHERE id = ?", (inv_id,))
            conn.commit()
            await context.bot.send_message(chat_id=user_id, text=f"🎉 تم تأكيد استثمارك رقم {inv_id}! تمت إضافة الربح إلى رصيدك.")
            await query.edit_message_text(f"✅ تم تأكيد الاستثمار رقم {inv_id}.")
        conn.close()
    elif data.startswith("reject_inv_"):
        inv_id = int(data.split("_")[2])
        conn = sqlite3.connect("gram_max.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE investments SET status = 'cancelled' WHERE id = ?", (inv_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"❌ تم رفض الاستثمار رقم {inv_id}.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("pending_investments", pending_investments))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
