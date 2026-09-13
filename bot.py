import logging
import sqlite3
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

BOT_TOKEN = "8724497887:AAE02WdKwwMWaXzXmRlsVUiYjPqjVfVR5LI"
ADMIN_ID = 8183652969
WALLET_ADDRESS = "UQBrfxfxzB5-op8FGLs-BxnZg0Bv0CveJ8VJbC3Xc9pVXZ5X"
BOT_USERNAME = "GramMax1_Bot"
SUPPORT_USERNAME = "FastHelp3"
WEBAPP_URL = "https://85p46zhr2g-ai.github.io/crypto-max-app/"

CHANNEL_1_ID = "@CRYBTO_MAX_1"
CHANNEL_2_ID = "@olka_ad"

MIN_DEPOSIT = 1.0
MIN_WITHDRAWAL = 1.0
WITHDRAWAL_FEE_PERCENT = 1.0
TASK_REWARD = 0.01
CHANNEL_ADD_FEE = 1.00
BOT_ADD_FEE = 0.30

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, referrals INTEGER DEFAULT 0, referrer_id INTEGER, wallet_address TEXT, language TEXT DEFAULT 'ar', notifications INTEGER DEFAULT 1, notified INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, fee REAL, wallet TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_id TEXT, completed_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS channel_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, request_type TEXT, link TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, referrals, wallet_address, language, notified FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (user_id, balance, referrals, notified) VALUES (?, 0, 0, 0)", (user_id,))
        conn.commit()
        result = (0, 0, None, 'ar', 0)
    conn.close()
    return result

def mark_notified(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET notified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def create_deposit(user_id, amount):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO deposits (user_id, amount, status, created_at) VALUES (?, ?, 'pending', ?)", (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def create_withdrawal(user_id, amount, fee, wallet):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO withdrawals (user_id, amount, fee, wallet, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)", (user_id, amount, fee, wallet, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
    cursor.execute("INSERT INTO channel_requests (user_id, request_type, link, status, created_at) VALUES (?, ?, ?, 'pending', ?)", (user_id, request_type, link, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    req_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return req_id

def approve_request(req_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, request_type, link FROM channel_requests WHERE id = ?", (req_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE channel_requests SET status = 'approved' WHERE id = ?", (req_id,))
        conn.commit()
    conn.close()
    return row

def reject_request(req_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE channel_requests SET status = 'rejected' WHERE id = ?", (req_id,))
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
    cursor.execute("INSERT INTO user_tasks (user_id, task_id, completed_at) VALUES (?, ?, ?)", (user_id, task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_completed_tasks(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT task_id FROM user_tasks WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

async def notify_admin(context, text):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        print(f"Admin notify error: {e}")

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
    
    balance, referrals, wallet, lang, notified = get_user(user_id)
    
    if not notified:
        await notify_admin(context, f"🔔 **مستخدم جديد**\n👤 {update.effective_user.full_name}\n🆔 `{user_id}`")
        mark_notified(user_id)
    
    keyboard = [[InlineKeyboardButton("🚀 دخول إلى التطبيق", web_app={"url": WEBAPP_URL})]]
    await update.message.reply_text("مرحباً بك في GRAM MAX! 🤖", reply_markup=InlineKeyboardMarkup(keyboard))

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
            await update.message.reply_text(f"✅ تم استلام طلب الإيداع.")
            await notify_admin(context, f"💰 **إيداع**\n👤 {user_name}\n🆔 `{user_id}`\n💵 {amount}")
        
        elif action == "withdraw_request":
            amount = float(req_data.get('amount', 0))
            wallet = req_data.get('wallet', '')
            balance, _, _, _, _ = get_user(user_id)
            if amount <= balance and amount >= MIN_WITHDRAWAL:
                fee = amount * (WITHDRAWAL_FEE_PERCENT / 100)
                create_withdrawal(user_id, amount, fee, wallet)
                await update.message.reply_text(f"✅ تم استلام طلب السحب.")
                await notify_admin(context, f"💸 **طلب سحب**\n👤 {user_name}\n🆔 `{user_id}`\n💵 {amount}\n💳 `{wallet}`")
            else:
                await update.message.reply_text("❌ رصيد غير كافٍ.")
        
        elif action == "link_wallet":
            address = req_data.get('address', '')
            if address and (address.startswith('UQ') or address.startswith('EQ')):
                update_wallet(user_id, address)
                await update.message.reply_text(f"✅ تم ربط المحفظة!")
                await notify_admin(context, f"💳 **ربط محفظة**\n👤 {user_name}\n🆔 `{user_id}`\n💳 `{address}`")
            else:
                await update.message.reply_text("❌ عنوان غير صحيح.")
        
        elif action == "verify_task":
            task_id = req_data.get('task_id', '')
            channel_map = {'task1': CHANNEL_1_ID, 'task2': CHANNEL_2_ID}
            if task_id in channel_map:
                channel_id = channel_map[task_id]
                try:
                    member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                    if member.status in ['member', 'administrator', 'creator']:
                        if not is_task_completed(user_id, task_id):
                            mark_task_completed(user_id, task_id)
                            update_balance(user_id, TASK_REWARD)
                            await update.message.reply_text(f"🎉 تم التحقق! +{TASK_REWARD} GRAM")
                            await notify_admin(context, f"✅ **إتمام مهمة**\n👤 {user_name}\n🆔 `{user_id}`\n📋 {task_id}\n💰 {TASK_REWARD}")
                        else:
                            await update.message.reply_text("✅ أكملت هذه المهمة مسبقاً.")
                    else:
                        await update.message.reply_text("❌ لم تشترك في القناة بعد.")
                except Exception as e:
                    await update.message.reply_text(f"❌ خطأ في التحقق. تأكد أن البوت مشرف في القناة.")
        
        elif action == "add_channel_request":
            balance, _, _, _, _ = get_user(user_id)
            if balance < CHANNEL_ADD_FEE:
                await update.message.reply_text(f"❌ رصيدك غير كافٍ. تحتاج {CHANNEL_ADD_FEE}$\nرصيدك: {balance} GRAM")
                return
            link = req_data.get('link', '')
            if not link or not link.startswith("https://t.me/"):
                await update.message.reply_text("❌ رابط غير صحيح.")
                return
            req_id = create_request(user_id, 'channel', link)
            await update.message.reply_text(f"✅ تم استلام الطلب. سيتم مراجعته.")
            await notify_admin(context, f"📢 **طلب إضافة قناة**\n👤 {user_name}\n🆔 `{user_id}`\n📢 {link}\n💵 {CHANNEL_ADD_FEE}$\n\nللقبول: /approve {req_id}\nللرفض: /reject {req_id}")
        
        elif action == "add_bot_request":
            balance, _, _, _, _ = get_user(user_id)
            if balance < BOT_ADD_FEE:
                await update.message.reply_text(f"❌ رصيدك غير كافٍ. تحتاج {BOT_ADD_FEE}$\nرصيدك: {balance} GRAM")
                return
            link = req_data.get('link', '')
            if not link or not link.startswith("https://t.me/"):
                await update.message.reply_text("❌ رابط غير صحيح.")
                return
            req_id = create_request(user_id, 'bot', link)
            await update.message.reply_text(f"✅ تم استلام الطلب. سيتم مراجعته.")
            await notify_admin(context, f"🤖 **طلب إضافة بوت**\n👤 {user_name}\n🆔 `{user_id}`\n🤖 {link}\n💵 {BOT_ADD_FEE}$\n\nللقبول: /approve {req_id}\nللرفض: /reject {req_id}")
        
        elif action == "change_lang":
            update_language(user_id, req_data.get('lang', 'ar'))
        
        elif action == "get_data":
            balance, referrals, wallet, lang, _ = get_user(user_id)
            completed = get_completed_tasks(user_id)
            await update.message.reply_text(f"DATA:{balance}|{referrals}|{wallet}|{lang}|{','.join(completed)}")
    
    except Exception as e:
        print(f"Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("استخدم الأزرار المتاحة.")

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /approve [رقم_الطلب]")
        return
    req_id = int(context.args[0])
    row = approve_request(req_id)
    if row:
        user_id, req_type, link = row
        fee = CHANNEL_ADD_FEE if req_type == 'channel' else BOT_ADD_FEE
        balance, _, _, _, _ = get_user(user_id)
        if balance >= fee:
            update_balance(user_id, -fee)
            await context.bot.send_message(chat_id=user_id, text=f"🎉 تم قبول طلبك! تم خصم {fee}$ من رصيدك.")
        await update.message.reply_text(f"✅ تم القبول.")
    else:
        await update.message.reply_text("❌ الطلب غير موجود.")

async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /reject [رقم_الطلب]")
        return
    req_id = int(context.args[0])
    reject_request(req_id)
    await update.message.reply_text(f"❌ تم الرفض.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("reject", reject_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
