import os
import io
import asyncio
import logging
import markdown2  # pip install markdown2
from bs4 import BeautifulSoup, NavigableString  # pip install beautifulsoup4
from PIL import Image
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash-exp"  # The correct model ID

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
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

# --- HTML Sanitization Helpers ---
ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "code", "pre", "a"}

def sanitize_html_for_telegram(html_text: str) -> str:
    """
    Uses BeautifulSoup to remove any HTML tags that Telegram doesn't support.
    Allowed tags are preserved (for <a> only the href attribute is kept).
    For block-level tags (p, div, br, hr, ul, ol), newlines are inserted.
    """
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        # Process every tag in the document
        for tag in soup.find_all(True):
            if tag.name not in ALLOWED_TAGS:
                # For some block-level tags, insert newline markers before and after
                if tag.name in ['p', 'div', 'br', 'hr', 'ul', 'ol']:
                    tag.insert_before(NavigableString("\n"))
                    tag.insert_after(NavigableString("\n"))
                tag.unwrap()  # Remove the tag but keep its content
            else:
                # For allowed <a> tags, keep only the href attribute.
                if tag.name == "a":
                    allowed_attr = {}
                    if tag.has_attr("href"):
                        allowed_attr["href"] = tag["href"]
                    tag.attrs = allowed_attr
        # Use decode_contents() to return just the inner HTML without wrapping <html> or <body> tags.
        safe_html = soup.decode_contents()
        # Clean up excessive newlines
        safe_html = "\n".join(line.strip() for line in safe_html.splitlines() if line.strip())
        return safe_html
    except Exception as e:
        logger.error("Error during HTML sanitization", exc_info=e)
        # In worst case, return plain text with no formatting.
        return html_text

def safe_markdown_to_html(md_text: str) -> str:
    """
    Converts Markdown to HTML and then sanitizes it so that Telegram's HTML parser accepts it.
    If any error occurs during conversion, the original Markdown text is returned.
    """
    try:
        html_text = markdown2.markdown(md_text)
        safe_html = sanitize_html_for_telegram(html_text)
        return safe_html
    except Exception as e:
        logger.error("Error converting Markdown to safe HTML", exc_info=e)
        return md_text  # fallback to plain markdown text

def send_safe_message(context, chat_id, text: str):
    """
    Attempts to send a message using HTML parse mode.
    If an error occurs, falls back to plain text.
    """
    try:
        safe_html = safe_markdown_to_html(text)
        return context.bot.send_message(
            chat_id=chat_id, text=safe_html, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error("Error sending HTML message, falling back to plain text", exc_info=e)
        return context.bot.send_message(chat_id=chat_id, text=text)

# --- Shared Context Management ---
chat_contexts = {}  # Dictionary to store chat contexts by chat_id

# --- Telegram Handler Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            config=types.GenerateContentConfig(response_modalities=["Text", "Image"], temperature=1.0)
        )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clears the conversation history and resets the Gemini chat."""
    chat_id = update.effective_chat.id
    if chat_id in chat_contexts:
        configure_gemini()
        client = genai.Client(api_key=GEMINI_API_KEY)
        chat_contexts[chat_id] = client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(response_modalities=["Text", "Image"], temperature=1.0)
        )
    await context.bot.send_message(chat_id=chat_id, text="Conversation history cleared and chat reset.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages and interacts with the Gemini API."""
    chat_id = update.effective_chat.id
    user_message = update.message.text
    try:
        if chat_id not in chat_contexts:
            configure_gemini()
            client = genai.Client(api_key=GEMINI_API_KEY)
            chat_contexts[chat_id] = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(response_modalities=["Text", "Image"], temperature=1.0)
            )
        response = chat_contexts[chat_id].send_message(user_message)
        for part in response.candidates[0].content.parts:
            if part.text is not None:
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
        logger.exception("Error processing Gemini response")
        await context.bot.send_message(chat_id=chat_id, text=f"Sorry, an error occurred: {type(e).__name__} - {e}")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming images (including media groups) and interacts with the Gemini API."""
    chat_id = update.effective_chat.id
    user_name = update.message.from_user.first_name
    media_group_id = update.message.media_group_id

    # If the message is part of a media group, accumulate images.
    if media_group_id:
        if "media_groups" not in context.chat_data:
            context.chat_data["media_groups"] = {}
        if media_group_id not in context.chat_data["media_groups"]:
            context.chat_data["media_groups"][media_group_id] = {"photos": [], "caption": update.message.caption or ""}
        context.chat_data["media_groups"][media_group_id]["photos"].append(update.message.photo)
        if update.message.caption:
            context.chat_data["media_groups"][media_group_id]["caption"] = update.message.caption
        if "job" not in context.chat_data["media_groups"][media_group_id]:
            async def process_media_group(mgid):
                await asyncio.sleep(1)  # Allow time for all media group images to arrive.
                media_group = context.chat_data["media_groups"].pop(mgid, None)
                if not media_group:
                    return
                all_photos = [photo for photos in media_group["photos"] for photo in photos]
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
                caption = media_group["caption"] or "Please analyze these images."
                if update.effective_chat.type in ["group", "supergroup"]:
                    caption = f"{user_name}: {caption}"
                parts = [types.Part(text=caption)]
                for img in image_list:
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    buf.seek(0)
                    parts.append(
                        types.Part(
                            inline_data=types.Blob(mime_type="image/jpeg", data=buf.getvalue())
                        )
                    )
                message = types.Content(parts=parts, role="user")
                if chat_id not in chat_contexts:
                    configure_gemini()
                    client = genai.Client(api_key=GEMINI_API_KEY)
                    chat_contexts[chat_id] = client.chats.create(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(response_modalities=["Text", "Image"], temperature=1.0)
                    )
                response = chat_contexts[chat_id].send_message(message)
                for part in response.candidates[0].content.parts:
                    if part.text is not None:
                        await send_safe_message(context, chat_id, part.text)
                    elif part.inline_data is not None:
                        response_image_stream = io.BytesIO(part.inline_data.data)
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=response_image_stream)
                        except Exception as e:
                            logger.error("Error sending image", exc_info=e)
                            await context.bot.send_message(chat_id=chat_id, text="Error sending the image.")
                    else:
                        logger.warning("Unexpected response part from Gemini.")
                        await context.bot.send_message(chat_id=chat_id, text="Unexpected response from Gemini.")
            context.chat_data["media_groups"][media_group_id]["job"] = asyncio.create_task(process_media_group(media_group_id))
        return

    # Process a single image normally.
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
        parts.append(
            types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=buf.getvalue()))
        )
        message = types.Content(parts=parts, role="user")
        if chat_id not in chat_contexts:
            configure_gemini()
            client = genai.Client(api_key=GEMINI_API_KEY)
            chat_contexts[chat_id] = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(response_modalities=["Text", "Image"], temperature=1.0)
            )
        response = chat_contexts[chat_id].send_message(message)
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                await send_safe_message(context, chat_id, part.text)
            elif part.inline_data is not None:
                response_image_stream = io.BytesIO(part.inline_data.data)
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=response_image_stream)
                except Exception as e:
                    logger.error("Error sending image", exc_info=e)
                    await context.bot.send_message(chat_id=chat_id, text="Error sending the image.")
            else:
                logger.warning("Unexpected response part from Gemini.")
                await context.bot.send_message(chat_id=chat_id, text="Unexpected response from Gemini.")
    except Exception as e:
        logger.exception("Error processing image")
        await context.bot.send_message(chat_id=chat_id, text=f"Sorry, an error occurred: {type(e).__name__} - {e}")

# --- Main Function ---
def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    logger.info("Starting the bot...")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}")