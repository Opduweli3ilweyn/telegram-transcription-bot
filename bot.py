import os
import threading
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from groq import Groq
import yt_dlp

# Set up API Keys (Can also be set in Render Environment Variables)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8940816231:AAGMNZxv92WaY0hMuK8eduY1q0cVD0lTmOo")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")

client = Groq(api_key=GROQ_API_KEY)

# --- DUMMY WEB SERVER FOR RENDER HEALTH CHECK ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot status: Active")

    def log_message(self, format, *args):
        return  # Silence HTTP access logs in console

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health check server listening on port {port}")
    server.serve_forever()

# --- YOUTUBE DOWNLOAD FUNCTION ---
def download_audio_from_youtube(url, output_path):
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '128',
        }],
        # Bypass YouTube Bot/Datacenter IP Blocks
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web'],
                'skip': ['hls', 'dash']
            }
        },
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# --- TELEGRAM HANDLERS ---
async def start(update, context):
    await update.message.reply_text("مرحباً! أرسل لي رابط فيديو يوتيوب لتفريغه إلى نص عربي.")

async def handle_message(update, context):
    text = update.message.text
    if "youtube.com" not in text and "youtu.be" not in text:
        await update.message.reply_text("يرجى إرسال رابط يوتيوب صحيح.")
        return

    status_msg = await update.message.reply_text("جاري تنزيل الصوت وتحليله عبر Groq Whisper... ⏳")

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file_base = os.path.join(tmpdir, "audio")
        expected_file = audio_file_base + ".m4a"

        try:
            # Download Youtube Audio
            download_audio_from_youtube(text, audio_file_base)

            if not os.path.exists(expected_file):
                raise FileNotFoundError("فشل حفظ ملف الصوت.")

            # Send to Groq Whisper AI API
            with open(expected_file, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(expected_file), file.read()),
                    model="whisper-large-v3",
                    language="ar",
                    response_format="text"
                )

            full_text = str(transcription).strip()

            if not full_text:
                await status_msg.edit_text("لم يتم العثور على كلام قابل للتفريغ في هذا الفيديو.")
                return

            await status_msg.edit_text("تم تفريغ النص بنجاح! 👇")

            # Split response if transcript exceeds Telegram message limits (4000 characters)
            for i in range(0, len(full_text), 4000):
                await update.message.reply_text(full_text[i:i+4000])

        except Exception as e:
            await status_msg.edit_text(f"حدث خطأ أثناء التفريغ:\n`{str(e)}`", parse_mode="Markdown")

def main():
    # Run HTTP Server in background thread
    threading.Thread(target=run_web_server, daemon=True).start()

    # Run Telegram Polling Bot
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Telegram Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
