import os
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📽️ Send me a video (MP4/WEBM), and I'll upscale it to 4K!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("⚠️ Please send a valid video file.")
        return

    file_id = video.file_id
    new_filename = f"{file_id}_input.mp4"
    output_filename = f"{file_id}_4k.mp4"

    await update.message.reply_text("📥 Downloading your video...")
    file = await context.bot.get_file(file_id)
    await file.download_to_drive(new_filename)

    await update.message.reply_text("⏳ Converting to 4K... Please wait.")

    try:
        # Run FFmpeg command
        ffmpeg_command = [
            "ffmpeg", "-y", "-i", new_filename,
            "-vf", "scale=3840:2160",
            "-c:v", "libx264", "-preset", "slow", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            output_filename
        ]
        process = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if process.returncode != 0:
            raise Exception(process.stderr)

        await update.message.reply_text("✅ Conversion complete. Uploading now...")
        with open(output_filename, "rb") as video_file:
            await update.message.reply_video(video=video_file, caption="🎉 Here is your 4K video!")

    except Exception as e:
        await update.message.reply_text(f"❌ Conversion failed:\n{str(e).strip()[:300]}")

    finally:
        # Cleanup
        if os.path.exists(new_filename):
            os.remove(new_filename)
        if os.path.exists(output_filename):
            os.remove(output_filename)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()
