import os
import time
import asyncio
import subprocess
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return '✅ Flask server is running!'

# Flask thread
def run_flask():
    app.run(host="0.0.0.0", port=8066)

# Bot setup
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOAD_DIR = "/app/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

last_progress = {}
user_cancelled = {}


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
        subprocess.run([
            "ffmpeg", "-ss", "00:00:01", "-i", file_path,
            "-frames:v", "1", "-q:v", "2", thumb_path
        ])
        return duration, thumb_path if os.path.exists(thumb_path) else None
    except Exception:
        return 0, None


async def upload_progress(current, total, message: Message, start_time, filename):
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

@client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply("👋 Send me a MEGA URL to start downloading and uploading it to Telegram\nUse /cancel to cancel the task(may not work properly!).")

@client.on_message(filters.command("cancel") & filters.private)
async def cancel_upload(client, message: Message):
    user_cancelled[message.chat.id] = True
    await message.reply("❌ Upload cancelled. It will stop shortly.")

@client.on_message(filters.private & filters.regex(r'https?://mega\.nz/\S+'))
async def handle_mega(client, message: Message):
    url = message.text.strip()
    status = await message.reply("📥 Starting MEGA download...")

    user_cancelled[message.chat.id] = False

    try:
        cmd = f"megadl '{url}' --path {DOWNLOAD_DIR}"
        proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return await status.edit(f"❌ Download failed:\n{stderr.decode()}")

    except Exception as e:
        return await status.edit(f"❌ Download error: {e}")

    files = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".mp4")]
    if not files:
        return await status.edit("❌ No video files found.")

    for filepath in files:
        if user_cancelled.get(message.chat.id):
            await status.edit("⛔ Upload cancelled.")
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
                progress=upload_progress,
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

# Run Flask + Bot
if __name__ == "__main__":
    Thread(target=run_flask).start()
    client.run()
    
