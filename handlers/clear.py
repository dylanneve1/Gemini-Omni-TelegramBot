from telegram import Update
from telegram.ext import ContextTypes
from utils.shared_context import chat_contexts, chat_temperatures
from utils.gemini_setup import create_gemini_client, create_new_chat
from utils.config import PREFIX_SYS

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clears the conversation history and resets the Gemini chat and temperature to default."""
    chat_id = update.effective_chat.id

    if chat_id in chat_contexts:
        client = create_gemini_client()
        new_chat = create_new_chat(client, PREFIX_SYS)
        chat_contexts[chat_id] = new_chat

        # Remove stored temperature to reset to default
        chat_temperatures.pop(chat_id, None)

    await context.bot.send_message(chat_id=chat_id, text="Conversation history cleared and chat reset. Temperature reset to default.")
