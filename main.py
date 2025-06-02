from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 🧠 Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    generation_config={
        "temperature": 0.8,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    },
    system_instruction="""
    Ты — бот-братишка, тёплый, душевный, чуть уличный. Отвечай просто, с характером, по-доброму.
    Иногда можешь вставить лёгкий сленг, но не переигрывай. Помогаешь, как старший брат.
    Никогда не говори, что ты ИИ или модель. Просто будь своим.
    """
)

# 📩 Обработка входящих сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    try:
        response = model.generate_content(user_input)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("Чёт я затупил, братишка… Попробуй ещё разок.")

# 🚀 Запуск бота
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Бот запущен, ждёт братишек в чате...")
    app.run_polling()

if __name__ == '__main__':
    main()
