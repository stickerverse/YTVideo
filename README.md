# Advanced YouTube Downloader

An advanced, modular YouTube video downloader that integrates various tools (Aria2, yt-dlp, Proxy Manager, CAPTCHA solver, Batch downloader) to provide a flexible and efficient download experience.

## Features

- **Multi-threaded Downloads**: Utilize Aria2 for faster, multi-threaded downloads
- **Video Downloads**: Download videos from YouTube and other supported sites using yt-dlp
- **Proxy Integration**: Route downloads through proxies for anonymity and to bypass restrictions
- **CAPTCHA Solving**: Automatically solve CAPTCHAs using third-party services
- **Batch Downloading**: Download multiple videos concurrently

## Installation

### Requirements

- Python 3.7 or higher
- Aria2 (for multi-threaded downloads)

### Install from GitHub

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube_downloader.git
cd youtube_downloader

# Install dependencies
pip install -r requirements.txt

# Install Aria2 (if not already installed)
# For Ubuntu/Debian:
# sudo apt-get install aria2
# For macOS:
# brew install aria2
# For Windows:
# Download from https://github.com/aria2/aria2/releases

# Install the package
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Download a single video
ytdownloader -u "https://www.youtube.com/watch?v=VIDEO_ID"

# Download multiple videos
ytdownloader -u "https://www.youtube.com/watch?v=VIDEO_ID1" "https://www.youtube.com/watch?v=VIDEO_ID2"

# Download videos from a file
ytdownloader -f urls.txt

# Download with proxy
ytdownloader -u "https://www.youtube.com/watch?v=VIDEO_ID" -p "http://user:pass@proxy.example.com:8080"

# Use Aria2 for download
ytdownloader -u "https://www.youtube.com/watch?v=VIDEO_ID" --use-aria2

# Specify output directory
ytdownloader -u "https://www.youtube.com/watch?v=VIDEO_ID" -o /path/to/downloads

# Set video format
ytdownloader -u "https://www.youtube.com/watch?v=VIDEO_ID" --format "bestvideo+bestaudio"
```

### GUI (optional)

```bash
ytdownloader --gui
```

## Configuration

Create a `.env` file in the project root directory with the following variables:

```
# API Key for CAPTCHA solving service (optional)
CAPTCHA_API_KEY=your_2captcha_api_key

# Default download directory
DOWNLOAD_DIR=/path/to/downloads

# Default proxy (optional)
DEFAULT_PROXY=http://user:pass@proxy.example.com:8080

# Aria2 settings
ARIA2_MAX_CONNECTIONS=4
ARIA2_SPLIT=4
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video downloader
- [Aria2](https://aria2.github.io/) - Lightweight multi-protocol & multi-source command-line download utility
- [2Captcha](https://2captcha.com/) - CAPTCHA solving service