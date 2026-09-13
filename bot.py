import logging
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

BOT_TOKEN = "8724497887:AAEmhudPVYMApgfakZT_T2X_r61dcTJuemc"
ADMIN_ID = 8183652969
WALLET_ADDRESS = "UQBrfxfxzB5-op8FGLs-BxnZg0Bv0CveJ8VJbC3Xc9pVXZ5X"
BOT_USERNAME = "GramMax1_Bot"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, referrals INTEGER DEFAULT 0, referrer_id INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, wallet TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, referrals, referrer_id FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (user_id, balance, referrals) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        result = (0, 0, None)
    conn.close()
    return result

def update_balance(user_id, amount):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def add_referral(user_id, referrer_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
    cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
    conn.commit()
    conn.close()

def create_withdrawal(user_id, amount, wallet):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO withdrawals (user_id, amount, wallet, status, created_at) VALUES (?, ?, ?, 'pending', ?)", 
                   (user_id, amount, wallet, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    withdraw_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return withdraw_id

def get_pending_withdrawals():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, wallet, created_at FROM withdrawals WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return rows

# ==================== أوامر المستخدم ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if args and args[0].startswith("ref_"):
        referrer_id = int(args[0].split("_")[1])
        if referrer_id != user_id:
            add_referral(user_id, referrer_id)
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

async def referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance, referrals, referrer_id = get_user(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    text = f"👥 **دعوة الأصدقاء**\n\nرابط الإحالة الخاص بك:\n`{link}`\n\nعدد المدعوين: {referrals}\nأرباح الإحالات: 5%"
    await update.message.reply_text(text, parse_mode='Markdown')

# ==================== قسم السحب ====================
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = "WAITING_AMOUNT"
    await update.message.reply_text("💵 السحب\n\nأرسل المبلغ الذي تريد سحبه (مثال: 5):")

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        balance, _, _ = get_user(user_id)
        if amount > balance:
            await update.message.reply_text(f"❌ رصيدك غير كافٍ. رصيدك الحالي: {balance}")
            context.user_data['state'] = None
            return
        context.user_data['withdraw_amount'] = amount
        context.user_data['state'] = "WAITING_WALLET"
        await update.message.reply_text("الآن أرسل عنوان محفظتك:")
    except ValueError:
        await update.message.reply_text("❌ الرجاء إرسال رقم صحيح.")
        context.user_data['state'] = None

async def withdraw_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text
    amount = context.user_data.get('withdraw_amount')
    user_id = update.effective_user.id
    withdraw_id = create_withdrawal(user_id, amount, wallet)
    context.user_data['state'] = None
    await update.message.reply_text(f"✅ تم استلام طلب السحب رقم {withdraw_id}.\nسيتم مراجعته من قبل الإدارة.")
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب سحب جديد رقم {withdraw_id}\n👤 المستخدم: `{user_id}`\n💰 المبلغ: {amount}\n🏦 المحفظة: `{wallet}`", parse_mode='Markdown')

# ==================== لوحة تحكم المشرف ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("👑 لوحة التحكم\n/pending_deposits - طلبات الإيداع\n/pending_withdrawals - طلبات السحب")

async def pending_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount FROM deposits WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("لا توجد طلبات إيداع.")
        return
    for row in rows:
        dep_id, user_id, amount = row
        text = f"📌 إيداع رقم: {dep_id}\n👤 المستخدم: `{user_id}`\n💰 المبلغ: {amount}"
        keyboard = [[InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_dep_{dep_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_dep_{dep_id}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    rows = get_pending_withdrawals()
    if not rows:
        await update.message.reply_text("لا توجد طلبات سحب.")
        return
    for row in rows:
        w_id, user_id, amount, wallet, created_at = row
        text = f"📌 سحب رقم: {w_id}\n👤 المستخدم: `{user_id}`\n💰 المبلغ: {amount}\n🏦 المحفظة: `{wallet}`"
        keyboard = [[InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_wd_{w_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_wd_{w_id}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==================== معالجة الأزرار ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💰 الاستثمار": await invest_menu(update, context)
    elif text == "💳 الإيداع": await deposit_menu(update, context)
    elif text == "👥 دعوة الأصدقاء": await referral_menu(update, context)
    elif text == "💵 السحب": await withdraw_start(update, context)
    elif context.user_data.get('state') == "WAITING_AMOUNT": await withdraw_amount(update, context)
    elif context.user_data.get('state') == "WAITING_WALLET": await withdraw_wallet(update, context)
    else: await update.message.reply_text("هذا القسم قيد التطوير.")

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.effective_message.web_app_data.data
    if "deposit_confirmed" in data:
        user_id = update.effective_user.id
        conn = sqlite3.connect("gram_max.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO deposits (user_id, amount, status, created_at) VALUES (?, 1.0, 'pending', ?)", (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ تم استلام طلب الإيداع! سيتم مراجعته.")
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب إيداع جديد من `{user_id}`.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "confirm_deposit":
        user_id = query.from_user.id
        conn = sqlite3.connect("gram_max.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO deposits (user_id, amount, status, created_at) VALUES (?, 1.0, 'pending', ?)", (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        await query.edit_message_text("✅ تم استلام طلب الإيداع!")
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب إيداع جديد من `{user_id}`.")
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
    elif data.startswith("confirm_wd_"):
        wd_id = int(data.split("_")[2])
        conn = sqlite3.connect("gram_max.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id = ?", (wd_id,))
        row = cursor.fetchone()
        if row:
            update_balance(row[0], -row[1])
            cursor.execute("UPDATE withdrawals SET status = 'completed' WHERE id = ?", (wd_id,))
            conn.commit()
            await context.bot.send_message(chat_id=row[0], text=f"🎉 تم تأكيد سحبك رقم {wd_id}.")
        conn.close()
        await query.edit_message_text(f"✅ تم تأكيد السحب {wd_id}.")
    elif data.startswith("reject_wd_"):
        wd_id = int(data.split("_")[2])
        conn = sqlite3.connect("gram_max.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE withdrawals SET status = 'rejected' WHERE id = ?", (wd_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"❌ تم رفض السحب {wd_id}.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("pending_deposits", pending_deposits))
    app.add_handler(CommandHandler("pending_withdrawals", pending_withdrawals))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
