import os
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📽️ Send me a video (WEBM/MP4) and I'll upscale it to 4K MP4.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    file_id = video.file_id
    file = await context.bot.get_file(file_id)

    input_path = f"{file_id}.webm"
    output_path = f"{file_id}_4k.mp4"

    await file.download_to_drive(input_path)
    await update.message.reply_text("⏳ Converting to 4K... Please wait.")

    ffmpeg_command = [
        "ffmpeg", "-i", input_path,
        "-vf", "scale=3840:2160",
        "-c:v", "libx264", "-preset", "slow", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    await update.message.reply_text("✅ Conversion complete. Uploading now...")
    await update.message.reply_video(video=open(output_path, "rb"), caption="🎉 Here is your 4K video!")

    os.remove(input_path)
    os.remove(output_path)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

app.run_polling()
