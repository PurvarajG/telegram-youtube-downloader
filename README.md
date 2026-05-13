# 🎬 YouTube Downloader Pro Telegram Bot

A full-featured Telegram bot that downloads YouTube videos and audio directly to your local machine. It supports resolution selection, audio extraction, format conversion, and features a live updating progress bar.

## Prerequisites
1. **Python 3.8+**
2. **FFmpeg**: This is **required** for audio extraction and format transcoding (H.264).
   - **Mac:** `brew install ffmpeg`
   - **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add to your system PATH.
   - **Linux:** `sudo apt install ffmpeg`

## Installation & Setup

1. **Clone or download the repository:**
   Download the files to a folder on your computer.

2. **Install Python dependencies:**
   Open your terminal/command prompt in the bot's folder and run:
   ```bash
   pip install -r requirements.txt