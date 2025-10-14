"""Kimi (Hack Club) API client implementation."""

import json
import requests
from typing import List, Optional
from google.genai import types

from utils.config import KIMI_API_URL, KIMI_MODEL, DEFAULT_TEMPERATURE
from utils.shared_context import logger


class KimiChatSession:
    """A simple chat session that keeps a local message history and
    relays messages to the Kimi HTTP endpoint.
    """

    def __init__(self, model: str = KIMI_MODEL, system_prefix: Optional[str] = None):
        """Initialize a Kimi chat session.

        Args:
            model: The Kimi model to use
            system_prefix: System message to initialize the chat
        """
        self.model = model
        self.system_prefix = system_prefix or ""
        # history: list of dicts with keys 'role' and 'content'
        self.history: List[dict] = []
        if self.system_prefix:
            self.history.append({"role": "system", "content": self.system_prefix})
        logger.info(f"New Kimi chat session created with model: {model}")

    def send_message(self, message, config: Optional[types.GenerateContentConfig] = None):
        """Sends a message to the Kimi endpoint and returns a fake response
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
                    # binaries to the Kimi payload; instead include a
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

        payload = {
            "model": self.model,
            "messages": list(self.history),
            "temperature": temperature,
        }

        try:
            resp = requests.post(
                KIMI_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
        except requests.exceptions.RequestException as e:
            logger.exception("Request to Kimi endpoint failed")
            raise

        if resp.status_code != 200:
            logger.error("Kimi API error (%s): %s", resp.status_code, resp.text)
            resp.raise_for_status()

        data = resp.json()

        # Parse assistant content. Typical Kimi responses follow the
        # OpenAI-like structure: { choices: [{ message: { content: ... } }] }
        assistant_content = ""
        try:
            assistant_content_raw = data.get("choices", [])[0].get("message", {}).get("content")
            if isinstance(assistant_content_raw, str):
                assistant_content = assistant_content_raw
            else:
                assistant_content = json.dumps(assistant_content_raw)
        except Exception:
            logger.exception("Failed to parse Kimi response JSON")

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


def create_new_kimi_chat(system_prefix):
    """Create a new Kimi chat session.

    Args:
        system_prefix: System message to initialize the chat

    Returns:
        A KimiChatSession instance
    """
    return KimiChatSession(system_prefix=system_prefix)
