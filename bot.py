import logging
import sqlite3
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = "8724497887:AAE02WdKwwMWaXzXmRlsVUiYjPqjVfVR5LI"
ADMIN_ID = 8183652969
BOT_USERNAME = "GramMax1_Bot"
WEBAPP_URL = "https://85p46zhr2g-ai.github.io/crypto-max-app/"
DEFAULT_CHANNEL_URL = "https://t.me/CRYBTO_MAX_1"
DEFAULT_WELCOME_IMAGE = "https://i.ibb.co/6PqZ8XK/welcome.jpg"
DEFAULT_BOT_NAME = "GRAM MAX"

TASK_REWARD = 0.01

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, referrals INTEGER DEFAULT 0, referrer_id INTEGER, wallet_address TEXT, language TEXT DEFAULT 'ar', notified INTEGER DEFAULT 0, is_new INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_id TEXT, reward REAL DEFAULT 0, completed_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def set_setting(key, value):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, referrals, wallet_address, language, notified, is_new FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (user_id, balance, referrals, notified, is_new) VALUES (?, 0, 0, 0, 1)", (user_id,))
        conn.commit()
        result = (0, 0, None, 'ar', 0, 1)
    conn.close()
    return result

def mark_user_not_new(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_new = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

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

def get_completed_tasks(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT task_id FROM user_tasks WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    
    balance, referrals, wallet, lang, notified, is_new = get_user(user_id)
    
    # الأزرار
    keyboard = [
        [InlineKeyboardButton("🚀 فتح البوت", web_app={"url": WEBAPP_URL})],
        [InlineKeyboardButton("📢 القناة الرسمية", url=get_setting("channel_url", DEFAULT_CHANNEL_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_new == 1:
        # مستخدم جديد: أرسل رسالة الترحيب مع الصورة
        bot_name = get_setting("bot_name", DEFAULT_BOT_NAME)
        welcome_image = get_setting("welcome_image", DEFAULT_WELCOME_IMAGE)
        welcome_text = (
            f"👋 أهلاً وسهلاً بك في بوت {bot_name}\n\n"
            f"🎉 أهلاً بك معنا!\n"
            f"استمتع بالخدمات والمهام والمميزات الموجودة داخل البوت."
        )
        
        try:
            await update.message.reply_photo(
                photo=welcome_image,
                caption=welcome_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Image error: {e}")
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
        # تحديث حالة المستخدم
        mark_user_not_new(user_id)
        
        # إشعار الأدمن
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 **مستخدم جديد**\n👤 {user_name}\n🆔 `{user_id}`",
                parse_mode='Markdown'
            )
        except:
            pass
    else:
        # مستخدم مسجل مسبقاً: أرسل رسالة بسيطة
        await update.message.reply_text(
            f"👋 أهلاً بك مجدداً {user_name}!\n\n"
            f"استخدم الأزرار أدناه للوصول السريع:",
            reply_markup=reply_markup
        )

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /set_channel [رابط_القناة]")
        return
    url = context.args[0]
    if not url.startswith("https://t.me/"):
        await update.message.reply_text("❌ الرابط غير صحيح.")
        return
    set_setting("channel_url", url)
    await update.message.reply_text(f"✅ تم تعيين رابط القناة: {url}")

async def set_welcome_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /set_welcome_image [رابط_الصورة]")
        return
    url = context.args[0]
    if not url.startswith("http"):
        await update.message.reply_text("❌ الرابط غير صحيح.")
        return
    set_setting("welcome_image", url)
    await update.message.reply_text(f"✅ تم تعيين صورة الترحيب: {url}")

async def set_bot_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /set_bot_name [الاسم]")
        return
    name = " ".join(context.args)
    set_setting("bot_name", name)
    await update.message.reply_text(f"✅ تم تعيين اسم البوت: {name}")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = (
        "👑 **لوحة الأدمن**\n\n"
        "الأوامر المتاحة:\n"
        "/set_channel [رابط] - تعيين رابط القناة الرسمية\n"
        "/set_welcome_image [رابط] - تعيين صورة الترحيب\n"
        "/set_bot_name [اسم] - تعيين اسم البوت\n\n"
        f"📢 القناة الحالية: {get_setting('channel_url', DEFAULT_CHANNEL_URL)}\n"
        f"🖼 صورة الترحيب: {get_setting('welcome_image', DEFAULT_WELCOME_IMAGE)[:50]}...\n"
        f"📝 اسم البوت: {get_setting('bot_name', DEFAULT_BOT_NAME)}"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    
    try:
        req_data = json.loads(data)
        action = req_data.get('action', '')
        
        if action == "get_data":
            balance, referrals, wallet, lang, _, _ = get_user(user_id)
            completed = get_completed_tasks(user_id)
            wallet_str = wallet if wallet else "None"
            await update.message.reply_text(f"DATA:{balance}|{referrals}|{wallet_str}|{lang}|{','.join(completed)}")
        
        elif action == "verify_task":
            task_id = req_data.get('task_id', '')
            channel_map = {'task1': '@CRYBTO_MAX_1', 'task2': '@olka_ad'}
            if task_id not in channel_map:
                await update.message.reply_text("TASK_FAIL:INVALID_TASK")
                return
            if is_task_completed(user_id, task_id):
                balance, _, _, _, _, _ = get_user(user_id)
                await update.message.reply_text(f"TASK_DONE:{task_id}|ALREADY|{balance}")
                return
            channel_id = channel_map[task_id]
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status in ['member', 'administrator', 'creator']:
                    mark_task_completed(user_id, task_id, TASK_REWARD)
                    update_balance(user_id, TASK_REWARD)
                    balance, _, _, _, _, _ = get_user(user_id)
                    await update.message.reply_text(f"TASK_DONE:{task_id}|SUCCESS|{balance}")
                else:
                    await update.message.reply_text("TASK_FAIL:NOT_SUBSCRIBED")
            except Exception as e:
                print(f"Verify error: {e}")
                await update.message.reply_text("TASK_FAIL:ERROR")
        
        elif action == "link_wallet":
            address = req_data.get('address', '')
            if address and (address.startswith('UQ') or address.startswith('EQ')):
                conn = sqlite3.connect("gram_max.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET wallet_address = ? WHERE user_id = ?", (address, user_id))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"WALLET_LINKED:{address}")
            else:
                await update.message.reply_text("WALLET_FAIL")
    
    except Exception as e:
        print(f"Error: {e}")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("set_channel", set_channel))
    app.add_handler(CommandHandler("set_welcome_image", set_welcome_image))
    app.add_handler(CommandHandler("set_bot_name", set_bot_name))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
