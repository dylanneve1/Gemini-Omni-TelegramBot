import io
import asyncio
import time
from telegram import Update
from telegram.ext import ContextTypes, filters
from google.genai import types
from telegramify_markdown import telegramify

from utils.config import DEFAULT_TEMPERATURE, PREFIX_SYS
from utils.shared_context import chat_contexts, chat_temperatures, chat_models, logger
from utils.model_setup import create_gemini_client, create_new_chat
from utils.sending import send_safe_message

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages and interacts with the Gemini API."""
    chat_id = update.effective_chat.id
    user_message = update.message.text

    # Ensure chat_context exists
    if chat_id not in chat_contexts:
        client = create_gemini_client()
        new_chat = create_new_chat(client, PREFIX_SYS, chat_id=chat_id)
        chat_contexts[chat_id] = new_chat

    # Get stored temperature or default
    temperature = chat_temperatures.get(chat_id, DEFAULT_TEMPERATURE)
    config_with_temp = types.GenerateContentConfig(
        response_modalities=["Text", "Image"],
        temperature=temperature
    )

    # Check if using MiniMax model and show "Thinking..." indicator
    current_model = chat_models.get(chat_id, "gemini")
    thinking_message = None
    thinking_task = None

    try:
        # For MiniMax, show animated thinking indicator during reasoning
        if current_model == "minimax":
            thinking_message = await context.bot.send_message(
                chat_id=chat_id,
                text="Thinking."
            )

            # Start background task to animate thinking dots and update time
            async def animate_thinking():
                start_time = time.time()
                dots = 1
                try:
                    while True:
                        await asyncio.sleep(0.5)
                        dots = (dots % 3) + 1
                        elapsed = int(time.time() - start_time)
                        dot_text = "." * dots
                        await thinking_message.edit_text(f"Thinking{dot_text} ({elapsed}s)")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error animating thinking message: {e}")

            thinking_task = asyncio.create_task(animate_thinking())

        # Send the user's text to the model
        # For MiniMax, this is async and won't block the animation
        if current_model == "minimax":
            response = await chat_contexts[chat_id].send_message(user_message, config=config_with_temp)
        else:
            response = chat_contexts[chat_id].send_message(user_message, config=config_with_temp)

        # Stop thinking animation
        if thinking_task:
            thinking_task.cancel()
            try:
                await thinking_task
            except asyncio.CancelledError:
                pass

        # Process the response
        first_text_part = True
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                # For MiniMax, update the thinking message with the first text response
                if current_model == "minimax" and thinking_message and first_text_part:
                    first_text_part = False
                    try:
                        # Format the text with telegramify
                        formatted_content_list = await telegramify(part.text)
                        # Use the first formatted content to edit the message
                        if formatted_content_list:
                            await thinking_message.edit_text(
                                formatted_content_list[0].content,
                                parse_mode="MarkdownV2"
                            )
                            # If there are more parts, send them as separate messages
                            for formatted_content in formatted_content_list[1:]:
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text=formatted_content.content,
                                    parse_mode="MarkdownV2"
                                )
                    except Exception as edit_error:
                        logger.error(f"Error editing thinking message: {edit_error}")
                        # If edit fails, just send as a new message
                        await send_safe_message(context, chat_id, part.text)
                else:
                    await send_safe_message(context, chat_id, part.text)
            elif part.inline_data is not None:
                image_stream = io.BytesIO(part.inline_data.data)
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=image_stream)
                except Exception as e:
                    logger.error("Error sending image", exc_info=e)
                    await context.bot.send_message(chat_id=chat_id, text="Error sending the image.")
            else:
                logger.warning("Unexpected response part from Gemini.")
                await context.bot.send_message(chat_id=chat_id, text="Unexpected response from Gemini.")

    except Exception as e:
        # Stop thinking animation if there's an error
        if thinking_task:
            thinking_task.cancel()
            try:
                await thinking_task
            except asyncio.CancelledError:
                pass

        # Update thinking message with error or send new error message
        error_text = f"Sorry, an error occurred: {type(e).__name__} - {e}"
        if thinking_message and current_model == "minimax":
            try:
                await thinking_message.edit_text(error_text)
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text=error_text)
        else:
            await context.bot.send_message(chat_id=chat_id, text=error_text)

        logger.exception("Error processing model response")
