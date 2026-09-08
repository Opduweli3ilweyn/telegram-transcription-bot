import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from groq import Groq

# --- YOUR API KEYS ---
TELEGRAM_BOT_TOKEN = "8940816231:AAGMNZxv92WaY0hMuK8eduY1q0cVD0lTmOo"
GROQ_API_KEY = "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"

# --- DUMMY WEB SERVER FOR RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Dummy web server listening on port {port}")
    server.serve_forever()

# --- BOT HANDLERS ---
async def start(update, context):
    await update.message.reply_text("مرحباً! أرسل لي رابط فيديو يوتيوب لتفريغه إلى نص عربي.")

async def handle_message(update, context):
    await update.message.reply_text("جاري معالجة الرابط، يرجى الانتظار...")

def main():
    # Start the dummy web server in a background thread
    threading.Thread(target=run_web_server, daemon=True).start()

    # Start the Telegram bot polling
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Telegram Bot is running live!")
    app.run_polling()

if __name__ == "__main__":
    main()
