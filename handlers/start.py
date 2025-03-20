from telegram import Update
from telegram.ext import ContextTypes
from utils.shared_context import chat_contexts, chat_temperatures
from utils.config import PREFIX_SYS
from utils.gemini_setup import create_gemini_client, create_new_chat
from utils.config import DEFAULT_TEMPERATURE

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and initializes the chat."""
    chat_id = update.effective_chat.id

    # Greet the user
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "Hello! I'm Omni. You can send me text, images, stickers, audio messages, or audio files, "
            f"and I'll respond accordingly. Use /clear to reset our conversation. Use /settemp <0.0-2.0> "
            f"to set the temperature for responses. Default temperature is {DEFAULT_TEMPERATURE}."
        )
    )

    if chat_id not in chat_contexts:
        client = create_gemini_client()
        new_chat = create_new_chat(client, PREFIX_SYS)
        chat_contexts[chat_id] = new_chat
        # Optionally reset temperature to default for a new session
        chat_temperatures.pop(chat_id, None)
