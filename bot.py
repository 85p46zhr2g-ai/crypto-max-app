import logging
import sqlite3
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# ⚠️ الإعدادات
BOT_TOKEN = "8724497887:AAEmhudPVYMApgfakZT_T2X_r61dcTJuemc"
ADMIN_ID = 8183652969
WALLET_ADDRESS = "UQBrfxfxzB5-op8FGLs-BxnZg0Bv0CveJ8VJbC3Xc9pVXZ5X"
BOT_USERNAME = "GramMax1_Bot"
SUPPORT_USERNAME = "SowzzFF"

# رابط التطبيق المصغر
WEBAPP_URL = "https://85p46zhr2g-ai.github.io/crypto-max-app/"

# قنوات الاشتراك الإجباري
CHANNEL_BOT = "https://t.me/GramMax1_Bot"
CHANNEL_CHAT = "https://t.me/GramMaxChat"
CHANNEL_OWNER = "https://t.me/SowzzFF"

# الحدود الدنيا والرسوم
MIN_DEPOSIT = 1.0
MIN_WITHDRAWAL = 1.0
WITHDRAWAL_FEE_PERCENT = 1.0
ADS_REQUIRED = 15

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==================== قاعدة البيانات ====================
def init_db():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, referrals INTEGER DEFAULT 0, referrer_id INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, fee REAL, wallet TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (user_id INTEGER PRIMARY KEY, language TEXT DEFAULT 'ar', notifications INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ads (user_id INTEGER PRIMARY KEY, ads_watched INTEGER DEFAULT 0, last_ad_time TEXT, withdraw_unlocked INTEGER DEFAULT 0)")
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

def get_ads(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ads_watched, withdraw_unlocked FROM ads WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO ads (user_id, ads_watched, withdraw_unlocked) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        result = (0, 0)
    conn.close()
    return result

def add_ad_watched(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ads_watched FROM ads WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current = row[0] if row else 0
    new_count = current + 1
    unlocked = 1 if new_count >= ADS_REQUIRED else 0
    cursor.execute("UPDATE ads SET ads_watched = ?, last_ad_time = ?, withdraw_unlocked = ? WHERE user_id = ?", 
                   (new_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), unlocked, user_id))
    conn.commit()
    conn.close()
    return new_count, unlocked

def get_settings(user_id):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT language, notifications FROM settings WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
        conn.commit()
        result = ('ar', 1)
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
    withdraw_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return withdraw_id

def get_pending_withdrawals():
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, fee, wallet, created_at FROM withdrawals WHERE status = 'pending'")
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

def update_language(user_id, lang):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def update_notifications(user_id, enabled):
    conn = sqlite3.connect("gram_max.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET notifications = ? WHERE user_id = ?", (enabled, user_id))
    conn.commit()
    conn.close()

# ==================== التحقق من الاشتراك ====================
async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id="@GramMaxChat", user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except:
        pass
    return False

# ==================== أمر البدء (زر واحد فقط) ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    # التحقق من الاشتراك
    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 قناة البوت", url=CHANNEL_BOT)],
            [InlineKeyboardButton("💬 قناة الدردشة", url=CHANNEL_CHAT)],
            [InlineKeyboardButton("👑 قناة صانع البوت", url=CHANNEL_OWNER)],
            [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            "📢 **يرجى الاشتراك بالقنوات أولاً.**\n\nبعد الاشتراك، اضغط على زر التحقق.",
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
    get_settings(user_id)
    get_ads(user_id)
    
    # زر واحد فقط لفتح التطبيق المصغر
    keyboard = [
        [InlineKeyboardButton("🚀 دخول إلى التطبيق", web_app={"url": WEBAPP_URL})]
    ]
    await update.message.reply_text(
        "مرحباً بك في GRAM MAX! 🤖\n\nاضغط على الزر أدناه لفتح التطبيق:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"🆘 **الدعم المباشر**\n\nللتواصل مع الدعم:\n@{SUPPORT_USERNAME}"
    await update.message.reply_text(text, parse_mode='Markdown')

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
        w_id, user_id, amount, fee, wallet, created_at = row
        text = f"📌 سحب رقم: {w_id}\n👤 المستخدم: `{user_id}`\n💰 المبلغ: {amount}\n💸 الرسوم: {fee}\n🏦 المحفظة: `{wallet}`"
        keyboard = [[InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_wd_{w_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_wd_{w_id}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==================== معالجة الأزرار ====================
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    
    try:
        req_data = json.loads(data)
        action = req_data.get('action', '')
        
        if action == "deposit_confirmed":
            amount = float(req_data.get('amount', MIN_DEPOSIT))
            if amount < MIN_DEPOSIT:
                await update.message.reply_text(f"❌ الحد الأدنى للإيداع هو {MIN_DEPOSIT} GRAM.")
                return
            create_deposit(user_id, amount)
            await update.message.reply_text(f"✅ تم استلام طلب الإيداع بمبلغ {amount} GRAM. سيتم مراجعته.")
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب إيداع جديد من `{user_id}` بمبلغ {amount}")
        
        elif action == "withdraw_request":
            amount = float(req_data.get('amount', 0))
            wallet = req_data.get('wallet', '')
            
            ads_watched, unlocked = get_ads(user_id)
            if not unlocked:
                await update.message.reply_text(f"❌ يجب مشاهدة {ADS_REQUIRED} إعلاناً أولاً لفتح السحب.")
                return
            
            balance, _ = get_user(user_id)
            if amount < MIN_WITHDRAWAL:
                await update.message.reply_text(f"❌ الحد الأدنى للسحب هو {MIN_WITHDRAWAL} GRAM.")
                return
            if amount > balance:
                await update.message.reply_text(f"❌ رصيدك غير كافٍ. رصيدك الحالي: {balance}")
                return
            
            fee = amount * (WITHDRAWAL_FEE_PERCENT / 100)
            withdraw_id = create_withdrawal(user_id, amount, fee, wallet)
            await update.message.reply_text(f"✅ تم استلام طلب السحب رقم {withdraw_id}.")
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 طلب سحب جديد رقم {withdraw_id}\n👤 `{user_id}`\n💰 {amount}\n💸 {fee}\n🏦 `{wallet}`", parse_mode='Markdown')
        
        elif action == "change_lang":
            lang = req_data.get('lang', 'ar')
            update_language(user_id, lang)
        
        elif action == "toggle_notifications":
            enabled = 1 if req_data.get('enabled') else 0
            update_notifications(user_id, enabled)
        
        elif action == "watch_ad_complete":
            new_count, unlocked = add_ad_watched(user_id)
            if unlocked:
                await context.bot.send_message(chat_id=user_id, text="🎉 تم فتح السحب بنجاح!")
            else:
                await context.bot.send_message(chat_id=user_id, text=f"✅ تم احتساب الإعلان. التقدم: {new_count}/{ADS_REQUIRED}")
    
    except Exception as e:
        print(f"Error in web_app_data: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == "check_sub":
        is_subscribed = await check_subscription(user_id, context)
        if is_subscribed:
            keyboard = [[InlineKeyboardButton("🚀 دخول إلى التطبيق", web_app={"url": WEBAPP_URL})]]
            await query.edit_message_text(
                "✅ تم التحقق من الاشتراك!\n\nاضغط على الزر أدناه لفتح التطبيق:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ لم يتم التحقق. يرجى الاشتراك في جميع القنوات أولاً.")
    
    elif data == "watch_ad":
        ads_watched, unlocked = get_ads(user_id)
        if unlocked:
            await query.edit_message_text("✅ السحب مفتوح بالفعل!")
            return
        await query.edit_message_text(
            f"🎬 **مشاهدة إعلان**\n\n"
            f"التقدم: {ads_watched}/{ADS_REQUIRED}\n\n"
            f"⚠️ يجب ربط مزود الإعلانات (AdsGram/Monetag) لتفعيل هذه الميزة."
        )
    
    elif data == "confirm_deposit":
        create_deposit(user_id, MIN_DEPOSIT)
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
        cursor.execute("SELECT user_id, amount, fee FROM withdrawals WHERE id = ?", (wd_id,))
        row = cursor.fetchone()
        if row:
            user_id, amount, fee = row
            total_deduction = amount + fee
            update_balance(user_id, -total_deduction)
            cursor.execute("UPDATE withdrawals SET status = 'completed' WHERE id = ?", (wd_id,))
            conn.commit()
            await context.bot.send_message(chat_id=user_id, text=f"🎉 تم تأكيد سحبك رقم {wd_id}.\nتم خصم {amount} + {fee} رسوم.")
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
    app.add_handler(CallbackQueryHandler(button_handler))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
