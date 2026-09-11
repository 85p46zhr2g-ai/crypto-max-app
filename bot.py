import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً 👋\n"
        "أهلاً بك في بوت Crypto Max 🤖\n\n"
        "اختر من القائمة أو اكتب /help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 الاستثمار\n"
        "👥 دعوة الأصدقاء\n"
        "📊 المستويات\n"
        "📈 الإحصائيات\n"
        "💵 السحب\n"
        "🎁 المكافآت\n"
        "🆘 الدعم"
    )

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN غير موجود")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
