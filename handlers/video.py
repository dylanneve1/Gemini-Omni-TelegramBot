from telegram import Update
from telegram.ext import ContextTypes
from utils.shared_context import logger

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming video messages and informs users that videos are not supported."""
    chat_id = update.effective_chat.id
    logger.info(f"Video received from chat_id: {chat_id}. Videos are not supported.")
    await context.bot.send_message(chat_id=chat_id, text="Videos aren't supported yet.")
