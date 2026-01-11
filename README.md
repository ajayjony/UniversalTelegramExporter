# Universal Telegram Exporter

<p align="center">
<a href="https://github.com/ajayjony/UniversalTelegramExporter/blob/master/LICENSE"><img alt="License: MIT" src="https://black.readthedocs.io/en/stable/_static/license.svg"></a>
<a href="https://github.com/python/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

<h3 align="center">
  <a href="https://github.com/ajayjony/UniversalTelegramExporter/discussions/categories/ideas">Feature request</a>
  <span> · </span>
  <a href="https://github.com/ajayjony/UniversalTelegramExporter/issues">Report a bug</a>
  <span> · </span>
  Support: <a href="https://github.com/ajayjony/UniversalTelegramExporter/discussions">Discussions</a>
</h3>

## Overview

**Universal Telegram Exporter** is a powerful Python tool that allows you to download and export media files and messages from Telegram conversations, channels, and groups. Built with [Telethon](https://github.com/LonamiWebs/Telethon), it provides a simple yet comprehensive solution for archiving your Telegram data.

### Features

- **Media Download**: Download audio, documents, photos, videos, video notes, and voice messages
- **Message Export**: Export message metadata (text, sender, timestamps) to JSON format
- **Flexible Filtering**: Filter downloads by date range and message count limits
- **File Format Control**: Specify which file formats to download for audio, documents, and videos
- **Custom Download Directories**: Store media in any directory you specify
- **Duplicate Handling**: Automatically manages duplicate files with intelligent naming
- **Session Persistence**: Maintains authentication state across multiple runs
- **Progress Tracking**: Real-time download progress with visual feedback
- **Error Recovery**: Automatic retry mechanism for failed downloads

### Support

| Category | Support |
|--|--|
| **Language** | Python 3.8+ |
| **Download media types** | audio, document, photo, video, video_note, voice |
| **License** | MIT |

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- A Telegram account

### Standard Installation

```bash
git clone https://github.com/ajayjony/UniversalTelegramExporter.git
cd UniversalTelegramExporter
pip install -r requirements.txt
```

### For Development

If you want to contribute or run tests:

```bash
git clone https://github.com/ajayjony/UniversalTelegramExporter.git
cd UniversalTelegramExporter
pip install -r requirements.txt
pip install pytest pytest-cov pylint mypy  # For development/testing
```

To run tests:
```bash
pytest tests/ --cov=. --cov-report=term-missing
```

---

## Configuration

### Setup Configuration

All configurations are passed via the `config.yaml` file.

1. **Copy the example configuration:**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **Get your Telegram API credentials:**
   - Visit [https://my.telegram.org/apps](https://my.telegram.org/apps)
   - Log in with your Telegram account
   - Register a new Telegram application
   - Copy your **api_id** and **api_hash**

3. **Get your chat/channel ID:**

   **Using Web Telegram:**
   - Open https://web.telegram.org/?legacy=1#/im
   - Go to the target chat/channel
   - Extract the ID from the URL:
     - `u853521067_2449618633394` → chat_id: `853521067`
     - `@somename` → chat_id: `@somename` or `somename`
     - `s1301254321_...` → chat_id: `-1001301254321` (add `-100` prefix)
     - `c1301254321_...` → chat_id: `-1001301254321` (add `-100` prefix)

   **Using Bot:**
   - Use [@username_to_id_bot](https://t.me/username_to_id_bot) to get the chat ID

4. **Update `config.yaml` with your credentials:**

```yaml
# Telegram API credentials
api_id: 123456
api_hash: "your_api_hash_here"
chat_id: -1001234567890

# Message tracking (auto-updated)
last_read_message_id: 0
ids_to_retry: []

# Media types to download
media_types:
  - audio
  - document
  - photo
  - video
  - voice
  - video_note

# File format filters
file_formats:
  audio:
    - all
  document:
    - all
  video:
    - all

# Optional: Custom settings
download_directory: null          # Custom download path (absolute or relative)
start_date: null                  # Filter messages after this date (ISO format: '2023-01-01')
end_date: null                    # Filter messages before this date (ISO format)
max_messages: null                # Limit number of media items to download

# Optional: Message export settings
export_messages: false            # Set to true to export message metadata to JSON
export_messages_file: messages_export.json  # Output JSON file name
```

### Configuration Options Explained

| Option | Description | Example |
|--------|-------------|---------|
| `api_id` | Your Telegram API ID | `123456` |
| `api_hash` | Your Telegram API hash | `abc123def456` |
| `chat_id` | Chat/channel/group ID to download from | `-1001234567890` |
| `last_read_message_id` | Last processed message (auto-updated, don't modify) | `0` |
| `ids_to_retry` | Failed message IDs for retry (auto-updated) | `[]` |
| `media_types` | Types of media to download | `[audio, photo, video]` |
| `file_formats` | Specific formats per media type | `{audio: [mp3, m4a]}` |
| `download_directory` | Custom download location | `/path/to/downloads` |
| `start_date` | Download only messages after this date | `2023-01-01` |
| `end_date` | Download only messages before this date | `2023-12-31` |
| `max_messages` | Maximum media items to download | `100` |
| `export_messages` | Export message metadata to JSON | `true` |
| `export_messages_file` | JSON export filename | `messages.json` |

---

## Usage

### Running the Exporter

```bash
python3 main.py
```

### On First Run

1. You'll be prompted to enter your phone number or bot token
2. Telegram will send a verification code
3. Enter the code when prompted
4. Your session will be saved (as `user.session` in the `Output` folder)
5. The downloader will start processing messages

### Download Directories

By default, media is organized by type:

```
Output/
├── user.session              # Telegram session file
└── audio/                    # Audio files
└── document/                 # Documents
└── photo/                    # Photos
└── video/                    # Videos
└── voice/                    # Voice messages
└── video_note/               # Video notes
```

### Custom Download Directory

To store all media in a custom location:

```yaml
download_directory: "/path/to/downloads"
```

The media type subdirectories will still be created within your custom directory.

### Message Export

To export message metadata to JSON:

```yaml
export_messages: true
export_messages_file: "messages.json"
```

The JSON file will contain structured data about each message including:
- Message ID
- Sender information
- Message text
- Timestamps
- Media type (if applicable)

---

## Proxy Support

To use a proxy, add the following to your `config.yaml`:

```yaml
proxy:
  scheme: socks5              # socks4, socks5, or http
  hostname: 11.22.33.44
  port: 1234
  username: your_username     # Optional
  password: your_password     # Optional
```

If your proxy doesn't require authentication, omit the username and password fields.

---

## Examples

### Download all photos from a channel (last 100 messages)

```yaml
chat_id: -1001234567890
media_types: [photo]
max_messages: 100
```

### Download only MP3 audio files

```yaml
media_types: [audio]
file_formats:
  audio: [mp3]
```

### Download all media since January 1, 2023

```yaml
media_types: [audio, photo, video, document]
start_date: "2023-01-01"
```

### Export messages and download videos

```yaml
media_types: [video]
export_messages: true
export_messages_file: "channel_messages.json"
```

---

## Contributing

We welcome contributions! To contribute:

1. **Fork the repository**: Click "Fork" on GitHub
2. **Create a feature branch**: 
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and test thoroughly
4. **Commit with clear messages**: 
   ```bash
   git commit -m "Add: description of changes"
   ```
5. **Push to your fork**: 
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Create a Pull Request** with a detailed description

### Running Tests

Before submitting a PR, ensure all tests pass:

```bash
pip install pytest pytest-cov
pytest tests/ --cov=. --cov-report=term-missing
```

### Code Quality

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Add docstrings to functions and modules
- Include type hints where appropriate
- Write tests for new functionality

### Ways to Contribute

- **Report bugs**: [Open an issue](https://github.com/ajayjony/UniversalTelegramExporter/issues)
- **Request features**: [Start a discussion](https://github.com/ajayjony/UniversalTelegramExporter/discussions)
- **Improve documentation**: Submit a PR with documentation updates
- **Fix bugs**: Submit a PR addressing open issues

---

## Troubleshooting

### File Reference Expired Error

**Problem**: "File reference expired" error during download

**Solution**: The file is automatically re-fetched. If the error persists after 3 retries, the message ID is added to `ids_to_retry` in config and will be attempted on the next run.

### Timeout Errors

**Problem**: Download times out

**Solution**: The exporter automatically retries 3 times with 5-second delays. Check your internet connection if errors persist.

### Authentication Issues

**Problem**: Cannot log in to Telegram

**Solution**: 
- Verify your phone number is correct
- Check your internet connection
- Delete `Output/user.session` and try again
- Ensure your Telegram account isn't restricted

### Import Errors

**Problem**: "ModuleNotFoundError: No module named 'telethon'"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
Copyright (c) 2026 Ajay Jony
Licensed under the MIT License
```

---

## Disclaimer

This tool is provided for educational and archival purposes only. Users are responsible for:

- Complying with Telegram's Terms of Service
- Respecting copyright laws and intellectual property rights
- Obtaining necessary permissions before downloading content
- Ensuring local laws permit the use of this tool

The author is not responsible for misuse of this tool.

---

## Support & Community

- **Discussions**: [GitHub Discussions](https://github.com/ajayjony/UniversalTelegramExporter/discussions)
- **Issues**: [Report a bug](https://github.com/ajayjony/UniversalTelegramExporter/issues)
- **Feature Requests**: [Suggest a feature](https://github.com/ajayjony/UniversalTelegramExporter/discussions/categories/ideas)

---

## Project Status

- **Latest Version**: 1.0.0
- **Python**: 3.8+
- **Status**: Active development
- **Last Updated**: January 2026

---

**Made with ❤️ by [Ajay Jony](https://github.com/ajayjony)**
