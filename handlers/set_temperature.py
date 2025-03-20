from telegram import Update
from telegram.ext import ContextTypes
from utils.shared_context import chat_temperatures
from utils.config import DEFAULT_TEMPERATURE

async def set_temperature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets the temperature for the chat."""
    chat_id = update.effective_chat.id

    try:
        if len(context.args) != 1:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Usage: /settemp <0.0-2.0>"
            )
            return

        temp_value = float(context.args[0])
        if 0.0 <= temp_value <= 2.0:
            chat_temperatures[chat_id] = temp_value
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Temperature set to {temp_value} for this chat. "
                     "It will be applied to the next message you send."
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Temperature value must be between 0.0 and 2.0."
            )
    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Invalid temperature value. Please use a number between 0.0 and 2.0."
        )
