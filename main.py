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
    return 'Hello, Flask is running on port 8000!'

# Initialize bot globally
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
client = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Track last progress message time per chat
last_progress_time = {}
# Track ongoing downloads per chat
active_downloads = {}

# FFmpeg metadata extractor
def get_video_metadata(file_path):
    try:
        cmd = ["ffmpeg", "-i", file_path, "-hide_banner"]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        output = result.stderr

        duration = 0
        for line in output.splitlines():
            if "Duration" in line:
                duration_str = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = duration_str.split(":")
                duration = int(float(h) * 3600 + float(m) * 60 + float(s))
                break

        thumb_path = file_path + "_thumb.jpg"
        subprocess.run(["ffmpeg", "-ss", "00:00:01", "-i", file_path, "-frames:v", "1", "-q:v", "2", thumb_path])

        return duration, thumb_path if os.path.exists(thumb_path) else None

    except Exception:
        return 0, None

async def progress(current, total, message: Message, filename):
    now = time.time()
    chat_id = message.chat.id
    last = last_progress_time.get(chat_id, 0)

    if now - last < 10:
        return

    last_progress_time[chat_id] = now
    percent = int(current * 100 / total)
    bar = "▰" * (percent // 5) + "▱" * (20 - percent // 5)
    uploaded = round(current / (1024 * 1024), 2)
    total_mb = round(total / (1024 * 1024), 2)

    try:
        await message.edit_text(
            f"📤 Uploading `{filename}`\n\n"
            f"{bar} {percent}%\n"
            f"📦 {uploaded}/{total_mb} MB"
        )
    except:
        pass

@client.on_message(filters.command("cancel") & filters.private)
async def cancel_handler(client, message: Message):
    chat_id = message.chat.id
    if chat_id in active_downloads:
        process = active_downloads[chat_id]
        process.terminate()
        del active_downloads[chat_id]
        await message.reply("❌ Download cancelled.")
    else:
        await message.reply("⚠️ No active download found.")

@client.on_message(filters.command("upload") & filters.private)
async def mega_handler(client, message: Message):
    url = message.text.split(" ", 1)[1] if " " in message.text else None
    if not url:
        return await message.reply("❌ Send a valid MEGA URL.")

    status = await message.reply("📥 Downloading from MEGA...")
    filename = "video.mp4"
    filepath = f"/app/{filename}"

    try:
        cmd = ["megadl", url, "--path", filepath]
        process = subprocess.Popen(cmd)
        active_downloads[message.chat.id] = process
        process.wait()
    except Exception as e:
        return await status.edit(f"❌ Download failed: {e}")
    finally:
        active_downloads.pop(message.chat.id, None)

    if not os.path.exists(filepath):
        return await status.edit("❌ Download failed.")

    await status.edit("✅ Download complete. Preparing to upload...")

    try:
        duration, thumb = get_video_metadata(filepath)
        await client.send_video(
            chat_id=message.chat.id,
            video=filepath,
            duration=duration if duration else None,
            thumb=thumb if thumb else None,
            caption=f"✅ Uploaded `{filename}`",
            progress=progress,
            progress_args=(status, filename)
        )

        if thumb and os.path.exists(thumb):
            os.remove(thumb)
        os.remove(filepath)

    except Exception as e:
        await status.edit(f"❌ Upload failed: {e}")

client.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
