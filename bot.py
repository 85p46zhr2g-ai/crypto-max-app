import logging
import sqlite3
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

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
CHANNEL_ADD_FEE_GRAM = 1.00
BOT_ADD_FEE_GRAM = 0.30

LEVELS = {
    1: {"amount": 1, "profit": 1.15, "hours": 12},
    2: {"amount": 2, "profit": 2.30, "hours": 24},
    3: {"amount": 5, "profit": 5.70, "hours": 48},
    4: {"amount": 7, "profit": 8.30, "hours": 72},
    5: {"amount": 10, "profit": 13, "hours": 120}
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, referrals INTEGER DEFAULT 0, referrer_id INTEGER, wallet_address TEXT, language TEXT DEFAULT 'ar', notified INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, fee REAL, wallet TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_id TEXT, reward REAL DEFAULT 0, completed_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS channel_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, request_type TEXT, link TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS investments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, level INTEGER, amount REAL, profit REAL, start_time TEXT, end_time TEXT, status TEXT DEFAULT 'active')")
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

def mark_task_completed(user_id, task_id, reward):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_tasks (user_id, task_id, reward, completed_at) VALUES (?, ?, ?, ?)", (user_id, task_id, reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_completed_tasks(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT task_id FROM user_tasks WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def create_investment(user_id, level, amount, profit, hours):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    start = datetime.now()
    end = start + timedelta(hours=hours)
    cursor.execute("INSERT INTO investments (user_id, level, amount, profit, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, 'active')",
                   (user_id, level, amount, profit, start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")))
    inv_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inv_id

def get_active_investments(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, level, amount, profit, end_time FROM investments WHERE user_id = ? AND status = 'active'", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

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
        
        if action == "get_data":
            balance, referrals, wallet, lang, _ = get_user(user_id)
            completed = get_completed_tasks(user_id)
            active_inv = get_active_investments(user_id)
            inv_str = ';'.join([f"{i[0]},{i[1]},{i[2]},{i[3]},{i[4]}" for i in active_inv])
            wallet_str = wallet if wallet else "None"
            await update.message.reply_text(f"DATA:{balance}|{referrals}|{wallet_str}|{lang}|{','.join(completed)}|{inv_str}")
        
        elif action == "verify_task":
            task_id = req_data.get('task_id', '')
            channel_map = {'task1': CHANNEL_1_ID, 'task2': CHANNEL_2_ID}
            if task_id not in channel_map:
                await update.message.reply_text("TASK_FAIL:INVALID_TASK")
                return
            
            if is_task_completed(user_id, task_id):
                await update.message.reply_text(f"TASK_DONE:{task_id}|ALREADY")
                return
            
            channel_id = channel_map[task_id]
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status in ['member', 'administrator', 'creator']:
                    mark_task_completed(user_id, task_id, TASK_REWARD)
                    update_balance(user_id, TASK_REWARD)
                    new_balance, _, _, _, _ = get_user(user_id)
                    await update.message.reply_text(f"TASK_DONE:{task_id}|{new_balance}")
                    await notify_admin(context, f"✅ **إتمام مهمة**\n👤 {user_name}\n🆔 `{user_id}`\n📋 {task_id}\n💰 {TASK_REWARD} GRAM")
                else:
                    await update.message.reply_text("TASK_FAIL:NOT_SUBSCRIBED")
            except Exception as e:
                print(f"Verify error: {e}")
                await update.message.reply_text("TASK_FAIL:ERROR")
        
        elif action == "link_wallet":
            address = req_data.get('address', '')
            if address and (address.startswith('UQ') or address.startswith('EQ')):
                update_wallet(user_id, address)
                await update.message.reply_text(f"WALLET_LINKED:{address}")
                await notify_admin(context, f"💳 **ربط محفظة**\n👤 {user_name}\n🆔 `{user_id}`\n💳 `{address}`")
            else:
                await update.message.reply_text("WALLET_FAIL")
        
        elif action == "add_request":
            req_type = req_data.get('type', '')
            link = req_data.get('link', '')
            fee = CHANNEL_ADD_FEE_GRAM if req_type == 'channel' else BOT_ADD_FEE_GRAM
            balance, _, _, _, _ = get_user(user_id)
            if balance < fee:
                await update.message.reply_text(f"ADD_FAIL:INSUFFICIENT|{balance}")
                return
            req_id = create_request(user_id, req_type, link)
            await update.message.reply_text(f"ADD_SUCCESS:{req_id}")
            await notify_admin(context, f"📢 **طلب إضافة {req_type}**\n👤 {user_name}\n🆔 `{user_id}`\n🔗 {link}\n💵 {fee} GRAM\n\nللقبول: /approve {req_id}")
        
        elif action == "deposit_confirmed":
            amount = float(req_data.get('amount', MIN_DEPOSIT))
            create_deposit(user_id, amount)
            await update.message.reply_text(f"DEPOSIT_OK:{amount}")
            await notify_admin(context, f"💰 **إيداع**\n👤 {user_name}\n🆔 `{user_id}`\n💵 {amount} GRAM")
        
        elif action == "withdraw_request":
            amount = float(req_data.get('amount', 0))
            wallet = req_data.get('wallet', '')
            balance, _, _, _, _ = get_user(user_id)
            if amount <= balance and amount >= MIN_WITHDRAWAL:
                fee = amount * (WITHDRAWAL_FEE_PERCENT / 100)
                create_withdrawal(user_id, amount, fee, wallet)
                await update.message.reply_text(f"WITHDRAW_OK:{amount}")
                await notify_admin(context, f"💸 **طلب سحب**\n👤 {user_name}\n🆔 `{user_id}`\n💵 {amount} GRAM\n💳 `{wallet}`")
            else:
                await update.message.reply_text(f"WITHDRAW_FAIL:INSUFFICIENT|{balance}")
        
        elif action == "invest_start":
            level = int(req_data.get('level', 1))
            amount = float(req_data.get('amount', 0))
            if level not in LEVELS:
                await update.message.reply_text("INVEST_FAIL:INVALID_LEVEL")
                return
            lvl = LEVELS[level]
            balance, _, _, _, _ = get_user(user_id)
            if amount < lvl['amount']:
                await update.message.reply_text(f"INVEST_FAIL:MIN|{lvl['amount']}")
                return
            if amount > balance:
                await update.message.reply_text(f"INVEST_FAIL:INSUFFICIENT|{balance}")
                return
            update_balance(user_id, -amount)
            inv_id = create_investment(user_id, level, amount, lvl['profit'], lvl['hours'])
            new_balance, _, _, _, _ = get_user(user_id)
            await update.message.reply_text(f"INVEST_SUCCESS:{inv_id}|{new_balance}")
            await notify_admin(context, f"📈 **استثمار جديد**\n👤 {user_name}\n🆔 `{user_id}`\n📊 المستوى: {level}\n💵 {amount} GRAM\n💰 العائد: {lvl['profit']} GRAM")
        
        elif action == "change_lang":
            update_language(user_id, req_data.get('lang', 'ar'))
    
    except Exception as e:
        print(f"Error: {e}")

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /approve [رقم]")
        return
    req_id = int(context.args[0])
    row = approve_request(req_id)
    if row:
        user_id, req_type, link = row
        fee = CHANNEL_ADD_FEE_GRAM if req_type == 'channel' else BOT_ADD_FEE_GRAM
        balance, _, _, _, _ = get_user(user_id)
        if balance >= fee:
            update_balance(user_id, -fee)
            await context.bot.send_message(chat_id=user_id, text=f"🎉 تم قبول طلبك! تم خصم {fee} GRAM")
        await update.message.reply_text(f"✅ تم القبول.")
    else:
        await update.message.reply_text("❌ الطلب غير موجود.")

async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /reject [رقم]")
        return
    req_id = int(context.args[0])
    reject_request(req_id)
    await update.message.reply_text(f"❌ تم الرفض.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("استخدم الأزرار المتاحة.")

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
