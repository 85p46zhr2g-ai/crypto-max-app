import logging
import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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

LEVELS = {1: {"amount": 1, "profit": 1.15, "hours": 12}, 2: {"amount": 2, "profit": 2.30, "hours": 24}, 3: {"amount": 5, "profit": 5.70, "hours": 48}, 4: {"amount": 7, "profit": 8.30, "hours": 72}, 5: {"amount": 10, "profit": 13, "hours": 120}}

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

def update_balance(user_id, amount):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
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

async def notify_admin(context, text):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        print(f"Admin notify error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)
    
    # عرض المهام مع أزرار Inline
    tasks_keyboard = [
        [InlineKeyboardButton("📢 CRYPTO MAX", url="https://t.me/CRYBTO_MAX_1"), InlineKeyboardButton("✅ تحقق", callback_data="verify_task_1")],
        [InlineKeyboardButton("📢 OLKA AD", url="https://t.me/olka_ad"), InlineKeyboardButton("✅ تحقق", callback_data="verify_task_2")],
        [InlineKeyboardButton("🚀 فتح التطبيق المصغر", web_app={"url": WEBAPP_URL})]
    ]
    
    await update.message.reply_text(
        "مرحباً بك في GRAM MAX! 🤖\n\n"
        "📋 **المهام المتاحة:**\n"
        "اشترك في القنوات واضغط تحقق:",
        reply_markup=InlineKeyboardMarkup(tasks_keyboard),
        parse_mode='Markdown'
    )

async def verify_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    task_num = data.split("_")[2]
    task_id = f"task{task_num}"
    channel_map = {'task1': CHANNEL_1_ID, 'task2': CHANNEL_2_ID}
    
    # عرض "جاري التحقق"
    await query.edit_message_text("⏳ جاري التحقق...")
    
    # انتظار ثانيتين
    await asyncio.sleep(2)
    
    # التحقق من الاشتراك
    channel_id = channel_map[task_id]
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            if is_task_completed(user_id, task_id):
                balance, _, _, _, _ = get_user(user_id)
                await query.edit_message_text(
                    f"✅ أكملت هذه المهمة مسبقاً.\n💰 رصيدك: {balance:.2f} GRAM"
                )
                return
            mark_task_completed(user_id, task_id, TASK_REWARD)
            update_balance(user_id, TASK_REWARD)
            balance, _, _, _, _ = get_user(user_id)
            await query.edit_message_text(
                f"✅ تم التحقق بنجاح!\n"
                f"☑️ تمت المهمة\n"
                f"💰 رصيدك الجديد: {balance:.2f} GRAM"
            )
            await notify_admin(context, f"✅ **إتمام مهمة**\n👤 {query.from_user.full_name}\n🆔 `{user_id}`\n📋 {task_id}\n💰 {TASK_REWARD} GRAM")
        else:
            await query.edit_message_text(
                f"❌ لم يتم التحقق من الاشتراك.\n\n"
                f"يرجى الاشتراك بالقناة ثم الضغط على تحقق مرة أخرى."
            )
    except Exception as e:
        print(f"Verify error: {e}")
        await query.edit_message_text("⚠️ تعذر التحقق حالياً، حاول مرة أخرى.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify_task_callback, pattern="^verify_task_"))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
