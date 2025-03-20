import logging

# Setup logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Shared contexts
chat_contexts = {}  # Dictionary to store chat contexts by chat_id
chat_temperatures = {}  # Dictionary to store temperature per chat_id
