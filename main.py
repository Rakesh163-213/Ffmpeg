import os
import time
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '✅ Flask is running. Bot is alive!'

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

last_progress = {}
user_cancelled = {}

DOWNLOAD_DIR = "/app/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_video_metadata(file_path):
    try:
        cmd = ["ffmpeg", "-i", file_path, "-hide_banner"]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        output = result.stderr

        # Duration
        duration = 0
        for line in output.splitlines():
            if "Duration" in line:
                duration_str = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = duration_str.split(":")
                duration = int(float(h) * 3600 + float(m) * 60 + float(s))
                break

        # Thumbnail
        thumb_path = file_path + "_thumb.jpg"
        subprocess.run(["ffmpeg", "-ss", "00:00:01", "-i", file_path, "-frames:v", "1", "-q:v", "2", thumb_path])
        return duration, thumb_path if os.path.exists(thumb_path) else None
    except Exception:
        return 0, None

async def progress(current, total, message: Message, start_time, filename):
    now = time.time()
    last = last_progress.get(message.chat.id, 0)

    if now - last < 2:
        return

    last_progress[message.chat.id] = now
    percent = int(current * 100 / total)
    bar = "▰" * (percent // 5) + "▱" * (20 - percent // 5)
    uploaded = round(current / (1024 * 1024), 2)
    total_mb = round(total / (1024 * 1024), 2)
    elapsed = now - start_time
    speed = round((uploaded / elapsed), 2) if elapsed else 0.0

    try:
        await message.edit_text(
            f"📤 Uploading `{filename}`\n\n"
            f"{bar} {percent}%\n"
            f"📦 {uploaded}/{total_mb} MB\n"
            f"🚀 Speed: {speed} MB/s"
        )
    except:
        pass

@client.on_message(filters.command("cancel") & filters.private)
async def cancel_upload(client, message: Message):
    user_cancelled[message.chat.id] = True
    await message.reply("❌ Upload cancelled.")

@client.on_message(filters.private & filters.regex(r'https?://mega\.nz/\S+'))
async def handle_mega(client, message: Message):
    url = message.text.strip()
    status = await message.reply("📥 Starting MEGA download...")

    # Reset cancel
    user_cancelled[message.chat.id] = False

    # Run megadl with --path as directory to allow multiple files
    try:
        subprocess.run(f"megadl '{url}' --path {DOWNLOAD_DIR}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return await status.edit(f"❌ Download failed:\n{e}")

    # Find downloaded files
    files = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".mp4")]
    if not files:
        return await status.edit("❌ No video files found.")

    for filepath in files:
        if user_cancelled.get(message.chat.id):
            break

        filename = os.path.basename(filepath)

        if not os.path.exists(filepath):
            continue

        await status.edit(f"✅ Downloaded `{filename}`. Preparing upload...")

        try:
            duration, thumb = get_video_metadata(filepath)
            start_time = time.time()

            await client.send_video(
                chat_id=message.chat.id,
                video=filepath,
                caption=f"✅ Uploaded `{filename}`",
                duration=duration,
                thumb=thumb,
                progress=progress,
                progress_args=(status, start_time, filename)
            )

        except Exception as e:
            await status.edit(f"❌ Upload failed: {e}")

        finally:
            try:
                os.remove(filepath)
                if thumb and os.path.exists(thumb):
                    os.remove(thumb)
            except:
                pass

    await status.edit("✅ All done!")

client.run()
