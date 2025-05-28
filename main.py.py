import random
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from groq import Groq
from telegram.error import Conflict

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "Your_TG_Token"
GROQ_API_KEY = "Your_Groq_Token"
groq_client = Groq(api_key=GROQ_API_KEY)

MOOD_RESPONSES = [
    "Отлично! Как сам?",
    "Нормально, но могло быть и лучше.",
    "Прекрасно! Готов к чему угодно",
    "Устал... Кофе не спасает ☕",
    "Пойдет",
    "Я просто бот, у меня все одинаково",
]

chat_modes = {}

main_keyboard = ReplyKeyboardMarkup(
    [["Привет", "Как дела?"], ["Давай свободно поговорим", "Пока"]],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие...",
)
ai_keyboard = ReplyKeyboardMarkup(
    [["Пожалуй, закончим"]], resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    chat_modes[user_id] = False
    await update.message.reply_text(
        " Я ваш помощник! Выберите действие:",
        reply_markup=main_keyboard,
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "Привет":
        await update.message.reply_text("И тебе привет! 👋", reply_markup=main_keyboard)

    elif text == "Как дела?":
        response = random.choice(MOOD_RESPONSES)
        await update.message.reply_text(response, reply_markup=main_keyboard)

    elif text == "Давай свободно поговорим":
        chat_modes[user_id] = True
        await update.message.reply_text(
            "💬 Режим свободного общения активирован. Говорите что угодно!",
            reply_markup=ai_keyboard,
        )

    elif text == "Пожалуй, закончим":
        chat_modes[user_id] = False
        await update.message.reply_text(
            "🔄 Возвращаюсь в обычный режим.",
            reply_markup=main_keyboard,
        )

    elif text == "Пока":
        await update.message.reply_text(
            "👋 До свидания! Чтобы снова активировать бота, отправьте /start",
            reply_markup=ReplyKeyboardRemove(),
        )
        if 'application' in globals():
            await application.stop()

    elif chat_modes.get(user_id, False):
        await generate_groq_response(update)

    else:
        await update.message.reply_text(
            "Используйте кнопки или команды :)",
            reply_markup=main_keyboard,
        )


async def generate_groq_response(update: Update) -> None:
    try:
        groq_client.models.list()

        messages = [
            {
                "role": "system",
                "content": "Ты дружелюбный ассистент. Отвечай на русском языке.",
            },
            {"role": "user", "content": update.message.text},
        ]

        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.7,
            max_tokens=1024,
        )

        if chat_completion.choices:
            ai_text = chat_completion.choices[0].message.content
            await update.message.reply_text(ai_text, reply_markup=ai_keyboard)
        else:
            raise ValueError("Пустой ответ от API")

    except Exception as e:
        logger.error(f"Groq API error: {str(e)}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Возврат в обычный режим...",
            reply_markup=main_keyboard,
        )
        chat_modes[update.message.from_user.id] = False


async def shutdown(application: Application) -> None:
    """Корректное завершение работы"""
    await application.stop()
    await application.shutdown()


def main() -> None:
    global application

    try:
        application = Application.builder().token(TOKEN).build()

        handlers = [
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons),
        ]
        for handler in handlers:
            application.add_handler(handler)

        logger.info("Бот запускается...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )

    except Conflict as e:
        logger.error(f"Конфликт: {e}\nЗакройте другие экземпляры бота!")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        logger.info("Бот остановлен")


if __name__ == "__main__":
    main()