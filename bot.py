import logging
import os

from enum import Enum
from telegram import *
from telegram.ext import *
from openai import OpenAI

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TRANSLATION, TEXT_CHECK, CONVERSATION, BACK = "Перевод", "Проверка текста на ошибки", "Свободное общение с ботом", "Назад"


class State(Enum):
    TRANSLATION = 1
    TEXT_CHECK = 2
    CONVERSATION = 3
    STARTED = 4


currentState: State = State.STARTED


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Привет, я туповатый бот, чтобы продолжить нажми на одну из кнопок")
    await changeState(State.STARTED, update, context)


async def changeState(state: State, update: Update, context: ContextTypes.DEFAULT_TYPE):
    global currentState
    currentState = state
    if state is State.STARTED:
        buttons = [[KeyboardButton(TRANSLATION)], [KeyboardButton(TEXT_CHECK)], [KeyboardButton(CONVERSATION)]]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Нажми на одну из кнопок чтобы продолжить",
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    if state is State.TRANSLATION:
        buttons = [[KeyboardButton(BACK)]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Пришли мне текст для перевода",
                                       reply_markup=ReplyKeyboardMarkup(buttons))


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if TRANSLATION in update.message.text:
        await changeState(State.TRANSLATION, update, context)
    if TEXT_CHECK in update.message.text:
        await checkText(update, context)
    if CONVERSATION in update.message.text:
        await dummyResponse(update, context)
    if BACK in update.message.text:
        await changeState(State.STARTED, update, context)


async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Переводим переводы")


async def checkText(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Проверяем проверочки")


async def dummyResponse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Ответ-заглушка для теста")


async def conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            # {"role": "system",
            # "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
            {"role": "user", "content": update.message.text}
        ]
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=completion.choices[0].message.content)


if __name__ == '__main__':
    application = ApplicationBuilder().token(os.environ.get('GPTBOT_API_KEY')).build()
    client = OpenAI()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)

    application.run_polling()
