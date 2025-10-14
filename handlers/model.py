from telegram import Update
from telegram.ext import ContextTypes
from utils.shared_context import chat_contexts, chat_models, logger
from utils.model_setup import create_gemini_client, create_new_chat, get_current_model
from utils.config import PREFIX_SYS, GEMINI_MODEL, KIMI_MODEL

async def model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switches between Gemini and Kimi models, or shows current model."""
    chat_id = update.effective_chat.id
    args = context.args

    # If no arguments, show current model and available options
    if not args:
        current = get_current_model(chat_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"Current model: {current}\n"
                f"Gemini model: {GEMINI_MODEL}\n"
                f"Kimi model: {KIMI_MODEL}\n\n"
                "Usage: /model <gemini|kimi>"
            )
        )
        return

    # Get the requested model
    requested_model = args[0].lower()

    if requested_model not in ["gemini", "kimi"]:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Invalid model. Please choose 'gemini' or 'kimi'.\nUsage: /model <gemini|kimi>"
        )
        return

    # Get current model
    current_model = get_current_model(chat_id)

    if requested_model == current_model:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Already using {requested_model} model."
        )
        return

    # Switch to the new model
    try:
        client = create_gemini_client()
        new_chat = create_new_chat(client, PREFIX_SYS, chat_id=chat_id, model_type=requested_model)
        chat_contexts[chat_id] = new_chat

        logger.info(f"Switched chat {chat_id} to {requested_model} model")

        model_name = GEMINI_MODEL if requested_model == "gemini" else KIMI_MODEL
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Successfully switched to {requested_model} model ({model_name}). Conversation history has been cleared."
        )

    except Exception as e:
        logger.exception(f"Error switching to {requested_model} model")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Error switching to {requested_model}: {type(e).__name__} - {e}"
        )
