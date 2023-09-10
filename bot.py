import os
import openai as novaai
import logging
import nest_asyncio
import requests
from translator import Translator
from PIL import Image
from io import BytesIO
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

def download_image(url: str, path: str) -> None:
    """Downloads an image and returns it."""
    try:
        response = requests.get(url)

        if response.status_code == 200:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)

            image = Image.open(BytesIO(response.content))
            image.save(fp=path)
        else:
            print(f"Failed to download image. Status code: {response.status_code}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise e


async def fetch_response(message: str) -> str:
    """Connects with the API to find the messages"""
    messages.append({"role": "user", "content": message})

    response = await novaai.ChatCompletion.acreate(
        model="gpt-3.5-turbo", messages=messages
    )

    return response['choices'][0]['message']['content']


async def imagine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates an image according to the user's prompt"""
    messages.append({"role": "user", "content": update.message.text})
    prompt = update.message.text.replace("/imagine", "").strip()

    try:
        response = novaai.Image.create(
            prompt=prompt,
            n=1,
            size="1024x1024"
        )

        path = "tmp/image.jpg"
        download_image(response['data'][0]['url'], path)
        await update.message.reply_photo(photo=open(path, "rb"))
        
    except Exception as e:
        print(f"An exception ocurred: {str(e)}")
        return await imagine(update, context) # Keep trying to create image until success


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tells user what the chat can be used for."""
    translator = Translator()
    await update.message.reply_text(translator.get_message(update.effective_user.language_code, "help"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    translator = Translator()
    user = update.effective_user

    await update.message.reply_html(
        rf"{translator.get_message(user.language_code, 'start')} {user.mention_html()}!",
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
    application.add_handler(CommandHandler("imagine", imagine))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()