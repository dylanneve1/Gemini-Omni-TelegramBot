"""Google Gemini API client implementation."""

from google import genai
from google.genai import types
from utils.config import GEMINI_API_KEY, GEMINI_MODEL
from utils.shared_context import logger


class GeminiChatSession:
    """Wrapper for Gemini chat session."""

    def __init__(self, client, system_prefix, response_modalities=None):
        """Initialize a Gemini chat session.

        Args:
            client: The Gemini API client
            system_prefix: System message to initialize the chat
            response_modalities: List of response modalities (default: ["Text", "Image"])
        """
        if response_modalities is None:
            response_modalities = ["Text", "Image"]

        self.chat = client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(response_modalities=response_modalities)
        )
        self.chat.send_message(system_prefix)
        logger.info(f"New Gemini chat created with model: {GEMINI_MODEL}")

    def send_message(self, message, config=None):
        """Send a message to the Gemini chat.

        Args:
            message: The message to send (text or list of Parts)
            config: Optional GenerateContentConfig

        Returns:
            The Gemini API response
        """
        return self.chat.send_message(message, config=config)


def create_gemini_client():
    """Creates and returns a new Gemini API client.

    Returns:
        A configured Gemini client or None if API key is not set

    Raises:
        ValueError: If GEMINI_API_KEY is not set when actually trying to use Gemini
    """
    if not GEMINI_API_KEY:
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Gemini client created successfully")
    return client


def create_new_gemini_chat(system_prefix, response_modalities=None):
    """Create a new Gemini chat session.

    Args:
        system_prefix: System message to initialize the chat
        response_modalities: List of response modalities (default: ["Text", "Image"])

    Returns:
        A GeminiChatSession instance

    Raises:
        ValueError: If GEMINI_API_KEY is not set
    """
    client = create_gemini_client()
    if client is None:
        raise ValueError("GEMINI_API_KEY environment variable not set. Please set it to use Gemini model.")
    return GeminiChatSession(client, system_prefix, response_modalities)
