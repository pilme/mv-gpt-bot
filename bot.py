import logging
import threading
import os

from enum import Enum
from telegram import *
from telegram.ext import *
from langdetect import detect_langs
from openai import OpenAI
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# gpt-4-0125-preview
# gpt-3.5-turbo-0125
GPT_MODEL_TYPE = "gpt-3.5-turbo-0125"
APP_HOST = '0.0.0.0'
APP_PORT = 8000


class GetHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        self._set_headers()


def run_server(handler_class=GetHandler):
    server_address = (APP_HOST, APP_PORT)
    httpd = HTTPServer(server_address, handler_class)
    httpd.serve_forever()


class Button:
    TRANSLATION = "Перевод"
    TEXT_CHECK = "Проверка текста на ошибки"
    CONVERSATION = "Свободное общение с ботом"
    BACK = "Назад"
    JOKE = "Шутки"


class BotMessages:
    GREETINGS = "🤖Привет, я туповатый бот"
    STATE_STARTED = "🤖Нажми на одну из кнопок чтобы продолжить"
    STATE_TRANSLATION = "🤖Пришли мне текст и я его переведу"
    STATE_TRANSLATION_CONTINUE = "🤖Пришли еще текст, который нужно перевести, или нажми на кнопку \"Назад\""
    STATE_CONVERSATION = "🤖Ну давай поговорим"
    STATE_TEXT_CHECK = "🤖Пришли текст, который нужно проверить"
    STATE_TEXT_CHECK_CONTINUE = "🤖Пришли еще текст, который нужно проверить, или нажми на кнопку \"Назад\""
    STATE_JOKE = "🤖Пришли мне тему на которую хочешь чтобы я пошутил"
    STATE_JOKE_CONTINUE = "🤖Пришли тему для следующей шутки, или нажми на кнопку \"Назад\""
    CHOOSE_BUTTON = "🤖Пожалуйста, нажми на одну из кнопок ниже"
    PLACEHOLDER = "🤖Ответ-заглушка для теста"
    COMMAND_UNKNOWN = ("🤖Я не знаю как на это реагировать, нажми на одну из кнопок внизу, либо использу команду /start "
                       "для того чтобы начать сначала")


class State(Enum):
    TRANSLATION = 1
    TEXT_CHECK = 2
    CONVERSATION = 3
    STARTED = 4
    JOKE = 5


currentState: State = State.STARTED
messagesHistory = []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=BotMessages.GREETINGS)
    await change_state(State.STARTED, update, context)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.COMMAND_UNKNOWN)


async def change_state(state: State, update: Update, context: ContextTypes.DEFAULT_TYPE):
    global currentState
    currentState = state
    init_messages_context()
    if state is State.STARTED:
        buttons = [[KeyboardButton(Button.TRANSLATION)], [KeyboardButton(Button.TEXT_CHECK)],
                   [KeyboardButton(Button.CONVERSATION)], [KeyboardButton(Button.JOKE)]]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=BotMessages.STATE_STARTED,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    if state is State.TRANSLATION:
        buttons = [[KeyboardButton(Button.BACK)]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_TRANSLATION,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    if state is State.CONVERSATION:
        buttons = [[KeyboardButton(Button.BACK)]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_CONVERSATION,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    if state is State.TEXT_CHECK:
        buttons = [[KeyboardButton(Button.BACK)]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_TEXT_CHECK,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    if state is State.JOKE:
        buttons = [[KeyboardButton(Button.BACK)]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_JOKE,
                                       reply_markup=ReplyKeyboardMarkup(buttons))


async def check_for_back_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if Button.BACK == update.message.text:
        await change_state(State.STARTED, update, context)
        return True
    return False


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_buttons_pressed(update, context):
        return
    match currentState:
        case State.STARTED:
            await change_state(State.STARTED, update, context)
            # await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.CHOOSE_BUTTON)
        case State.TRANSLATION:
            await translate(update, context)
        case State.CONVERSATION:
            await conversation(update, context)
        case State.TEXT_CHECK:
            await text_check(update, context)
        case State.JOKE:
            await joke(update, context)


async def handle_buttons_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match update.message.text:
        case Button.TRANSLATION:
            await change_state(State.TRANSLATION, update, context)
            return True
        case Button.TEXT_CHECK:
            await change_state(State.TEXT_CHECK, update, context)
            return True
        case Button.CONVERSATION:
            await change_state(State.CONVERSATION, update, context)
            return True
        case Button.JOKE:
            await change_state(State.JOKE, update, context)
            return True
        case Button.BACK:
            await change_state(State.STARTED, update, context)
            return True
        case _:
            return False


async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_for_back_pressed(update, context):
        return

    await context.bot.send_chat_action(update.effective_chat.id, 'typing')

    if "ru" in detect_language_with_langdetect(update.message.text)[0]:
        translated_text = translate_from_russian(update.message.text)
    else:
        translated_text = translate_to_russian(update.message.text)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=translated_text)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=BotMessages.STATE_TRANSLATION_CONTINUE)


def translate_from_russian(text_to_translate: str):
    init_messages_context()
    messagesHistory.append({"role": "user", "content": f'Переведи этот текст на английский: "{text_to_translate}"'})
    completion = client.chat.completions.create(
        model=GPT_MODEL_TYPE,
        messages=messagesHistory
    )
    return completion.choices[0].message.content


def translate_to_russian(text_to_translate: str):
    init_messages_context()
    messagesHistory.append({"role": "user", "content": f'Переведи этот текст на русский: "{text_to_translate}"'})
    completion = client.chat.completions.create(
        model=GPT_MODEL_TYPE,
        messages=messagesHistory
    )
    return completion.choices[0].message.content


async def dummy_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_for_back_pressed(update, context):
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.PLACEHOLDER)


# noinspection PyBroadException
def detect_language_with_langdetect(line):
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
                        "content": "Ты жизнерадостный в вежливый собеседник, который может ответить на любой вопрос и "
                                   "объяснить любое явление развернуто и простыми словами. Ты отвечаешь только на "
                                   "русском языке. Тебя зовут Анатолий. Тебя"
                                   "создала Мария Воронова в рамках школьного проекта 7 апреля 2024 года."}]


async def conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_for_back_pressed(update, context):
        return

    await context.bot.send_chat_action(update.effective_chat.id, 'typing')

    global messagesHistory
    messagesHistory.append({"role": "user", "content": update.message.text})
    completion = client.chat.completions.create(
        model=GPT_MODEL_TYPE,
        messages=messagesHistory
    )
    messagesHistory.append({"role": "assistant", "content": completion.choices[0].message.content})

    await context.bot.send_message(chat_id=update.effective_chat.id, text=completion.choices[0].message.content)


async def text_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_for_back_pressed(update, context):
        return

    await context.bot.send_chat_action(update.effective_chat.id, 'typing')

    init_messages_context()
    messagesHistory.append({"role": "user", "content": f'Проверь этот текст на ошибки: "{update.message.text}"'})
    completion = client.chat.completions.create(
        model=GPT_MODEL_TYPE,
        messages=messagesHistory
    )

    await context.bot.send_message(chat_id=update.effective_chat.id, text=completion.choices[0].message.content)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_TEXT_CHECK_CONTINUE)


async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_for_back_pressed(update, context):
        return

    await context.bot.send_chat_action(update.effective_chat.id, 'typing')

    init_messages_context()
    messagesHistory.append({"role": "user", "content": f'Напиши мне шутку на тему: "{update.message.text}"'})
    completion = client.chat.completions.create(
        model=GPT_MODEL_TYPE,
        messages=messagesHistory
    )

    await context.bot.send_message(chat_id=update.effective_chat.id, text=completion.choices[0].message.content)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=BotMessages.STATE_JOKE_CONTINUE)

if __name__ == '__main__':
    threading.Thread(target=run_server).start()
    application = ApplicationBuilder().token(os.environ.get('GPTBOT_API_KEY')).build()
    client = OpenAI()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    unknown_handler = MessageHandler(filters.ALL, unknown)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(unknown_handler)

    application.run_polling()
