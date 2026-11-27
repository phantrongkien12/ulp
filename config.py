import os

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

OWNER_ID = int(os.getenv("OWNER_ID", 8357044091))
ADMIN_ID = int(os.getenv("ADMIN_ID", 8357044091))
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", 0))

UPDATE_CHANNEL_URL = os.getenv("UPDATE_CHANNEL_URL", "t.me/yourchannel")
COMMAND_PREFIXES = ['/', '!', '.']
