import logging
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

BOT_TOKEN = "8724497887:AAEmhudPVYMApgfakZT_T2X_r61dcTJuemc"
ADMIN_ID = 8183652969
WALLET_ADDRESS = "UQBrfxfxzB5-op8FGLs-BxnZg0Bv0CveJ8VJbC3Xc9pVXZ5X"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending', created_at TEXT)")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        conn.commit()
        result = (0,)
    conn.close()
    return result[0]

def update_balance(user_id, amount):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def create_deposit(user_id, amount):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO deposits (user_id, amount, status, created_at) VALUES (?, ?, 'pending', ?)", 
                   (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_pending_deposits():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, created_at FROM deposits WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return rows

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)
    keyboard = [["💰 الاستثمار", "👥 دعوة الأصدقاء"], ["📊 المستويات", "📈 الإحصائيات"], ["💵 السحب", "💳 الإيداع"], ["🎁 المكافآت", "🆘 الدعم"], ["⚙️ الإعدادات"]]
    await update.message.reply_text("مرحباً بك في GRAM MAX! 🤖", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def invest_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💰 الاستثمار\n\n1️⃣ 1 GRAM ➜ 1.15 (12 ساعة)\n2️⃣ 2 GRAM ➜ 2.20 (24 ساعة)\n3️⃣ 5 GRAM ➜ 5.70 (48 ساعة)\n4️⃣ 7 GRAM ➜ 8.30 (3 أيام)\n5️⃣ 10 GRAM ➜ 13 (5 أيام)\n\nقم بالتحويل إلى:\n`" + WALLET_ADDRESS + "`"
    keyboard = [[InlineKeyboardButton("✅ تم الإيداع", callback_data="confirm_deposit")]]
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💳 الإيداع\n\nقم بالتحويل إلى:\n`" + WALLET_ADDRESS + "`"
    keyboard = [[InlineKeyboardButton("✅ تم الإيداع", callback_data="confirm_deposit")]]
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("👑 لوحة التحكم\n/pending_deposits - طلبات الإيداع")

async def pending_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    rows = get_pending_deposits()
    if not rows:
        await update.message.reply_text("لا توجد طلبات.")
        return
    for row in rows:
        dep_id, user_id, amount, created_at = row
        text = f"📌 طلب إيداع رقم: {dep_id}\n👤 المستخدم: `{user_id}`\n💰 المبلغ: {amount}\n⏰ الوقت: {created_at}"
        keyboard = [[InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_dep_{dep_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_dep_{dep_id}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💰 الاستثمار": await invest_menu(update, context)
    elif text == "💳 الإيداع": await deposit_menu(update, context)
    else: await update.message.reply_text("هذا القسم قيد التطوير.")

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.effective_message.web_app_data.data
    if "deposit_confirmed" in data:
        user_id = update.effective_user.id
        create_deposit(user_id, 1.0) # مبلغ مؤقت
        await update.message.reply_text("✅ تم استلام طلب الإيداع! سيتم مراجعته.")
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب إيداع جديد من `{user_id}`.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "confirm_deposit":
        create_deposit(query.from_user.id, 1.0)
        await query.edit_message_text("✅ تم استلام الطلب! سيتم مراجعته.")
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب إيداع جديد من `{query.from_user.id}`.")
    elif data.startswith("confirm_dep_"):
        dep_id = int(data.split("_")[2])
        conn = sqlite3.connect("gram_max.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, amount FROM deposits WHERE id = ?", (dep_id,))
        row = cursor.fetchone()
        if row:
            update_balance(row[0], row[1])
            cursor.execute("UPDATE deposits SET status = 'completed' WHERE id = ?", (dep_id,))
            conn.commit()
            await context.bot.send_message(chat_id=row[0], text=f"🎉 تم تأكيد إيداعك رقم {dep_id}.")
        conn.close()
        await query.edit_message_text(f"✅ تم تأكيد الإيداع {dep_id}.")
    elif data.startswith("reject_dep_"):
        dep_id = int(data.split("_")[2])
        conn = sqlite3.connect("gram_max.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE deposits SET status = 'rejected' WHERE id = ?", (dep_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"❌ تم رفض الإيداع {dep_id}.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("pending_deposits", pending_deposits))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
