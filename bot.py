import os
import threading
import tempfile
import yt_dlp
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from groq import Groq

TELEGRAM_BOT_TOKEN = "8940816231:AAGMNZxv92WaY0hMuK8eduY1q0cVD0lTmOo"
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is active!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

async def start(update, context):
    await update.message.reply_text("مرحباً! أرسل لي رابط فيديو يوتيوب لتفريغه إلى نص عربي.")

def download_audio_from_youtube(url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '128',
        }],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

async def handle_message(update, context):
    text = update.message.text
    if "youtube.com" not in text and "youtu.be" not in text:
        await update.message.reply_text("يرجى إرسال رابط يوتيوب صحيح.")
        return

    status_msg = await update.message.reply_text("جاري تنزيل الصوت وتحليله عبر Groq... ⏳")

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file_base = os.path.join(tmpdir, "audio")
        expected_file = audio_file_base + ".m4a"

        try:
            download_audio_from_youtube(text, audio_file_base)

            with open(expected_file, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(expected_file), file.read()),
                    model="whisper-large-v3",
                    language="ar",
                    response_format="text"
                )

            full_text = str(transcription)

            # Split long transcriptions into 4000-character chunks for Telegram
            for i in range(0, len(full_text), 4000):
                await update.message.reply_text(full_text[i:i+4000])

        except Exception as e:
            await update.message.reply_text(f"حدث خطأ أثناء التفريغ: {str(e)}")

def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
