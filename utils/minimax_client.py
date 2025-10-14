"""MiniMax API client implementation using Anthropic-compatible API."""

import json
import asyncio
from typing import List, Optional
from anthropic import Anthropic
from google.genai import types

from utils.config import MINIMAX_API_URL, MINIMAX_MODEL, MINIMAX_API_KEY, DEFAULT_TEMPERATURE
from utils.shared_context import logger


class MinimaxChatSession:
    """A chat session that uses the MiniMax API via Anthropic-compatible interface."""

    def __init__(self, model: str = MINIMAX_MODEL, system_prefix: Optional[str] = None):
        """Initialize a MiniMax chat session.

        Args:
            model: The MiniMax model to use
            system_prefix: System message to initialize the chat
        """
        self.model = model
        self.system_prefix = system_prefix or ""
        # history: list of dicts with keys 'role' and 'content'
        self.history: List[dict] = []

        # Initialize Anthropic client with MiniMax endpoint
        if not MINIMAX_API_KEY:
            raise ValueError("MINIMAX_API_KEY environment variable not set.")

        self.client = Anthropic(
            base_url=MINIMAX_API_URL,
            api_key=MINIMAX_API_KEY,
        )

        logger.info(f"New MiniMax chat session created with model: {model}")

    async def send_message(self, message, config: Optional[types.GenerateContentConfig] = None):
        """Sends a message to the MiniMax endpoint and returns a fake response
        object compatible with the existing handlers.

        Args:
            message: The message to send (text or list of Parts)
            config: Optional GenerateContentConfig for temperature setting

        Returns:
            A response object compatible with Gemini's response format
        """
        # Build a single user content string from the incoming message
        if isinstance(message, str):
            user_content = message
        elif isinstance(message, list):
            parts_text = []
            for p in message:
                # types.Part has attributes .text and .inline_data
                text_val = getattr(p, "text", None)
                inline = getattr(p, "inline_data", None)
                if text_val:
                    parts_text.append(text_val)
                elif inline is not None:
                    # Inline data is binary content. We won't attach raw
                    # binaries to the MiniMax payload; instead include a
                    # brief placeholder describing the attachment.
                    size = len(getattr(inline, "data", b""))
                    mime = getattr(inline, "mime_type", "application/octet-stream")
                    parts_text.append(f"[Attached file: {mime}, size={size} bytes]")
                else:
                    parts_text.append(str(p))
            user_content = "\n".join(parts_text)
        else:
            user_content = str(message)

        # Add user message to local history
        self.history.append({"role": "user", "content": user_content})

        temperature = getattr(config, "temperature", None) if config else None
        temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE

        # Ensure temperature is within valid range (0.0, 1.0]
        if temperature is not None:
            temperature = max(0.01, min(1.0, temperature))

        try:
            # Use streaming API to collect full response
            # Run in thread pool to avoid blocking event loop during animation
            def _sync_stream():
                full_response = ""
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=4096,
                    temperature=temperature,
                    system=self.system_prefix if self.system_prefix and not self.history[0].get("role") == "system" else None,
                    messages=[msg for msg in self.history if msg.get("role") != "system"]
                ) as stream:
                    for text in stream.text_stream:
                        full_response += text
                return full_response

            # Run the blocking call in a thread pool
            loop = asyncio.get_event_loop()
            assistant_content = await loop.run_in_executor(None, _sync_stream)

        except Exception as e:
            logger.exception("Request to MiniMax endpoint failed")
            raise

        # Save assistant reply in history
        self.history.append({"role": "assistant", "content": assistant_content})

        # Build a fake response object compatible with handler expectations
        class FakePart:
            def __init__(self, text=None, inline_data=None):
                self.text = text
                self.inline_data = inline_data

        class FakeContent:
            def __init__(self, parts):
                self.parts = parts

        class FakeCandidate:
            def __init__(self, content):
                self.content = content

        class FakeResponse:
            def __init__(self, candidates):
                self.candidates = candidates

        fake_parts = [FakePart(text=assistant_content)]
        fake = FakeResponse([FakeCandidate(FakeContent(fake_parts))])
        return fake


def create_new_minimax_chat(system_prefix):
    """Create a new MiniMax chat session.

    Args:
        system_prefix: System message to initialize the chat

    Returns:
        A MinimaxChatSession instance
    """
    return MinimaxChatSession(system_prefix=system_prefix)
