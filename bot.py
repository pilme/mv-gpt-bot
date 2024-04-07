import logging
import os

from enum import Enum
from telegram import *
from telegram.ext import *
from langdetect import detect_langs
from openai import OpenAI

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


class Button:
    TRANSLATION = "Перевод"
    TEXT_CHECK = "Проверка текста на ошибки"
    CONVERSATION = "Свободное общение с ботом"
    BACK = "Назад"


class BotMessages:
    GREETINGS = "Привет, я туповатый бот, чтобы продолжить нажми на одну из кнопок"
    STATE_STARTED = "Нажми на одну из кнопок чтобы продолжить"
    STATE_TRANSLATION = "Пришли мне текст для перевода"
    STATE_CONVERSATION = "Ну давай поговорим"
    STATE_TEXT_CHECK = "Пришли текст для проверки"
    CHOOSE_BUTTON = "Пожалуйста, нажми на одно из кнопок ниже"
    PLACEHOLDER = "Ответ-заглушка для теста"


class State(Enum):
    TRANSLATION = 1
    TEXT_CHECK = 2
    CONVERSATION = 3
    STARTED = 4


currentState: State = State.STARTED
messagesHistory = []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=BotMessages.GREETINGS)
    await change_state(State.STARTED, update, context)


async def change_state(state: State, update: Update, context: ContextTypes.DEFAULT_TYPE):
    global currentState
    currentState = state
    if state is State.STARTED:
        buttons = [[KeyboardButton(Button.TRANSLATION)], [KeyboardButton(Button.TEXT_CHECK)],
                   [KeyboardButton(Button.CONVERSATION)]]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=BotMessages.STATE_STARTED,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    if state is State.TRANSLATION:
        buttons = [[KeyboardButton(Button.BACK)]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_TRANSLATION,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    if state is State.CONVERSATION:
        init_messages_context()
        buttons = [[KeyboardButton(Button.BACK)]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_CONVERSATION,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    if state is State.TEXT_CHECK:
        buttons = [[KeyboardButton(Button.BACK)]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_TEXT_CHECK,
                                       reply_markup=ReplyKeyboardMarkup(buttons))


async def check_for_back_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if Button.BACK in update.message.text:
        await change_state(State.STARTED, update, context)
        return True
    return False


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match currentState:
        case State.STARTED:
            await handle_buttons_pressed(update, context)
        case State.TRANSLATION:
            await translate(update, context)
        case State.CONVERSATION:
            await dummy_response(update, context)
        case State.TEXT_CHECK:
            await dummy_response(update, context)


async def handle_buttons_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match update.message.text:
        case Button.TRANSLATION:
            await change_state(State.TRANSLATION, update, context)
        case Button.TEXT_CHECK:
            await change_state(State.TEXT_CHECK, update, context)
        case Button.CONVERSATION:
            await change_state(State.CONVERSATION, update, context)
        case _:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=BotMessages.CHOOSE_BUTTON)


async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_for_back_pressed(update, context):
        return
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=detect_language_with_langdetect(update.message.text))


async def dummy_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_for_back_pressed(update, context):
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.PLACEHOLDER)


# noinspection PyBroadException
def detect_language_with_langdetect(line):
    from langdetect import detect_langs
    try:
        langs = detect_langs(line)
        for item in langs:
            # The first one returned is usually the one that has the highest probability
            return item.lang, item.prob
    except:
        return "err", 0.0


def init_messages_context():
    global messagesHistory
    messagesHistory = [{"role": "system",
                        "content": "You are a poetic assistant, skilled in explaining complex programming concepts "
                                   "with creative flair."}]


async def conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global messagesHistory
    # Добавить в историю то что ввел пользователь
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            # {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming
            # concepts with creative flair."},
            {"role": "user", "content": update.message.text}
        ]
    )
    # Добавить в историю то что отдал чат GPT
    await context.bot.send_message(chat_id=update.effective_chat.id, text=completion.choices[0].message.content)


if __name__ == '__main__':
    application = ApplicationBuilder().token(os.environ.get('GPTBOT_API_KEY')).build()
    client = OpenAI()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)

    application.run_polling()
