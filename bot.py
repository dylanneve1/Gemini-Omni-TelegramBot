import os
import io
import asyncio
import logging
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types
from PIL import Image

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash-exp"  # The correct model ID

# --- Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Error Handling ---
class APIError(Exception):
    """Custom exception for API errors."""
    pass

# --- Gemini Setup ---
def configure_gemini():
    """Configures the Gemini API."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")

# --- Shared Context Management ---
# Store chats by chat_id instead of by user for shared context in group chats
chat_contexts = {}  # Dictionary to store chat contexts by chat_id

# --- Telegram Handler Functions ---
async def start(update, context):
    """Sends a welcome message and initializes the chat."""
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="Hello! I'm your multimodal Gemini 2.0 bot. You can send me text or images, and I'll respond accordingly. Use /clear to reset our conversation."
    )
    
    if chat_id not in chat_contexts:
        configure_gemini()
        client = genai.Client(api_key=GEMINI_API_KEY)
        chat_contexts[chat_id] = client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
        )

async def clear(update, context):
    """Clears the conversation history and resets the Gemini chat."""
    chat_id = update.effective_chat.id
    
    if chat_id in chat_contexts:
        configure_gemini()
        client = genai.Client(api_key=GEMINI_API_KEY)
        chat_contexts[chat_id] = client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
        )
    
    await context.bot.send_message(chat_id=chat_id, text="Conversation history cleared and chat reset.")

async def handle_text(update, context):
    """Handles incoming text messages and interacts with the Gemini API."""
    user_message = update.message.text
    chat_id = update.effective_chat.id

    try:
        if chat_id not in chat_contexts:
            configure_gemini()
            client = genai.Client(api_key=GEMINI_API_KEY)
            chat_contexts[chat_id] = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
            )

        response = chat_contexts[chat_id].send_message(user_message)

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                await context.bot.send_message(chat_id=chat_id, text=part.text)
            elif part.inline_data is not None:
                image_stream = io.BytesIO(part.inline_data.data)
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=image_stream)
                except Exception as e:
                    logger.error(f"Error sending image: {e}")
                    await context.bot.send_message(chat_id=chat_id, text="Error sending the image.")
            else:
                logger.warning("Received an unexpected part type from Gemini.")
                await context.bot.send_message(chat_id=chat_id, text="Received an unexpected response from Gemini.")

    except Exception as e:
        logger.exception(f"Error processing Gemini response: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"Sorry, an error occurred: {type(e).__name__} - {e}")

async def handle_image(update, context):
    """Handles incoming images (including media groups) and interacts with the Gemini API."""
    chat_id = update.effective_chat.id
    user_name = update.message.from_user.first_name
    media_group_id = update.message.media_group_id

    # If the message is part of a media group, accumulate images
    if media_group_id:
        if "media_groups" not in context.chat_data:
            context.chat_data["media_groups"] = {}
        if media_group_id not in context.chat_data["media_groups"]:
            # Initialize storage for this media group
            context.chat_data["media_groups"][media_group_id] = {
                "photos": [],
                "caption": update.message.caption or ""
            }
        # Append the photo (list of sizes) from this update
        context.chat_data["media_groups"][media_group_id]["photos"].append(update.message.photo)
        # Update caption if provided (use the latest caption)
        if update.message.caption:
            context.chat_data["media_groups"][media_group_id]["caption"] = update.message.caption

        # If not already scheduled, schedule processing after a short delay
        if "job" not in context.chat_data["media_groups"][media_group_id]:
            async def process_media_group(mgid):
                await asyncio.sleep(1)  # Wait to allow all media group images to arrive
                media_group = context.chat_data["media_groups"].pop(mgid, None)
                if not media_group:
                    return
                # Flatten the list of photo arrays into a single list
                all_photos = [photo for photos in media_group["photos"] for photo in photos]
                # Deduplicate images using a key derived from file_id
                unique_images = {}
                for photo in all_photos:
                    key = photo.file_id[:-7]
                    if key not in unique_images or photo.file_size > unique_images[key].file_size:
                        unique_images[key] = photo
                image_list = []
                for photo in unique_images.values():
                    file = await context.bot.get_file(photo.file_id)
                    image_bytes = await file.download_as_bytearray()
                    image_list.append(Image.open(io.BytesIO(image_bytes)))
                # Build Gemini message parts
                caption = media_group["caption"] or "Please analyze these images."
                if update.effective_chat.type in ["group", "supergroup"]:
                    caption = f"{user_name}: {caption}"
                parts = [types.Part(text=caption)]
                for img in image_list:
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    buf.seek(0)
                    parts.append(types.Part(inline_data=types.Blob(
                        mime_type="image/jpeg",
                        data=buf.getvalue()
                    )))
                message = types.Content(parts=parts, role="user")

                if chat_id not in chat_contexts:
                    configure_gemini()
                    client = genai.Client(api_key=GEMINI_API_KEY)
                    chat_contexts[chat_id] = client.chats.create(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
                    )

                response = chat_contexts[chat_id].send_message(message)
                for part in response.candidates[0].content.parts:
                    if part.text is not None:
                        await context.bot.send_message(chat_id=chat_id, text=part.text)
                    elif part.inline_data is not None:
                        response_image_stream = io.BytesIO(part.inline_data.data)
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=response_image_stream)
                        except Exception as e:
                            logger.error(f"Error sending image: {e}")
                            await context.bot.send_message(chat_id=chat_id, text="Error sending the image.")
                    else:
                        logger.warning("Received an unexpected part type from Gemini.")
                        await context.bot.send_message(chat_id=chat_id, text="Received an unexpected response from Gemini.")

            # Schedule the job to process the media group
            context.chat_data["media_groups"][media_group_id]["job"] = asyncio.create_task(process_media_group(media_group_id))
        return  # Exit early; the response will be handled by the scheduled job

    # If not part of a media group, process a single image normally
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(image_bytes))
        caption = update.message.caption or "Please analyze this image."
        if update.effective_chat.type in ["group", "supergroup"]:
            caption = f"{user_name}: {caption}"
        parts = [types.Part(text=caption)]
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        parts.append(types.Part(inline_data=types.Blob(
            mime_type="image/jpeg",
            data=buf.getvalue()
        )))
        message = types.Content(parts=parts, role="user")

        if chat_id not in chat_contexts:
            configure_gemini()
            client = genai.Client(api_key=GEMINI_API_KEY)
            chat_contexts[chat_id] = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
            )

        response = chat_contexts[chat_id].send_message(message)
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                await context.bot.send_message(chat_id=chat_id, text=part.text)
            elif part.inline_data is not None:
                response_image_stream = io.BytesIO(part.inline_data.data)
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=response_image_stream)
                except Exception as e:
                    logger.error(f"Error sending image: {e}")
                    await context.bot.send_message(chat_id=chat_id, text="Error sending the image.")
            else:
                logger.warning("Received an unexpected part type from Gemini.")
                await context.bot.send_message(chat_id=chat_id, text="Received an unexpected response from Gemini.")

    except Exception as e:
        logger.exception(f"Error processing image: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"Sorry, an error occurred: {type(e).__name__} - {e}")

# --- Main Function ---
def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Register Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # --- Start the Bot ---
    logger.info("Starting the bot...")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}")