import logging
import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# ⚠️ ضع التوكن الخاص بك هنا بين علامات التنصيص
BOT_TOKEN = "8724497887:AAGj-Sfd6ID2vdu_4mbnOQ3E8yJqbZ5zMRA"

# ⚠️ ضع عنوان محفظتك هنا
WALLET_ADDRESS = "UQBrfxfxzB5-op8FGLs-BxnZgOBv0CveJ8VJbC3Xc9pVXZ5X"

# القائمة الرئيسية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# قسم الاستثمار
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
    await update.message.reply_text(text, parse_mode='Markdown')

# الرد على الأزرار
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

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
 
