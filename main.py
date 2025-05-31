import os
import time
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return '✅ Bot is running!'

def run_flask():
    app.run(host="0.0.0.0", port=8000)

Thread(target=run_flask).start()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

cancel_flags = {}
last_progress_time = {}

def get_video_metadata(file_path):
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", file_path, "-hide_banner"],
            stderr=subprocess.PIPE, text=True
        )
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
    except:
        return 0, None

async def progress(current, total, message: Message, filename):
    now = time.time()
    chat_id = message.chat.id
    last = last_progress_time.get(chat_id, {"time": 0, "bytes": 0})
    if now - last["time"] < 10:
        return
    time_diff = now - last["time"]
    byte_diff = current - last["bytes"]
    speed = byte_diff / time_diff if time_diff > 0 else 0
    last_progress_time[chat_id] = {"time": now, "bytes": current}
    percent = int(current * 100 / total)
    bar = "▰" * (percent // 5) + "▱" * (20 - percent // 5)
    uploaded = round(current / (1024 * 1024), 2)
    total_mb = round(total / (1024 * 1024), 2)
    speed_str = f"{round(speed / 1024 / 1024, 2)} MB/s"
    try:
        await message.edit_text(
            f"📤 Uploading `{filename}`\n\n"
            f"{bar} {percent}%\n"
            f"📦 {uploaded}/{total_mb} MB\n"
            f"🚀 Speed: {speed_str}"
        )
    except:
        pass

@client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    await message.reply("👋 Send a MEGA link and I’ll download & upload it here.")

@client.on_message(filters.command("cancel") & filters.private)
async def cancel_handler(client, message):
    cancel_flags[message.chat.id] = True
    await message.reply("❌ Cancelled.")

@client.on_message(filters.private & filters.text & filters.regex(r"https?://mega\.nz/"))
async def mega_handler(client, message: Message):
    url = message.text.strip()
    chat_id = message.chat.id
    cancel_flags[chat_id] = False

    status = await message.reply("📥 Downloading from MEGA...")

    download_dir = "/app/downloads"
    os.makedirs(download_dir, exist_ok=True)

    try:
        result = subprocess.run(
            ["megadl", url],
            cwd=download_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            return await status.edit(f"❌ Download failed:\n{result.stderr}")

        files = os.listdir(download_dir)
        if not files:
            return await status.edit("❌ No file found after download.")
        filepath = os.path.join(download_dir, files[0])
        filename = os.path.basename(filepath)

    except Exception as e:
        return await status.edit(f"❌ Download error: {str(e)}")

    if cancel_flags.get(chat_id):
        return await status.edit("❌ Operation cancelled.")

    await status.edit("✅ Download complete. Preparing to upload...")

    try:
        duration, thumb = get_video_metadata(filepath)
        await client.send_video(
            chat_id=chat_id,
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

client.run()
