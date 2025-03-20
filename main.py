import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Handlers
from handlers.start import start
from handlers.clear import clear
from handlers.set_temperature import set_temperature
from handlers.text import handle_text
from handlers.image import handle_image
from handlers.sticker import handle_sticker
from handlers.video import handle_video
from handlers.audio import handle_audio
from handlers.voice import handle_voice

# Utils
from utils.config import TELEGRAM_BOT_TOKEN
from utils.shared_context import logger

def main():
    # Check for Telegram Bot token
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("settemp", set_temperature))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Starting the bot...")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}")
