import io
from telegram import Update
from telegram.ext import ContextTypes
from google.genai import types, errors  # Import the errors module
from utils.config import DEFAULT_TEMPERATURE, PREFIX_SYS
from utils.shared_context import chat_contexts, chat_temperatures, logger
from utils.gemini_setup import create_gemini_client, create_new_chat
from utils.sending import send_safe_message

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles file uploads, sends them to Gemini, and returns the response."""
    chat_id = update.effective_chat.id
    document = update.message.document
    file_name = document.file_name

    logger.info(f"Handling file '{file_name}' from chat_id: {chat_id}")

    # Ensure chat_context exists
    if chat_id not in chat_contexts:
        client = create_gemini_client()
        new_chat = create_new_chat(client, PREFIX_SYS)
        chat_contexts[chat_id] = new_chat

    temperature = chat_temperatures.get(chat_id, DEFAULT_TEMPERATURE)
    config_with_temp = types.GenerateContentConfig(
        response_modalities=["Text", "Image"],
        temperature=temperature
    )

    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        mime_type = document.mime_type
        if not mime_type: # added safeguard
            mime_type = "application/octet-stream" # generic binary
            logger.warning(f"File {file_name} has no MIME type. Using: {mime_type}")

        caption = update.message.caption or ""  # Fallback to empty string.
        parts = []
        if caption:  # added so we don't get empty parts with no data in them
            parts.append(types.Part(text=caption))
        parts.append(types.Part(inline_data=types.Blob(mime_type=mime_type, data=file_bytes)))

        response = chat_contexts[chat_id].send_message(message=parts, config=config_with_temp)

        # Process the response
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                await send_safe_message(context, chat_id, part.text)
            elif part.inline_data is not None:
                response_image_stream = io.BytesIO(part.inline_data.data)
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=response_image_stream)
                except Exception as e:
                    logger.error("Error sending image", exc_info=e)
                    await context.bot.send_message(chat_id=chat_id, text="Error sending the image response.")
            else:
                logger.warning("Unexpected response part from Gemini.")
                await context.bot.send_message(chat_id=chat_id, text="Unexpected response from Gemini.")


    except errors.APIError as e:  # Catch Gemini API errors
        logger.exception(f"Gemini API error processing file: {file_name}")
        if "Unsupported MIME type" in str(e):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Sorry, the file type '{mime_type}' is not supported."
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Sorry, an error occurred while processing the file: {e}"
            )
    except Exception as e:
        logger.exception(f"Error processing file: {file_name}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Sorry, an unexpected error occurred: {type(e).__name__} - {e}"
        )
