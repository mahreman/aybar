import os
import sys
import time
import logging
import threading
import json # Added import for json
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Configure basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TO_AYBAR_FILE = "to_aybar.txt"
FROM_AYBAR_FILE = "from_aybar.txt"

# Global script configuration
SCRIPT_CONFIG = {}

def load_script_config():
    """Loads 'telegram' section from config.json into SCRIPT_CONFIG."""
    global SCRIPT_CONFIG
    try:
        with open("config.json", 'r', encoding='utf-8') as f:
            full_config = json.load(f)
            SCRIPT_CONFIG = full_config.get("telegram", {})
        if not SCRIPT_CONFIG:
            logger.warning("No 'telegram' section found in config.json or it's empty.")
        else:
            logger.info("Telegram configuration loaded from config.json")
    except FileNotFoundError:
        logger.warning("config.json not found. Relying solely on environment variables for Telegram config.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding config.json: {e}. Relying solely on environment variables.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading config.json: {e}. Relying solely on environment variables.")

class TelegramBridge:
    def __init__(self, token: str, authorized_chat_id: int):
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN is missing.")
            raise ValueError("Telegram Bot Token is required.")
        if not authorized_chat_id:
            logger.error("AUTHORIZED_CHAT_ID is missing or invalid.")
            raise ValueError("Authorized Chat ID is required and must be an integer.")

        self.authorized_chat_id = authorized_chat_id
        self.application = Application.builder().token(token).build()
        self.polling_thread = None
        self.is_running = False
        logger.info(f"TelegramBridge initialized for chat ID: {self.authorized_chat_id}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message and update.message.chat_id == self.authorized_chat_id:
            user_message = update.message.text
            logger.info(f"Received message from authorized user: {user_message[:50]}...")
            try:
                with open(TO_AYBAR_FILE, "w", encoding="utf-8") as f:
                    f.write(user_message)
                logger.info(f"Message written to {TO_AYBAR_FILE} for Aybar.")
            except Exception as e:
                logger.error(f"Error writing message to {TO_AYBAR_FILE}: {e}")
        else:
            if update.message:
                logger.warning(
                    f"Ignoring message from unauthorized chat ID: {update.message.chat_id}"
                )

    async def send_message_job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Docstring removed
        job_data = context.job.data
        chat_id = job_data['chat_id']
        text_to_send = job_data['text']
        try:
            await context.bot.send_message(chat_id=chat_id, text=text_to_send)
            logger.info(f"Message successfully sent to chat ID {chat_id} via job_queue: {text_to_send[:50]}...")
        except Exception as e:
            logger.error(f"Error sending message via job_queue to {chat_id}: {e}")

    def poll_for_answer(self):
        # Docstring removed
        logger.info("Answer polling thread started.")
        while self.is_running:
            try:
                if os.path.exists(FROM_AYBAR_FILE):
                    if os.path.getsize(FROM_AYBAR_FILE) > 0:
                        logger.info(f"{FROM_AYBAR_FILE} found and is not empty. Reading content.")
                        answer = ""
                        try:
                            with open(FROM_AYBAR_FILE, "r", encoding="utf-8") as f:
                                answer = f.read().strip()
                        except Exception as e:
                            logger.error(f"Error reading {FROM_AYBAR_FILE}: {e}")
                            time.sleep(1)
                            continue

                        if answer:
                            logger.info(f"Queueing answer for Telegram user: {answer[:50]}...")
                            self.application.job_queue.run_once(self.send_message_job, 0, data={'chat_id': self.authorized_chat_id, 'text': answer})

                        try:
                            os.remove(FROM_AYBAR_FILE)
                            logger.info(f"{FROM_AYBAR_FILE} deleted.")
                        except Exception as e:
                            logger.error(f"Error deleting {FROM_AYBAR_FILE}: {e}")
                    else:
                        pass
            except Exception as e:
                logger.error(f"Error in poll_for_answer loop: {e}")
            time.sleep(1)
        logger.info("Answer polling thread stopped.")

    def start(self):
        # Docstring removed
        self.is_running = True

        message_handler_instance = MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=[self.authorized_chat_id]),
            self.handle_message
        )
        self.application.add_handler(message_handler_instance)

        self.polling_thread = threading.Thread(target=self.poll_for_answer, daemon=True)
        self.polling_thread.start()

        logger.info("Starting Telegram bot polling...")
        try:
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.critical(f"Telegram bot polling failed critically: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        # Docstring removed
        logger.info("Stopping Telegram interface...")
        self.is_running = False
        if self.application and hasattr(self.application, 'stop') and self.application.is_running:
            logger.info("Application stop method available (actual async stop not implemented here for simplicity).")
            pass

        if self.polling_thread and self.polling_thread.is_alive():
            logger.info("Waiting for polling thread to join...")
            self.polling_thread.join(timeout=5)
            if self.polling_thread.is_alive():
                logger.warning("Polling thread did not join in time.")
        logger.info("Telegram interface stopped.")

if __name__ == "__main__":
    logger.info("Telegram Interface Script starting...")
    load_script_config() # Load config from file first

    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.info("TELEGRAM_BOT_TOKEN not found in environment variables. Trying config.json...")
        TOKEN = SCRIPT_CONFIG.get("TELEGRAM_BOT_TOKEN")
        if not TOKEN or TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE_OR_LEAVE_EMPTY_IF_USING_ENV_VAR":
            logger.critical("Fatal: TELEGRAM_BOT_TOKEN not found in environment variables or config.json, or is a placeholder.")
            sys.exit(1)

    AUTH_CHAT_ID_STR = os.getenv("AUTHORIZED_CHAT_ID")
    if not AUTH_CHAT_ID_STR:
        logger.info("AUTHORIZED_CHAT_ID not found in environment variables. Trying config.json...")
        AUTH_CHAT_ID_STR = SCRIPT_CONFIG.get("AUTHORIZED_CHAT_ID")
        if not AUTH_CHAT_ID_STR or AUTH_CHAT_ID_STR == "YOUR_AUTHORIZED_CHAT_ID_HERE_OR_LEAVE_EMPTY_IF_USING_ENV_VAR":
            logger.critical("Fatal: AUTHORIZED_CHAT_ID not found in environment variables or config.json, or is a placeholder.")
            sys.exit(1)

    AUTHORIZED_CHAT_ID = None
    try:
        AUTHORIZED_CHAT_ID = int(AUTH_CHAT_ID_STR)
    except ValueError:
        logger.critical(f"Fatal: AUTHORIZED_CHAT_ID ('{AUTH_CHAT_ID_STR}') is not a valid integer.")
        sys.exit(1)

    if not AUTHORIZED_CHAT_ID: # Should be caught by int conversion or previous checks, but as a safeguard
        logger.critical("Fatal: AUTHORIZED_CHAT_ID is not set after all checks.")
        sys.exit(1)

    bridge = TelegramBridge(token=TOKEN, authorized_chat_id=AUTHORIZED_CHAT_ID)
    try:
        bridge.start()
    except KeyboardInterrupt:
        logger.info("Telegram Interface interrupted by user (Ctrl+C).")
    except Exception as e:
        logger.critical(f"An unhandled exception occurred in Telegram Interface: {e}", exc_info=True)
    finally:
        bridge.stop()
        logger.info("Telegram Interface has shut down.")
