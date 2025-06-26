from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")


# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я AI-бот. Напиши /help для списка команд.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start — запустить бота\n/ask — задать вопрос\n/upload — загрузить файл\n/reset — сбросить контекст")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пока что я ещё не обучен отвечать на вопросы. Скоро добавим!")

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Функция загрузки будет реализована на следующем этапе.")

# Запуск бота
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("upload", upload))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
