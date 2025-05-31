import os
import time
import asyncio
import subprocess
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask

# == Flask App ==
app = Flask(__name__)

@app.route('/')
def home():
    return '✅ Flask is running! Bot should be running too.'

def run_flask():
    app.run(host='0.0.0.0', port=8000)

# Start Flask in a separate thread
flask_thread = Thread(target=run_flask)
flask_thread.start()

# == Telegram Bot ==
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

downloads = {}

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
        subprocess.run(["ffmpeg", "-ss", "00:00:01", "-i", file_path,
                        "-frames:v", "1", "-q:v", "2", thumb_path])

        return duration, thumb_path if os.path.exists(thumb_path) else None

    except Exception:
        return 0, None

last_progress_time = {}

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
async def cancel_download(client, message: Message):
    user_id = message.from_user.id
    process = downloads.get(user_id)
    if process:
        process.terminate()
        downloads.pop(user_id)
        await message.reply("❌ Download canceled.")
    else:
        await message.reply("⚠️ No active download to cancel.")

@client.on_message(filters.private & filters.text)
async def handle_mega_url(client, message: Message):
    url = message.text.strip()
    if not url.startswith("https://mega.nz"):
        return await message.reply("❌ Please send a valid MEGA URL.")

    status = await message.reply("📥 Downloading from MEGA...")

    filename = f"video_{message.from_user.id}.mp4"
    filepath = os.path.join("/app", filename)

    try:
        user_id = message.from_user.id
        downloads[user_id] = subprocess.Popen(["megadl", url, "--path", "."])

        while downloads[user_id].poll() is None:
            await asyncio.sleep(5)

        downloads.pop(user_id)

        downloaded_file = next((f for f in os.listdir(".") if f.endswith(".mp4")), None)
        if not downloaded_file:
            return await status.edit("❌ Download failed.")

        duration, thumb = get_video_metadata(downloaded_file)

        await client.send_video(
            chat_id=message.chat.id,
            video=downloaded_file,
            duration=duration if duration else None,
            thumb=thumb if thumb else None,
            caption=f"✅ Uploaded `{downloaded_file}`",
            progress=progress,
            progress_args=(status, downloaded_file)
        )

        if thumb and os.path.exists(thumb):
            os.remove(thumb)
        os.remove(downloaded_file)

    except Exception as e:
        await status.edit(f"❌ Upload failed: {e}")

client.run()
        
