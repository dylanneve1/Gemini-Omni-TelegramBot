"""Unified chat setup that routes to Gemini, Kimi, or MiniMax based on configuration."""

from utils.config import DEFAULT_MODEL, get_system_prefix
from utils.shared_context import logger, chat_models
from utils.gemini_client import create_new_gemini_chat
from utils.kimi_client import create_new_kimi_chat
from utils.minimax_client import create_new_minimax_chat


def create_gemini_client():
    """Compatibility function - no longer needed but kept for backward compatibility."""
    return None


def create_new_chat(client, system_prefix, response_modalities=None, chat_id=None, model_type=None):
    """
    Creates a new chat instance (Gemini, Kimi, or MiniMax) based on configuration.

    Args:
        client: Ignored (kept for backward compatibility)
        system_prefix: System message to initialize the chat (will be overridden with model-specific message)
        response_modalities: Response modalities for Gemini (ignored for Kimi and MiniMax)
        chat_id: Optional chat ID to track which model to use
        model_type: Force a specific model type ("gemini", "kimi", or "minimax")

    Returns:
        A chat session (either GeminiChatSession, KimiChatSession, or MinimaxChatSession)
    """
    # Determine which model to use
    if model_type:
        current_model = model_type
    elif chat_id and chat_id in chat_models:
        current_model = chat_models[chat_id]
    else:
        current_model = DEFAULT_MODEL

    # Store the model choice for this chat
    if chat_id:
        chat_models[chat_id] = current_model

    # Get model-specific system prefix
    model_system_prefix = get_system_prefix(current_model)

    # Create the appropriate chat session
    if current_model == "kimi":
        logger.info(f"Creating new Kimi chat session for chat_id: {chat_id}")
        return create_new_kimi_chat(model_system_prefix)
    elif current_model == "minimax":
        logger.info(f"Creating new MiniMax chat session for chat_id: {chat_id}")
        return create_new_minimax_chat(model_system_prefix)
    else:  # Default to Gemini
        logger.info(f"Creating new Gemini chat session for chat_id: {chat_id}")
        return create_new_gemini_chat(model_system_prefix, response_modalities)


def get_current_model(chat_id):
    """Get the current model for a chat.

    Args:
        chat_id: The chat ID

    Returns:
        The model name ("gemini", "kimi", or "minimax")
    """
    return chat_models.get(chat_id, DEFAULT_MODEL)
