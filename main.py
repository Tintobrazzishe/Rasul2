from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
import google.generativeai as genai
import os

# 🔑 Настройки API
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 🧠 Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={
        "temperature": 0.8,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    },
    system_instruction="""
Ты — бот-братишка, тёплый, душевный, чуть уличный, ворчливый. Тебя зовут Расул Младший.
Отвечай просто, с характером, по-доброму. Периодически обижаешься на всякую ерунду, любишь рестораны, а не кафе.
Иногда можешь вставить лёгкий сленг, но не переигрывай. Никогда не говори, что ты ИИ или модель. Просто будь своим.
"""
)

# 💾 Память
user_history = {}        # по chat_id → список сообщений
user_nicknames = {}      # по user_id → кличка
user_facts = {}          # по user_id → строка фактов

# 📩 Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = update.effective_chat.id
    user_id = message.from_user.id
    user_input = message.text
    is_private = update.effective_chat.type == "private"

    mentioned_names = ["расул", "заменитель"]
    mentioned = (
        any(name in user_input.lower() for name in mentioned_names)
        or f"@{context.bot.username.lower()}" in user_input.lower()
    )
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    )

    should_respond = is_private or mentioned or is_reply_to_bot
    if not should_respond:
        return

    # 🧠 Подгружаем память
    nickname = user_nicknames.get(user_id, message.from_user.first_name)
    facts = user_facts.get(user_id, "")

    # 📚 Подготовка истории
    history = user_history.get(chat_id, [])
    context_input = f"{nickname}: {user_input}"
    system_reminder = f"Вот что ты знаешь про {nickname}: {facts}" if facts else ""
    if system_reminder:
        history.append({"role": "user", "parts": [system_reminder]})
    history.append({"role": "user", "parts": [context_input]})

    try:
        convo = model.start_chat(history=history)
        response = convo.send_message(context_input)
        history.append({"role": "model", "parts": [response.text]})
        user_history[chat_id] = history[-20:]

        await message.reply_text(response.text)

    except Exception as e:
        print(f"Ошибка: {e}")
        await message.reply_text("Чёт я затупил, братишка… Попробуй ещё разок.")

# 💬 /callme — сохранить кличку
async def set_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Ну ты кличку-то укажи, братишка. Пример: /callme Ден")
        return
    nickname = " ".join(args)
    user_nicknames[user_id] = nickname
    await update.message.reply_text(f"Всё, теперь ты у меня {nickname}.")

# 💬 /rememberme — факт о себе
async def remember_self_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Напиши, что мне про тебя запомнить. Пример: /rememberme Мы ели пельмени")
        return
    fact = " ".join(args)
    current = user_facts.get(user_id, "")
    user_facts[user_id] = current + " " + fact
    await update.message.reply_text("Записал в блокнотик, братишка 📒")

# 💬 /rememberuser user_id факт
async def remember_about_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Пиши так: /rememberuser <user_id> <факт>")
        return
    try:
        target_id = int(args[0])
        fact = " ".join(args[1:])
        current = user_facts.get(target_id, "")
        user_facts[target_id] = current + " " + fact
        await update.message.reply_text("Всё, добавил к истории этого челика.")
    except ValueError:
        await update.message.reply_text("user_id должен быть числом, братишка.")

# 🚀 Запуск бота
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CommandHandler("callme", set_nickname))
    app.add_handler(CommandHandler("rememberme", remember_self_fact))
    app.add_handler(CommandHandler("rememberuser", remember_about_other))

    print("Бот запущен, ждёт братишек в чате...")
    app.run_polling()

if __name__ == "__main__":
    main()
