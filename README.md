# 🎬 YouTube Downloader Pro Telegram Bot

A full-featured Telegram bot that downloads YouTube videos and audio directly to your local machine. Supports resolution selection, audio extraction, format conversion, and a live updating progress bar.

---

## Prerequisites

1. **Python 3.8+**
2. **FFmpeg** — required for audio extraction and format transcoding (H.264).
   - **Mac:** `brew install ffmpeg`
   - **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add to your system PATH.
   - **Linux:** `sudo apt install ffmpeg`
3. A **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)

---

## Installation & Setup

**1. Clone the repository:**
```bash
git clone https://github.com/PurvarajG/telegram-youtube-downloader.git
cd telegram-youtube-downloader
```

**2. Install Python dependencies:**
```bash
pip install -r requirements.txt
```

**3. Create your `.env` file:**

Create a file named `.env` in the project root and add the following:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
SAVE_DIRECTORY=/path/to/your/save/folder
```

- `TELEGRAM_BOT_TOKEN` — get this from [@BotFather](https://t.me/BotFather) on Telegram (**required**)
- `SAVE_DIRECTORY` — where downloads are saved. Defaults to `~/Downloads` if not set (**optional**)

**4. Run the bot:**
```bash
python ytbot.py
```

You should see: `🚀 Bot is active and listening!`

---

## Usage

1. Open Telegram and start a chat with your bot
2. Send `/start`
3. Paste any YouTube link
4. Select your desired **quality** (4K → SD or Audio Only)
5. Select your **codec / format**
6. The bot will download the file and save it to your configured directory, with a live progress bar throughout

---

## Supported Formats

| Type  | Options |
|-------|---------|
| Video | 4K (2160p), 2K (1440p), 1080p, 720p, 480p |
| Codec | AV1, VP9, H.264 Native, H.264 Transcode |
| Audio | MP3, M4A, WAV, FLAC |

---

## Notes

- Files are saved **locally to the machine running the bot**, not sent back via Telegram
- H.264 Transcode uses FFmpeg and will take longer than native formats
- If FFmpeg isn't found, ensure it's on your system PATH or set the absolute path in `ytbot.py`
