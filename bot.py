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

# القنوات الإجبارية (للمهام فقط)
MANDATORY_CHANNEL_1 = "https://t.me/CRYBTO_MAX_1"
MANDATORY_CHANNEL_2 = "https://t.me/olka_ad"
MANDATORY_CHANNEL_1_ID = "@CRYBTO_MAX_1"
MANDATORY_CHANNEL_2_ID = "@olka_ad"

# الحدود والرسوم
MIN_DEPOSIT = 1.0
MIN_WITHDRAWAL = 1.0
WITHDRAWAL_FEE_PERCENT = 1.0
TASK_REWARD = 0.01
CHANNEL_ADD_FEE = 1.00
BOT_ADD_FEE = 0.30

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==================== قاعدة البيانات ====================
def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, referrals INTEGER DEFAULT 0, referrer_id INTEGER, wallet_address TEXT, language TEXT DEFAULT 'ar', notifications INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, fee REAL, wallet TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_id TEXT, completed_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS channel_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, request_type TEXT, link TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, referrals, wallet_address, language FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (user_id, balance, referrals) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        result = (0, 0, None, 'ar')
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

def update_language(user_id, lang):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def create_request(user_id, request_type, link):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO channel_requests (user_id, request_type, link, status, created_at) VALUES (?, ?, ?, 'pending', ?)", 
                   (user_id, request_type, link, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def is_task_completed(user_id, task_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user_tasks WHERE user_id = ? AND task_id = ?", (user_id, task_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_task_completed(user_id, task_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_tasks (user_id, task_id, completed_at) VALUES (?, ?, ?)", 
                   (user_id, task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_completed_tasks(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT task_id FROM user_tasks WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# ==================== إشعارات المشرف ====================
async def notify_admin(context, text):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        print(f"Admin notify error: {e}")

# ==================== أمر البدء ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].split("_")[1])
            if referrer_id != user_id:
                add_referral(user_id, referrer_id)
        except:
            pass
    
    get_user(user_id)
    
    await notify_admin(context, f"🔔 **مستخدم جديد**\n\n👤 {update.effective_user.full_name}\n🆔 `{user_id}`\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    keyboard = [[InlineKeyboardButton("🚀 دخول إلى التطبيق", web_app={"url": WEBAPP_URL})]]
    await update.message.reply_text(
        "مرحباً بك في GRAM MAX! 🤖\n\nاضغط على الزر أدناه لفتح التطبيق:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== معالجة WebApp ====================
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    
    try:
        req_data = json.loads(data)
        action = req_data.get('action', '')
        
        if action == "deposit_confirmed":
            amount = float(req_data.get('amount', MIN_DEPOSIT))
            create_deposit(user_id, amount)
            await update.message.reply_text(f"✅ تم استلام طلب الإيداع بمبلغ {amount} GRAM.")
            await notify_admin(context, f"💰 **إيداع جديد**\n\n👤 {user_name}\n🆔 `{user_id}`\n💵 {amount} GRAM\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        elif action == "withdraw_request":
            amount = float(req_data.get('amount', 0))
            wallet = req_data.get('wallet', '')
            balance, _, _, _ = get_user(user_id)
            if amount <= balance and amount >= MIN_WITHDRAWAL:
                fee = amount * (WITHDRAWAL_FEE_PERCENT / 100)
                create_withdrawal(user_id, amount, fee, wallet)
                await update.message.reply_text(f"✅ تم استلام طلب السحب.")
                await notify_admin(context, f"💸 **طلب سحب جديد**\n\n👤 {user_name}\n🆔 `{user_id}`\n💵 {amount} GRAM\n💳 `{wallet}`\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            else:
                await update.message.reply_text("❌ رصيد غير كافٍ أو أقل من الحد الأدنى.")
        
        elif action == "link_wallet":
            address = req_data.get('address', '')
            if address and (address.startswith('UQ') or address.startswith('EQ')):
                update_wallet(user_id, address)
                await update.message.reply_text(f"✅ تم ربط المحفظة بنجاح!")
                await notify_admin(context, f"💳 **تم ربط محفظة**\n\n👤 {user_name}\n🆔 `{user_id}`\n💳 `{address}`")
            else:
                await update.message.reply_text("❌ عنوان محفظة غير صحيح.")
        
        elif action == "verify_task":
            task_id = req_data.get('task_id', '')
            channel_map = {'task1': MANDATORY_CHANNEL_1_ID, 'task2': MANDATORY_CHANNEL_2_ID}
            if task_id in channel_map:
                channel_id = channel_map[task_id]
                try:
                    member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                    if member.status in ['member', 'administrator', 'creator']:
                        if not is_task_completed(user_id, task_id):
                            mark_task_completed(user_id, task_id)
                            update_balance(user_id, TASK_REWARD)
                            await update.message.reply_text(f"🎉 تم التحقق! حصلت على {TASK_REWARD} GRAM.")
                            await notify_admin(context, f"✅ **تم إكمال مهمة**\n\n👤 {user_name}\n🆔 `{user_id}`\n📋 {task_id}\n💰 {TASK_REWARD} GRAM")
                        else:
                            await update.message.reply_text("✅ لقد أكملت هذه المهمة مسبقاً.")
                    else:
                        await update.message.reply_text("❌ لم تشترك في القناة بعد.")
                except Exception as e:
                    await update.message.reply_text(f"❌ خطأ في التحقق. تأكد أن البوت مشرف في القناة.")
        
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
        
        elif action == "change_lang":
            lang = req_data.get('lang', 'ar')
            update_language(user_id, lang)
        
        elif action == "get_data":
            balance, referrals, wallet, lang = get_user(user_id)
            completed = get_completed_tasks(user_id)
            await update.message.reply_text(f"DATA:{balance}|{referrals}|{wallet}|{lang}|{','.join(completed)}")
    
    except Exception as e:
        print(f"Error in web_app_data: {e}")

# ==================== معالجة الرسائل ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
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
            create_request(user_id, 'channel', text)
            context.user_data['state'] = None
            await update.message.reply_text(f"✅ تم استلام طلبك! سيتم مراجعته من قبل الإدارة.")
            await notify_admin(context, f"📢 **إضافة قناة جديدة**\n\n👤 {user_name}\n🆔 `{user_id}`\n📢 {text}\n💵 {CHANNEL_ADD_FEE}$\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: تأكد من أن القناة موجودة والبوت مشرف فيها.")
    
    elif state == "WAITING_BOT_LINK":
        if not text.startswith("https://t.me/"):
            await update.message.reply_text("❌ الرجاء إرسال رابط بوت صحيح.")
            return
        create_request(user_id, 'bot', text)
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ تم استلام طلبك! سيتم مراجعته من قبل الإدارة.")
        await notify_admin(context, f"🤖 **إضافة بوت جديد**\n\n👤 {user_name}\n🆔 `{user_id}`\n🤖 {text}\n💵 {BOT_ADD_FEE}$\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    else:
        await update.message.reply_text("استخدم الأزرار المتاحة.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
