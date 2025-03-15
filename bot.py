import os
import io
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
    await context.bot.send_message(chat_id=chat_id,
                                   text="Hello! I'm your multimodal Gemini 2.0 bot. You can send me text or images, and I'll respond accordingly. Use /clear to reset our conversation.")
    
    # Initialize a new chat for this chat_id if it doesn't exist
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
    
    # Reset the chat for this chat_id
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
    user_name = update.message.from_user.first_name

    try:
        # Initialize chat if it doesn't exist for this chat_id
        if chat_id not in chat_contexts:
            configure_gemini()
            client = genai.Client(api_key=GEMINI_API_KEY)
            chat_contexts[chat_id] = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
            )

        # Send message to Gemini and get the response
        response = chat_contexts[chat_id].send_message(user_message)

        # Process the response
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
    """Handles incoming images and interacts with the Gemini API."""
    chat_id = update.effective_chat.id
    user_name = update.message.from_user.first_name
    
    try:
        # Get the image file
        photo = update.message.photo[-1]  # Get the largest available photo
        file = await context.bot.get_file(photo.file_id)
        
        # Download the image
        image_bytes_io = io.BytesIO()
        await file.download_to_memory(image_bytes_io)
        image_bytes_io.seek(0)
        
        # Initialize chat if it doesn't exist for this chat_id
        if chat_id not in chat_contexts:
            configure_gemini()
            client = genai.Client(api_key=GEMINI_API_KEY)
            chat_contexts[chat_id] = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
            )
        
        # Add username prefix in group chats
        caption = update.message.caption or "Please analyze this image."
        if update.effective_chat.type in ["group", "supergroup"]:
            caption = f"{user_name}: {caption}"
        
        # Send the image to Gemini
        # Create a multipart message
        message = types.Content(
            parts=[
                types.Part(text=caption),
                types.Part(inline_data=types.Blob(
                    mime_type="image/jpeg",
                    data=image_bytes_io.getvalue()
                ))
            ],
            role="user"
        )
        response = chat_contexts[chat_id].send_message(message)

        # Process the response
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

