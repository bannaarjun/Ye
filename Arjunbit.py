import os
import subprocess
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Read your Telegram Bot token from environment variable
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
    exit(1)

# Define video resolutions to convert to
RESOLUTIONS = {
    "360p": "640x360",
    "480p": "854x480",
    "240p": "426x240"
}

# Create directories to store downloads and output files
DOWNLOAD_DIR = "downloads"
OUTPUT_DIR = "outputs"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hi! I am ArjunBot.\n"
        "Send me a video file or document (up to 2GB),\n"
        "and I will convert it to 360p, 480p, and 240p resolutions.\n"
        "Use /Arjun to activate."
    )

def arjun_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Bot activated! Now send me a video file or a document containing a video."
    )

def download_and_convert(update: Update, context: CallbackContext):
    message = update.message
    file_obj = None

    # Check if message has video file or document with video mime type
    if message.video:
        file_obj = message.video.get_file()
        file_name = message.video.file_name or "video.mp4"
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("video"):
        file_obj = message.document.get_file()
        file_name = message.document.file_name or "video.mp4"
    else:
        update.message.reply_text("Please send a valid video file or document containing a video.")
        return

    safe_file_name = file_name.replace(" ", "_")
    local_path = os.path.join(DOWNLOAD_DIR, safe_file_name)

    # Download the file
    update.message.reply_text("Downloading your video, please wait...")
    file_obj.download(custom_path=local_path)
    update.message.reply_text("Download completed. Starting conversion...")

    converted_files = []
    for label, resolution in RESOLUTIONS.items():
        output_file = os.path.join(OUTPUT_DIR, f"{os.path.splitext(safe_file_name)[0]}_{label}.mp4")
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i", local_path,
            "-vf", f"scale={resolution}:force_original_aspect_ratio=decrease",
            "-c:a", "copy",
            output_file
        ]
        try:
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            converted_files.append((label, output_file))
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode() if e.stderr else "Unknown error"
            update.message.reply_text(f"Failed to convert video to {label}: {error_message}")
            cleanup_files([local_path] + [f[1] for f in converted_files])
            return

    # Send back converted videos
    for label, file_path in converted_files:
        with open(file_path, "rb") as f:
            update.message.reply_document(document=InputFile(f), filename=os.path.basename(file_path),
                                         caption=f"Your video in {label} resolution:")

    # Clean up files after sending
    cleanup_files([local_path] + [f[1] for f in converted_files])

def cleanup_files(files):
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

def main():
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("Arjun", arjun_command))
    dispatcher.add_handler(MessageHandler(Filters.video | Filters.document.category("video"), download_and_convert))

    print("Bot started. Waiting for messages...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
  
