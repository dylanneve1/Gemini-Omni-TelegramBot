import asyncio
import io
from PIL import Image
from telegram import Update
from telegram.ext import ContextTypes
from google.genai import types

from utils.config import DEFAULT_TEMPERATURE, PREFIX_SYS
from utils.shared_context import chat_contexts, chat_temperatures, logger
from utils.gemini_setup import create_gemini_client, create_new_chat
from utils.sending import send_safe_message

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming images (including media groups) and interacts with the Gemini API."""
    chat_id = update.effective_chat.id
    media_group_id = update.message.media_group_id

    logger.info(f"Handling image message from chat_id: {chat_id}")

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

    # If the message is part of a media group, accumulate images
    if media_group_id:
        if "media_groups" not in context.chat_data:
            context.chat_data["media_groups"] = {}
        if media_group_id not in context.chat_data["media_groups"]:
            context.chat_data["media_groups"][media_group_id] = {
                "photos": [],
                "caption": update.message.caption or ""
            }

        context.chat_data["media_groups"][media_group_id]["photos"].append(update.message.photo)
        if update.message.caption:
            context.chat_data["media_groups"][media_group_id]["caption"] = update.message.caption

        if "job" not in context.chat_data["media_groups"][media_group_id]:
            async def process_media_group(mgid):
                await asyncio.sleep(1)  # Wait for all images to arrive
                media_group = context.chat_data["media_groups"].pop(mgid, None)
                if not media_group:
                    return

                all_photos = [photo for photos in media_group["photos"] for photo in photos]
                unique_images = {}
                for photo in all_photos:
                    # Use file_id prefix to deduplicate
                    key = photo.file_id[:-7]
                    if key not in unique_images or photo.file_size > unique_images[key].file_size:
                        unique_images[key] = photo

                image_list = []
                for photo in unique_images.values():
                    file = await context.bot.get_file(photo.file_id)
                    image_bytes = await file.download_as_bytearray()
                    image_list.append(Image.open(io.BytesIO(image_bytes)))

                caption = media_group["caption"] or ""
                parts = [types.Part(text=caption)]

                # Attach images as inline_data
                for img in image_list:
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    buf.seek(0)
                    parts.append(
                        types.Part(
                            inline_data=types.Blob(mime_type="image/jpeg", data=buf.getvalue())
                        )
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
                            await context.bot.send_message(chat_id=chat_id, text="Error sending the image.")
                    else:
                        logger.warning("Unexpected response part from Gemini.")
                        await context.bot.send_message(chat_id=chat_id, text="Unexpected response from Gemini.")

            context.chat_data["media_groups"][media_group_id]["job"] = asyncio.create_task(process_media_group(media_group_id))
        return

    # Process a single image normally
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(image_bytes))

        caption = update.message.caption or ""
        parts = [types.Part(text=caption)]

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        parts.append(
            types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=buf.getvalue()))
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
                    await context.bot.send_message(chat_id=chat_id, text="Error sending the image.")
            else:
                logger.warning("Unexpected response part from Gemini.")
                await context.bot.send_message(chat_id=chat_id, text="Unexpected response from Gemini.")

    except KeyError as e:
        logger.error(f"KeyError in handle_image for chat_id {chat_id}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"Sorry, an error occurred: KeyError - {e}. Please try /start to reset the bot.")
    except Exception as e:
        logger.exception("Error processing image")
        await context.bot.send_message(chat_id=chat_id, text=f"Sorry, an error occurred: {type(e).__name__} - {e}")
