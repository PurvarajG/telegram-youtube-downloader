import os
import re
import time
import asyncio
import yt_dlp
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.request import HTTPXRequest

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No token provided! Please add TELEGRAM_BOT_TOKEN to your .env file.")

# Allow users to customize their save path via the .env file, defaulting to Downloads
SAVE_DIRECTORY = os.getenv("SAVE_DIRECTORY", os.path.expanduser("~/Downloads")) 

if not os.path.exists(SAVE_DIRECTORY):
    os.makedirs(SAVE_DIRECTORY)

# --- UTILS ---
def get_progress_bar(percentage):
    blocks = int(percentage / 10)
    return "█" * blocks + "▒" * (10 - blocks)

def clean_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def progress_hook(d, status_msg, context, loop):
    """Updates UI during the yt-dlp DOWNLOAD phase"""
    if d['status'] == 'downloading':
        current_time = time.time()
        last_edit_time = context.user_data.get('last_edit_time', 0)
        
        if current_time - last_edit_time > 3:
            context.user_data['last_edit_time'] = current_time
            percentage_str = clean_ansi(d.get('_percent_str', '0%').replace('%', '').strip())
            try:
                percentage = float(percentage_str)
            except ValueError:
                percentage = 0
                
            eta = clean_ansi(d.get('_eta_str', 'N/A'))
            speed = clean_ansi(d.get('_speed_str', 'N/A'))
            total = clean_ansi(d.get('_total_bytes_str', d.get('_total_bytes_estimate_str', 'N/A')))
            
            bar = get_progress_bar(percentage)
            progress_text = (
                f"📥 *Downloading Media...*\n\n"
                f"`{bar}` {percentage}%\n"
                f"📊 *Size:* {total}\n"
                f"🚀 *Speed:* {speed}\n"
                f"⏳ *ETA:* {eta}"
            )
            
            try:
                asyncio.run_coroutine_threadsafe(
                    context.bot.edit_message_text(
                        chat_id=status_msg.chat_id,
                        message_id=status_msg.message_id,
                        text=progress_text,
                        parse_mode="Markdown"
                    ),
                    loop
                )
            except Exception:
                pass

def download_video_sync(ydl_opts, url):
    """Downloads the file and returns BOTH the file path and the video duration"""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base_name = os.path.splitext(ydl.prepare_filename(info))[0]
        actual_file = None
        for ext in ['.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.wav', '.flac']:
            if os.path.exists(base_name + ext):
                actual_file = base_name + ext
                break
        
        if not actual_file:
            actual_file = ydl.prepare_filename(info)
            
        duration = info.get('duration', 1) 
        return actual_file, duration

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 *YouTube Downloader Pro*\nSend me a link to get started.", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Please send a valid YouTube link.")
        return
    context.user_data['current_url'] = url
    
    keyboard = [
        [InlineKeyboardButton("🎥 4K (2160p)", callback_data='res_2160'), InlineKeyboardButton("🎥 2K (1440p)", callback_data='res_1440')],
        [InlineKeyboardButton("🎬 HD (1080p)", callback_data='res_1080'), InlineKeyboardButton("🎬 HD (720p)", callback_data='res_720')],
        [InlineKeyboardButton("📱 SD (480p)", callback_data='res_480'), InlineKeyboardButton("🎵 Audio Only", callback_data='res_audio')]
    ]
    await update.message.reply_text("Step 1: Select Quality", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("res_"):
        res = data.split("_")[1]
        context.user_data['selected_res'] = res
        
        if res == 'audio':
            keyboard = [
                [InlineKeyboardButton("🎵 MP3 (Standard)", callback_data='codec_mp3')],
                [InlineKeyboardButton("🍎 M4A (Apple Devices)", callback_data='codec_m4a')],
                [InlineKeyboardButton("💿 WAV (Lossless Uncompressed)", callback_data='codec_wav')],
                [InlineKeyboardButton("🎛️ FLAC (Lossless High-Res)", callback_data='codec_flac')]
            ]
            await query.edit_message_text("Step 2: Select Audio Format", reply_markup=InlineKeyboardMarkup(keyboard))
            return
            
        keyboard = [
            [InlineKeyboardButton("AV1 (High Efficiency / Best Size)", callback_data='codec_av1')],
            [InlineKeyboardButton("VP9 (Standard Web Format)", callback_data='codec_vp9')],
            [InlineKeyboardButton("H.264 (Native YouTube)", callback_data='codec_h264_native')],
            [InlineKeyboardButton("H.264 (Forced Transcode / Max Compatibility)", callback_data='codec_h264_transcode')]
        ]
        await query.edit_message_text(f"Step 2: Select Video Codec for {res}p", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("codec_"):
        codec = data.replace("codec_", "")
        await start_download(query, context, codec)

async def start_download(query, context, codec):
    res = context.user_data.get('selected_res')
    url = context.user_data.get('current_url')
    loop = asyncio.get_running_loop()

    os.environ["PATH"] += os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"

    ydl_opts = {
        'outtmpl': f'{SAVE_DIRECTORY}/%(title)s.%(ext)s',
        'progress_hooks': [lambda d: progress_hook(d, status_msg, context, loop)],
        'noplaylist': True,
        'quiet': True,
        'overwrites': True,
        'extractor_args': {'youtube': ['player_client=android,ios']},
    }

    display_codec = codec.replace('_', ' ').upper()

    if codec in ['mp3', 'm4a', 'wav', 'flac']:
        status_msg = await query.edit_message_text(f"⏳ Fetching Audio as {display_codec}...")
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec}]
        })
        if codec in ['mp3', 'm4a']:
            ydl_opts['postprocessors'][0]['preferredquality'] = '192'
            
    elif codec == 'av1':
        status_msg = await query.edit_message_text(f"⏳ Fetching {res}p in AV1...")
        ydl_opts.update({'format': f'bestvideo[height={res}][vcodec^=av01]+bestaudio/best[height={res}][vcodec^=av01]', 'merge_output_format': 'mp4'})
    elif codec == 'vp9':
        status_msg = await query.edit_message_text(f"⏳ Fetching {res}p in VP9...")
        ydl_opts.update({'format': f'bestvideo[height={res}][vcodec^=vp9]+bestaudio/best[height={res}][vcodec^=vp9]', 'merge_output_format': 'mp4'})
    elif codec == 'h264_native':
        status_msg = await query.edit_message_text(f"⏳ Fetching {res}p in Native H.264...")
        ydl_opts.update({'format': f'bestvideo[height={res}][vcodec^=avc1]+bestaudio/best[height={res}][vcodec^=avc1]', 'merge_output_format': 'mp4'})
    elif codec == 'h264_transcode':
        status_msg = await query.edit_message_text(f"⏳ Fetching {res}p to transcode to H.264...")
        ydl_opts.update({'format': f'bestvideo[height={res}]+bestaudio/best[height={res}]'})

    try:
        raw_file, duration = await asyncio.to_thread(download_video_sync, ydl_opts, url)
        final_file = raw_file

        if codec == 'h264_transcode':
            final_file = os.path.splitext(raw_file)[0] + "-H264.mp4" # Hyphen prevents Markdown crashes
            
            await context.bot.edit_message_text(
                chat_id=query.message.chat_id,
                message_id=status_msg.message_id,
                text=f"✅ *Download 100%*\n\n⚙️ *Initializing H.264 Transcoder...*\n_Analyzing {duration} seconds of video._",
                parse_mode="Markdown"
            )

            # NOTE: If FFmpeg silently fails, replace 'ffmpeg' below with your absolute path (e.g., '/opt/homebrew/bin/ffmpeg')
            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-y', '-i', raw_file, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-c:a', 'aac', final_file,
                stderr=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE
            )

            time_regex = re.compile(r"time=\s*(\d+):(\d+):([\d\.]+)")
            last_ui_update = time.time()

            while True:
                try:
                    line = await process.stderr.readuntil(b'\r')
                except asyncio.exceptions.IncompleteReadError as e:
                    line = e.partial

                if not line:
                    break
                
                line_str = line.decode('utf-8', errors='ignore')
                match = time_regex.search(line_str)
                
                if match:
                    h, m, s = match.groups()
                    current_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    percentage = min(100.0, round((current_seconds / duration) * 100, 1))
                    
                    if time.time() - last_ui_update > 3:
                        last_ui_update = time.time()
                        bar = get_progress_bar(percentage)
                        
                        text = (
                            f"⚙️ *Transcoding to H.264...*\n\n"
                            f"`{bar}` {percentage}%\n"
                            f"🎬 *Processed:* `{int(current_seconds)}s / {int(duration)}s`\n"
                            f"_CPU is processing the media file._"
                        )
                        try:
                            await context.bot.edit_message_text(
                                chat_id=status_msg.chat_id,
                                message_id=status_msg.message_id,
                                text=text,
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
            
            await process.wait()
            
            if os.path.exists(raw_file):
                os.remove(raw_file)

        size_mb = os.path.getsize(final_file) / (1024 * 1024)
        safe_filename = os.path.basename(final_file).replace('_', '-') # Extra safety for Telegram Markdown
        
        # 1. Update the loading message so it stops spinning
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=f"✅ *Processing Complete*\n_Check below for file details._",
            parse_mode="Markdown"
        )
        
        # 2. Send a BRAND NEW message to trigger a push notification
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🎉 *ALL DONE!*\n\n📂 `{safe_filename}` ({size_mb:.1f}MB)\n⚙️ *Format:* {display_codec}\n📍 *Saved to your Downloads folder.*",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        error_msg = str(e)
        if "Requested format is not available" in error_msg:
            friendly_error = f"❌ **Format Unavailable**\n\nYouTube does not have a {res}p file available for this specific video."
        else:
            friendly_error = f"❌ Error:\n`{error_msg}`"
            
        await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=status_msg.message_id, text=friendly_error, parse_mode="Markdown")

def main():
    t_request = HTTPXRequest(connection_pool_size=8, connect_timeout=60.0, read_timeout=60.0)
    app = Application.builder().token(TOKEN).request(t_request).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print(f"🚀 Bot is active and listening! Saving to {SAVE_DIRECTORY}")
    app.run_polling()

if __name__ == '__main__':
    main()