from google import genai
from google.genai import types
from utils.config import GEMINI_API_KEY, MODEL_NAME
from utils.shared_context import logger

def configure_gemini():
    """Ensures the GEMINI_API_KEY is set."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")

def create_gemini_client():
    """Creates and returns a new Gemini API client."""
    configure_gemini()
    client = genai.Client(api_key=GEMINI_API_KEY)
    return client

def create_new_chat(client, system_prefix, response_modalities=None):
    """
    Creates a new Gemini chat instance and sends the system prefix message as
    the initial message. Returns the created chat.
    """
    if response_modalities is None:
        response_modalities = ["Text", "Image"]

    chat = client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(response_modalities=response_modalities)
    )
    chat.send_message(system_prefix)
    logger.info("New Gemini chat created and system prefix message sent.")
    return chat
