import io
from telegramify_markdown import telegramify, ContentTypes
from telegramify_markdown.type import File, Photo
from telegram.ext import ContextTypes
from utils.shared_context import logger

async def send_safe_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    """
    Sends a formatted message using telegramify-markdown.
    Breaks down text into possible multiple segments (Text, File, Photo).
    """
    formatted_content_list = await telegramify(text)

    for formatted_content in formatted_content_list:
        if formatted_content.content_type == ContentTypes.TEXT:
            await context.bot.send_message(
                chat_id=chat_id,
                text=formatted_content.content,
                parse_mode="MarkdownV2"
            )
        elif formatted_content.content_type == ContentTypes.FILE:
            if isinstance(formatted_content, File):
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=io.BytesIO(formatted_content.file_data),
                    filename=formatted_content.file_name,
                    caption=formatted_content.caption,
                    parse_mode="MarkdownV2"
                )
        elif formatted_content.content_type == ContentTypes.PHOTO:
            if isinstance(formatted_content, Photo):
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(formatted_content.file_data),
                    filename=formatted_content.file_name,
                    caption=formatted_content.caption,
                    parse_mode="MarkdownV2"
                )
        else:
            logger.warning("Unsupported content type in send_safe_message.")
