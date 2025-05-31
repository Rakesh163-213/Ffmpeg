import os
import shutil
import subprocess
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, BOT_TOKEN
from moviepy.editor import VideoFileClip

DOWNLOAD_DIR = "./downloads"

# Track upload progress
last_progress_time = {}
last_progress_bytes = {}

app = Client(
    "mega_bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Determine if file is video
def is_video(file_path):
    return file_path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi', '.webm'))

# Create thumbnail
def create_thumbnail(video_path, thumb_path):
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-ss", "00:00:01.000", "-vframes", "1",
        thumb_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Get duration using moviepy
def get_video_duration(path):
    clip = VideoFileClip(path)
    return int(clip.duration)

# Upload progress with speed and ETA
async def progress(current, total, message: Message, file_name):
    now = time.time()
    chat_id = message.chat.id

    prev_time = last_progress_time.get(chat_id, now)
    prev_bytes = last_progress_bytes.get(chat_id, 0)

    elapsed = max(now - prev_time, 1e-5)
    speed = (current - prev_bytes) / elapsed
    speed_mb = round(speed / (1024 * 1024), 2)

    remaining = total - current
    eta_str = time.strftime("%M:%S", time.gmtime(int(remaining / speed))) if speed > 0 else "Calculating..."

    last_progress_time[chat_id] = now
    last_progress_bytes[chat_id] = current

    percent = int(current * 100 / total)
    bar_len = 20
    filled_len = percent * bar_len // 100
    bar = "▰" * filled_len + "▱" * (bar_len - filled_len)

    uploaded_mb = round(current / (1024 * 1024), 2)
    total_mb = round(total / (1024 * 1024), 2)

    await message.edit_text(
        f"📤 Uploading `{file_name}`\n\n"
        f"{bar} {percent}%\n"
        f"📦 {uploaded_mb}/{total_mb} MB\n"
        f"⚡️ Speed: {speed_mb} MB/s\n"
        f"⏳ ETA: {eta_str}"
    )

# Handle MEGA.nz links
@app.on_message(filters.private & filters.text)
async def mega_handler(client: Client, message: Message):
    text = message.text

    if "mega.nz" in text:
        status = await message.reply_text("📥 Downloading from MEGA...")

        try:
            if not os.path.exists(DOWNLOAD_DIR):
                os.makedirs(DOWNLOAD_DIR)

            cmd = f"megatools dl --path={DOWNLOAD_DIR} '{text}'"
            subprocess.run(cmd, shell=True, check=True)

            for root, dirs, files in os.walk(DOWNLOAD_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_msg = await message.reply_text("📤 Uploading...")

                    await client.send_chat_action(message.chat.id, ChatAction.UPLOAD_DOCUMENT)

                    if is_video(file_path):
                        thumb_path = os.path.join(DOWNLOAD_DIR, "thumb.jpg")
                        create_thumbnail(file_path, thumb_path)
                        duration = get_video_duration(file_path)

                        await client.send_video(
                            chat_id=message.chat.id,
                            video=file_path,
                            caption=f"✅ Uploaded: `{file}`",
                            duration=duration,
                            thumb=thumb_path,
                            supports_streaming=True,
                            progress=progress,
                            progress_args=(file_msg, file)
                        )
                        os.remove(thumb_path)
                    else:
                        await client.send_document(
                            chat_id=message.chat.id,
                            document=file_path,
                            caption=f"✅ Uploaded: `{file}`",
                            progress=progress,
                            progress_args=(file_msg, file)
                        )

                    os.remove(file_path)

            shutil.rmtree(DOWNLOAD_DIR)

        except Exception as e:
            await status.edit_text(f"❌ Error: {str(e)}")

    else:
        await message.reply_text("❗ Please send a valid mega.nz link.")

app.run()
