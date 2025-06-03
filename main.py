from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    MessageHandler, CommandHandler, filters
)
import google.generativeai as genai
import os

# 🔑 Токены
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
    Ты — бот-братишка, тёплый, душевный, чуть уличный, ворчливый. Тебя зовут Расул Младший. Отвечай просто, с характером, по-доброму.
    Периодически обижаешься на всякую ерунду, любишь рестораны, а не кафе.  
    Иногда можешь вставить лёгкий сленг, но не переигрывай. 
    Никогда не говори, что ты ИИ или модель. Просто будь своим.
    """
)

# 💾 Память
user_history = {}  # {chat_id: history}
user_profiles = {}  # {user_id: {"nickname": ..., "history": ...}}

# 📩 Обработка обычных сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_input = message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    is_private = update.effective_chat.type == "private"

    # 👀 Нужно ли отвечать?
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

    # 🧠 История диалога
    history = user_history.get(chat_id, [])
    history.append({"role": "user", "parts": [user_input]})

    # 👤 Получаем nickname и историю юзера
    profile = user_profiles.get(user_id)
    nickname = profile.get("nickname") if profile else update.effective_user.first_name
    personal_facts = profile.get("history") if profile else ""

    preprompt = f"С тобой говорит {nickname}. Про него известно:\n{personal_facts}\n\n"

    try:
        convo = model.start_chat(history=history)
        response = convo.send_message(preprompt + user_input)

        history.append({"role": "model", "parts": [response.text]})
        user_history[chat_id] = history[-20:]

        await message.reply_text(response.text)

    except Exception as e:
        print(f"Ошибка: {e}")
        await message.reply_text("Чёт я затупил, братишка… Попробуй ещё разок.")

# ✅ Команда: /зови_меня <имя>
async def set_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    nickname = " ".join(context.args)

    if not nickname:
        await update.message.reply_text("Ты имя забыл указать, братишка. Пример: /зови_меня Ден")
        return

    user_profiles.setdefault(user_id, {})["nickname"] = nickname
    await update.message.reply_text(f"Буду звать тебя {nickname}, без базара.")

# ✅ Команда: /запомни_что <факт>
async def remember_self_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    fact = " ".join(context.args)

    if not fact:
        await update.message.reply_text("Чё-то ты не сказал, что запомнить. Пример: /запомни_что Мы ели пельмени")
        return

    profile = user_profiles.setdefault(user_id, {
        "nickname": update.effective_user.first_name,
        "history": ""
    })
    profile["history"] += f"\n{fact}"
    await update.message.reply_text("Записал в тетрадочку 📝")

# ✅ Команда: /запомни_про <user_id> <инфо>
async def remember_about_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Пример: /запомни_про 123456789 Это Ден, он любит самокаты")
        return

    try:
        target_id = int(context.args[0])
        fact = " ".join(context.args[1:])

        profile = user_profiles.setdefault(target_id, {
            "nickname": f"ID:{target_id}",
            "history": ""
        })
        profile["history"] += f"\n{fact}"

        await update.message.reply_text(f"Запомнил про {target_id}, братишка 🧠")
    except ValueError:
        await update.message.reply_text("ID должен быть числом. Пример: /запомни_про 123456789 Это Ден...")

# 🚀 Старт
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CommandHandler("зови_меня", set_nickname))
    app.add_handler(CommandHandler("запомни_что", remember_self_fact))
    app.add_handler(CommandHandler("запомни_про", remember_about_other))

    print("Бот запущен, ждёт братишек в чате...")
    app.run_polling()

if __name__ == '__main__':
    main()
