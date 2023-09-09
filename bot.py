import os
import openai as novaai
import logging
import nest_asyncio
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Set API base and key to nova endpoint
novaai.api_base = 'https://api.nova-oss.com/v1'
novaai.api_key = os.getenv('NOVA_API_KEY')

# Enable multiple loops
nest_asyncio.apply()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
messages = [{"role": "system", "content": "You are an intelligent assistant."}]

async def fetch_response(message: str) -> str:
    """Connects with the API to find the messages"""
    messages.append({"role": "user", "content": message})

    response = await novaai.ChatCompletion.acreate(
        model="gpt-3.5-turbo", messages=messages
    )

    return response['choices'][0]['message']['content']


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tells user what the chat can be used for."""
    await update.message.reply_text(
        """Welcome to my help menu! I can assist you with various tasks such as answering questions, providing information, setting reminders, and even playing games. Just ask me anything and I'll do my best to assist you!"""
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    response = await fetch_response(update.message.text)
    await update.message.reply_text(response)


def main() -> None:
    """Start the bot."""
    token = os.getenv('TELEGRAM_TOKEN')

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()