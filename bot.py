import logging
import os

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
from openai import OpenAI

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет, я бот, напиши что-нибуть")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            #{"role": "system",
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







