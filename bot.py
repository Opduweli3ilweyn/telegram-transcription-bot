import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# --- YOUR HARDCODED API KEYS ---
TELEGRAM_BOT_TOKEN = "8940816231:AAGMNZxv92WaY0hMuK8eduY1q0cVD0lTmOo"
GROQ_API_KEY = "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"

groq_client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **أهلاً بك!**\n\n"
        "أرسل لي أي رابط يوتيوب (مهما كان طوله) وسأقوم باستخراج الصوت وتفريغه إلى نص عربي."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if "youtu" not in url:
        return

    status_msg = await update.message.reply_text("⏳ **جاري استخراج الصوت من يوتيوب...**")
    
    chat_id = update.message.chat_id
    audio_file = f"audio_{chat_id}.mp3"
    txt_file = f"transcript_{chat_id}.txt"

    try:
        ydl_opts = {
            'format': 'ba/b',
            'outtmpl': audio_file,
            'overwrites': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '32',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await status_msg.edit_text("🎙️ **جاري تفريغ الصوت العربي باستخدام ذكاء Whisper...**")

        with open(audio_file, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_file, file.read()),
                model="whisper-large-v3",
                language="ar",
                response_format="text"
            )

        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(transcription)

        await status_msg.edit_text("📤 **تم التفريغ بنجاح! جاري إرسال الملف...**")

        preview = transcription[:400] + "..." if len(transcription) > 400 else transcription
        
        await update.message.reply_text(f"✅ **معاينة النص:**\n\n{preview}")
        with open(txt_file, "rb") as doc:
            await update.message.reply_document(document=doc, filename="تفريغ_صوتي.txt")

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ **حدث خطأ:** {str(e)}")

    finally:
        for f in [audio_file, txt_file]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Telegram Bot is running live!")
    app.run_polling()
