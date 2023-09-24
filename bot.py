import os
import openai as novaai
import logging
import nest_asyncio
import requests
import speech_recognition as sr
from PIL import Image
from io import BytesIO
from translator import Translator
from telegram import ForceReply, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Set API base and key to nova endpoint
novaai.api_base = 'https://api.nova-oss.com/v1'
novaai.api_key = os.getenv('NOVA_API_KEY')

# Enable multiple loops
nest_asyncio.apply()

# Enable logging
os.makedirs(os.path.dirname('logger/log.txt'), exist_ok=True)
logging.basicConfig(
    filename='logs/log.txt',
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
            raise Exception(f"Failed to download image. Status code: {response.status_code}")

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
    user = update.effective_user
    message = Translator().get_message(update.effective_user.language_code, 'start')

    await update.message.reply_html(
        rf"{message} {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    os.makedirs(os.path.dirname('tmp/audio.wav'), exist_ok=True)
    message = update.message
    audio = message.audio if message.audio is not None else message.voice

    audio_data = await audio.get_file()
    audio_path = await audio_data.download_to_drive('tmp/audio.wav')

    recognizer = sr.Recognizer()
    with sr.AudioFile(str(audio_path)) as source:
        audio = recognizer.record(source)
        transcription = recognizer.recognize_google(audio, language=update.effective_user.language_code)

    response = await fetch_response(transcription)
    await update.message.reply_text(response)


async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main conversational function.
    Responsible for calling the function that will send the message to chat-gpt and then answering the user.
    """
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
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

    # audio messages will use speech-to-text
    application.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, process_audio))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()