import io
from telegram import Update
from telegram.ext import ContextTypes
from google.genai import types
from utils.config import DEFAULT_TEMPERATURE, PREFIX_SYS
from utils.shared_context import chat_contexts, chat_temperatures, logger
from utils.gemini_setup import create_gemini_client, create_new_chat
from utils.sending import send_safe_message

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming audio files (music) and interacts with the Gemini API."""
    chat_id = update.effective_chat.id
    audio = update.message.audio

    logger.info(f"Handling audio file from chat_id: {chat_id}")

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
        file = await context.bot.get_file(audio.file_id)
        audio_bytes = await file.download_as_bytearray()
        audio_stream = io.BytesIO(audio_bytes)

        caption = update.message.caption or ""
        mime_type = audio.mime_type if audio.mime_type else "audio/mpeg"

        parts = [types.Part(text=caption)]
        parts.append(
            types.Part(inline_data=types.Blob(mime_type=mime_type, data=audio_stream.getvalue()))
        )

        response = chat_contexts[chat_id].send_message(message=parts, config=config_with_temp)
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

    except Exception as e:
        logger.exception("Error processing audio file")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Sorry, an error occurred processing the audio file: {type(e).__name__} - {e}"
        )
