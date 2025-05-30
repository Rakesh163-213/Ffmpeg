import os
import subprocess
import mimetypes

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Ensure this is set

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📽️ Send me a video (MP4/WEBM) and I’ll upscale it to 4K.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("⚠️ Please send a valid video file.")
        return

    file_id = video.file_id
    mime_type = video.mime_type or 'video/mp4'
    extension = mimetypes.guess_extension(mime_type) or '.mp4'

    input_path = f"{file_id}{extension}"
    output_path = f"{file_id}_4k.mp4"

    file = await context.bot.get_file(file_id)

    await update.message.reply_text("📥 Downloading your video...")
    await file.download_to_drive(input_path)

    if os.path.getsize(input_path) < 100 * 1024:
        await update.message.reply_text("❌ Downloaded file is too small to be valid.")
        return

    await update.message.reply_text("⏳ Converting to 4K... Please wait.")

    ffmpeg_command = [
        "ffmpeg", "-i", input_path,
        "-vf", "scale=3840:2160",
        "-c:v", "libx264", "-preset", "slow", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) < 100 * 1024:
        error_msg = result.stderr.decode().strip().split('\n')[-10:]
        await update.message.reply_text("❌ Conversion failed:\n" + "\n".join(error_msg))
        os.remove(input_path)
        return

    await update.message.reply_text("✅ Conversion done. Uploading your 4K video...")

    try:
        with open(output_path, "rb") as f:
            await update.message.reply_video(video=f, caption="🎉 Here’s your 4K video!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to upload the video: {str(e)}")

    os.remove(input_path)
    os.remove(output_path)
print("Starting▶️")
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
app.run_polling()
