import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read comma-separated tokens and convert to a clean list
raw_tokens = os.getenv("BOT_TOKENS", "")
BOT_TOKENS = [token.strip() for token in raw_tokens.split(",") if token.strip()]

if not BOT_TOKENS:
    raise ValueError("CRITICAL: No bot tokens provided in environment variables (.env)!")