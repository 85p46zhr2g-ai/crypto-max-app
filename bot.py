import logging
import sqlite3
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# ⚠️ الإعدادات
BOT_TOKEN = "8724497887:AAE02WdKwwMWaXzXmRlsVUiYjPqjVfVR5LI"
ADMIN_ID = 8183652969
WALLET_ADDRESS = "UQBrfxfxzB5-op8FGLs-BxnZg0Bv0CveJ8VJbC3Xc9pVXZ5X"
BOT_USERNAME = "GramMax1_Bot"
SUPPORT_USERNAME = "FastHelp3"
WEBAPP_URL = "https://85p46zhr2g-ai.github.io/crypto-max-app/"

# القنوات الإجبارية
MANDATORY_CHANNEL_1 = "https://t.me/CRYBTO_MAX_1"
MANDATORY_CHANNEL_2 = "https://t.me/olka_ad"
MANDATORY_CHANNEL_1_ID = "@CRYBTO_MAX_1"
MANDATORY_CHANNEL_2_ID = "@olka_ad"

# الحدود والرسوم
MIN_DEPOSIT = 1.0
MIN_WITHDRAWAL = 1.0
WITHDRAWAL_FEE_PERCENT = 1.0
TASK_REWARD = 0.01
CHANNEL_ADD_FEE = 2.00
BOT_ADD_FEE = 0.30

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==================== قاعدة البيانات ====================
def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, referrals INTEGER DEFAULT 0, referrer_id INTEGER, wallet_address TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, fee REAL, wallet TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (user_id INTEGER PRIMARY KEY, language TEXT DEFAULT 'ar', notifications INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS task_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, channel_link TEXT, channel_id TEXT, owner_id INTEGER, status TEXT DEFAULT 'active', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, channel_id INTEGER, completed_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS channel_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, request_type TEXT, link TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    conn.commit()
    conn.close()

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

def create_deposit(user_id, amount):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO deposits (user_id, amount, status, created_at) VALUES (?, ?, 'pending', ?)", 
                   (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def create_withdrawal(user_id, amount, fee, wallet):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO withdrawals (user_id, amount, fee, wallet, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", 
                   (user_id, amount, fee, wallet, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_pending_withdrawals():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, fee, wallet FROM withdrawals WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_referral(user_id, referrer_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
    cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
    conn.commit()
    conn.close()

def update_wallet(user_id, address):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET wallet_address = ? WHERE user_id = ?", (address, user_id))
    conn.commit()
    conn.close()

def get_wallet(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT wallet_address FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def create_request(user_id, request_type, link):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO channel_requests (user_id, request_type, link, status, created_at) VALUES (?, ?, ?, 'pending', ?)", 
                   (user_id, request_type, link, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_pending_requests():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, request_type, link FROM channel_requests WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def approve_request(req_id, link):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, request_type FROM channel_requests WHERE id = ?", (req_id,))
    row = cursor.fetchone()
    if row:
        user_id, req_type = row
        cursor.execute("UPDATE channel_requests SET status = 'approved' WHERE id = ?", (req_id,))
        if req_type == 'channel':
            cursor.execute("INSERT INTO task_channels (channel_link, channel_id, owner_id, status, created_at) VALUES (?, ?, ?, 'active', ?)", 
                           (link, link.replace("https://t.me/", "@"), user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    conn.close()
    return row

def reject_request(req_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE channel_requests SET status = 'rejected' WHERE id = ?", (req_id,))
    conn.commit()
    conn.close()

# ==================== التحقق من الاشتراك ====================
async def check_mandatory_subscription(user_id, context):
    try:
        member1 = await context.bot.get_chat_member(chat_id=MANDATORY_CHANNEL_1_ID, user_id=user_id)
        member2 = await context.bot.get_chat_member(chat_id=MANDATORY_CHANNEL_2_ID, user_id=user_id)
        if member1.status in ['member', 'administrator', 'creator'] and member2.status in ['member', 'administrator', 'creator']:
            return True
    except:
        pass
    return False

# ==================== أمر البدء ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    is_subscribed = await check_mandatory_subscription(user_id, context)
    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 الاشتراك بالقناة الأولى", url=MANDATORY_CHANNEL_1)],
            [InlineKeyboardButton("📢 الاشتراك بالقناة الثانية", url=MANDATORY_CHANNEL_2)],
            [InlineKeyboardButton("✅ التحقق من الاشتراك", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            "📢 **يرجى الاشتراك بالقناتين أولاً.**\n\nبعد الاشتراك، اضغط على زر التحقق.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].split("_")[1])
            if referrer_id != user_id:
                add_referral(user_id, referrer_id)
        except:
            pass
    
    get_user(user_id)
    keyboard = [[InlineKeyboardButton("🚀 دخول إلى التطبيق", web_app={"url": WEBAPP_URL})]]
    await update.message.reply_text(
        "مرحباً بك في GRAM MAX! 🤖\n\nاضغط على الزر أدناه لفتح التطبيق:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== معالجة WebApp ====================
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    
    try:
        req_data = json.loads(data)
        action = req_data.get('action', '')
        
        if action == "deposit_confirmed":
            amount = float(req_data.get('amount', MIN_DEPOSIT))
            create_deposit(user_id, amount)
            await update.message.reply_text(f"✅ تم استلام طلب الإيداع بمبلغ {amount} GRAM.")
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب إيداع جديد من `{user_id}` بمبلغ {amount}")
        
        elif action == "withdraw_request":
            amount = float(req_data.get('amount', 0))
            wallet = req_data.get('wallet', '')
            balance, _ = get_user(user_id)
            if amount <= balance and amount >= MIN_WITHDRAWAL:
                fee = amount * (WITHDRAWAL_FEE_PERCENT / 100)
                create_withdrawal(user_id, amount, fee, wallet)
                await update.message.reply_text(f"✅ تم استلام طلب السحب.")
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب سحب جديد من `{user_id}`")
            else:
                await update.message.reply_text("❌ رصيد غير كافٍ أو أقل من الحد الأدنى.")
        
        elif action == "link_wallet":
            address = req_data.get('address', '')
            if address and (address.startswith('UQ') or address.startswith('EQ')):
                update_wallet(user_id, address)
                await update.message.reply_text(f"✅ تم ربط المحفظة بنجاح: {address[:15]}...")
            else:
                await update.message.reply_text("❌ عنوان محفظة غير صحيح.")
        
        elif action == "add_channel_request":
            context.user_data['state'] = "WAITING_CHANNEL_LINK"
            await update.message.reply_text(
                "📢 **إضافة قناة**\n\n"
                f"💵 رسوم الإضافة: {CHANNEL_ADD_FEE}$\n\n"
                "⚠️ الشروط:\n"
                "1. القناة عامة (Public).\n"
                "2. البوت مشرف في القناة.\n"
                "3. لا تكرار.\n\n"
                "أرسل رابط قناتك الآن:"
            )
        
        elif action == "add_bot_request":
            context.user_data['state'] = "WAITING_BOT_LINK"
            await update.message.reply_text(
                "🤖 **إضافة بوت**\n\n"
                f"💵 رسوم الإضافة: {BOT_ADD_FEE}$\n\n"
                "أرسل رابط البوت الآن:"
            )
        
        elif action == "do_task":
            task_id = req_data.get('task_id', '')
            conn = sqlite3.connect("gram_max.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_tasks WHERE user_id = ? AND channel_id = ?", (user_id, task_id))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO user_tasks (user_id, channel_id, completed_at) VALUES (?, ?, ?)", 
                               (user_id, task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                update_balance(user_id, TASK_REWARD)
                await update.message.reply_text(f"🎉 تم إكمال المهمة! حصلت على {TASK_REWARD} GRAM.")
            else:
                conn.close()
                await update.message.reply_text("✅ لقد أكملت هذه المهمة مسبقاً.")
        
        elif action == "change_lang":
            lang = req_data.get('lang', 'ar')
            conn = sqlite3.connect("gram_max.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE settings SET language = ? WHERE user_id = ?", (lang, user_id))
            conn.commit()
            conn.close()
        
        elif action == "toggle_notifications":
            enabled = 1 if req_data.get('enabled') else 0
            conn = sqlite3.connect("gram_max.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE settings SET notifications = ? WHERE user_id = ?", (enabled, user_id))
            conn.commit()
            conn.close()
    
    except Exception as e:
        print(f"Error in web_app_data: {e}")

# ==================== معالجة الرسائل ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')
    
    if state == "WAITING_CHANNEL_LINK":
        if not text.startswith("https://t.me/"):
            await update.message.reply_text("❌ الرجاء إرسال رابط قناة صحيح.")
            return
        channel_username = text.replace("https://t.me/", "").replace("@", "")
        try:
            chat = await context.bot.get_chat(chat_id=f"@{channel_username}")
            if chat.username is None:
                await update.message.reply_text("❌ يجب أن تكون القناة عامة.")
                return
            bot_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=context.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text("❌ يجب إضافة البوت كمشرف في القناة أولاً.")
                return
            conn = sqlite3.connect("gram_max.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM task_channels WHERE channel_id = ?", (f"@{channel_username}",))
            if cursor.fetchone():
                conn.close()
                await update.message.reply_text("❌ هذه القناة مضافة مسبقاً.")
                return
            conn.close()
            create_request(user_id, 'channel', text)
            context.user_data['state'] = None
            await update.message.reply_text(f"✅ تم استلام طلبك! سيتم مراجعته من قبل الإدارة.")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 طلب إضافة قناة\n👤 {update.effective_user.full_name}\n🆔 `{user_id}`\n📢 {text}\n💵 {CHANNEL_ADD_FEE}$",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ قبول", callback_data=f"approve_req_{user_id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"reject_req_{user_id}")
                ]])
            )
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: تأكد من أن القناة موجودة والبوت مشرف فيها.")
    
    elif state == "WAITING_BOT_LINK":
        if not text.startswith("https://t.me/"):
            await update.message.reply_text("❌ الرجاء إرسال رابط بوت صحيح.")
            return
        create_request(user_id, 'bot', text)
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم استلام طلبك! سيتم مراجعته من قبل الإدارة.")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 طلب إضافة بوت\n👤 {update.effective_user.full_name}\n🆔 `{user_id}`\n🤖 {text}\n💵 {BOT_ADD_FEE}$",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ قبول", callback_data=f"approve_req_{user_id}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"reject_req_{user_id}")
            ]])
        )
    else:
        await update.message.reply_text("استخدم الأزرار المتاحة.")

# ==================== معالجة الأزرار ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == "check_sub":
        is_subscribed = await check_mandatory_subscription(user_id, context)
        if is_subscribed:
            keyboard = [[InlineKeyboardButton("🚀 دخول إلى التطبيق", web_app={"url": WEBAPP_URL})]]
            await query.edit_message_text(
                "✅ تم التحقق من الاشتراك!\n\nاضغط على زر أدناه:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ لم يتم التحقق. يرجى الاشتراك في القناتين أولاً.")
    
    elif data.startswith("approve_req_"):
        req_id = int(data.split("_")[2])
        row = approve_request(req_id, "")
        if row:
            user_id, req_type = row
            await context.bot.send_message(chat_id=user_id, text=f"🎉 تم قبول طلبك!")
        await query.edit_message_text("✅ تم القبول.")
    
    elif data.startswith("reject_req_"):
        req_id = int(data.split("_")[2])
        reject_request(req_id)
        await query.edit_message_text("❌ تم رفض الطلب.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
