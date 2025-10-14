# Omni - Multimodal AI Telegram Bot

## Description

Omni is a Telegram bot that supports multiple AI models (Google Gemini, Kimi K2, and MiniMax-M2), designed to be a versatile and engaging conversational partner. It's capable of understanding and responding to various types of content, including:

*   **Text:**  Engage in text-based conversations, ask questions, and get creative text outputs.
*   **Images:** Send images and stickers, and Omni can analyze and respond to them, even performing image-related tasks.
*   **Audio Messages and Audio Files:** Send voice messages or music files, and Omni can process and understand the audio content.

Omni is built with a focus on providing creative and helpful responses, avoiding generic or lazy outputs, especially when generating images. It aims to engage users with personality and concise, informative replies. Conversation history is maintained for a more contextual interaction, and you can reset the conversation at any time.

Responses are formatted using `telegramify-markdown` to ensure visually appealing and well-structured messages in Telegram, including support for MarkdownV2 formatting, images, and files within responses.

## Setup Instructions

Before you can run Omni, you need to set up a few things:

### Prerequisites

*   **Python 3.7+**
*   **pip** (Python package installer)
*   **Telegram Bot Token:** You need to create a Telegram bot using BotFather and obtain its token.
*   **Google Gemini API Key:** (Required for Gemini model) You need to obtain an API key for the Google Gemini API.
*   **MiniMax API Key:** (Optional, for MiniMax-M2 model) You need to obtain an API key from MiniMax.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/dylanneve1/Gemini-Omni-TelegramBot
    cd Gemini-Omni-TelegramBot
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Environment Variables

You need to set the following environment variables:

*   `TELEGRAM_BOT_TOKEN`:  Your Telegram Bot Token obtained from BotFather.
*   `GEMINI_API_KEY`: Your Google Gemini API key (required for Gemini model).
*   `MINIMAX_API_KEY`: Your MiniMax API key (optional, only needed for MiniMax-M2 model).

You can set these variables in your shell environment or using a `.env` file if you prefer. For example, in your shell:

```bash
export TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
export MINIMAX_API_KEY="YOUR_MINIMAX_API_KEY"  # Optional
```

### Running the Bot

Once you have set up everything, you can run the bot using:

```bash
python main.py
```

You should see a message in the console indicating that the bot has started.

## Usage Instructions

Interact with Omni in Telegram using the following commands and message types:

*   **/start:** Sends a welcome message and initializes the bot for your chat.
*   **/clear:** Clears the current conversation history and resets the chat with Omni, starting a fresh conversation.
*   **/model [gemini|kimi|minimax]:** Switch between AI models. Use without arguments to see current model.
*   **/set_temperature [0.0-2.0]:** Adjust response creativity/randomness. Higher values = more creative.
*   **/astra:** Toggle Astra mode (experimental unrestricted mode).

You can send Omni various message types:

*   **Text Messages:**  Simply type and send text messages. Omni will respond based on the conversation context. All models support text.
*   **Images:** Send images or photos (Gemini only). You can also add captions to your images for context. Omni can analyze and respond to images. You can send single images or media groups of images.
*   **Stickers:** Send stickers (Gemini only). Omni can understand and react to stickers as well.
*   **Audio Messages (Voice Notes):** Send voice messages (Gemini only). Omni will process the audio and respond accordingly.
*   **Audio Files (Music):** Send audio files like music tracks (Gemini only). Omni can analyze and understand audio files.

### Supported Models

*   **Gemini (gemini-2.5-flash-image):** Multimodal model supporting text, images, audio, and file uploads. Can generate both text and images in responses.
*   **Kimi (kimi-k2-instruct-0905):** Text-only model through HackClub API. No API key required for Kimi.
*   **MiniMax-M2:** Advanced reasoning model with text-only support. Displays "Thinking..." indicator during response generation to show reasoning progress.

**Adding Omni to Groups:**

You can add Omni to Telegram group chats. When added to a group, Omni will automatically introduce itself with a welcome message and become active in the group.

## Error Handling and Logging

Omni includes basic error handling and logging. Errors during API calls or message processing will be logged to the console. If you encounter issues, check the logs for more details.

## Dependencies

*   `python-telegram-bot` - Telegram Bot API wrapper
*   `google.genai` - Google Gemini API client
*   `anthropic` - Anthropic/Claude API client (used for MiniMax compatibility)
*   `requests` - HTTP library (used for Kimi API)
*   `pillow` - Python Imaging Library
*   `telegramify-markdown` - Markdown formatting for Telegram
*   `aiohttp` - Async HTTP client

These dependencies are listed in the `requirements.txt` file.

## License

[MIT License](LICENSE) (Please add your chosen license here and create a LICENSE file if you are distributing this project).

## Author

Dylan Neve
