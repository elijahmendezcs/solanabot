# File: notifications.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID")
API_URL  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_telegram(message: str):
    """Send a message via Telegram bot"""
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram bot token or chat ID missing; skipping notification.")
        return
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(API_URL, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
