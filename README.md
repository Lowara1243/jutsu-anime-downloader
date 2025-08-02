# Anime Downloader for Jut.su

This script allows you to download anime series and movies from `jut.su`. It supports selecting video quality, downloading specific seasons or episodes, and can be configured to bypass Cloudflare protection.

## Features

- Download anime by providing a URL or name.
- Choose from available video qualities (e.g., 1080p, 720p, 480p).
- Start downloading from a specific season and episode.
- Option to include or skip movies.
- Supports using proxies to route traffic.
- Bypasses Cloudflare protection by using browser cookies and a user-agent.

## Requirements

- Python 3.10 or newer
- The following Python libraries: `beautifulsoup4`, `requests`, `tqdm`, `loguru`

## Installation

1.  **Clone the repository or download the files:**
    ```bash
    git clone https://github.com/Lowara1243/jutsu-anime-downloader.git
    cd jutsu-anime-downloader
    ```
    Or simply download the `main.py` script.

2.  **Install the required libraries:**
    ```bash
    # Using pip
    pip install . # or `pip install bs4 loguru lxml requests tqdm`

    # Alternatively, using uv (faster)
    uv sync
    ```

## Configuration (Important for Cloudflare)

To ensure the script works correctly, you need to configure it to look like a real browser session. This involves setting your `User-Agent` and providing session cookies.

### 1. Set Your User-Agent

You must replace the default `User-Agent` in the script with the one from your browser.

1.  Open the `main.py` file.
2.  Find the `self.headers` dictionary (around line 15).
3.  To get your User-Agent:
    - Open your web browser (e.g., Firefox, Chrome).
    - Press `F12` to open Developer Tools.
    - Go to the **Network** tab.
    - Visit any website (like `jut.su`).
    - Click on any request in the list.
    - In the **Headers** tab, find the `User-Agent` request header and copy its value.
4.  Paste the copied value to replace the existing `User-Agent` in the script.

### 2. Provide Browser Cookies

The script needs your browser's cookies for `jut.su` to bypass Cloudflare checks.

1.  Install a browser extension that can export cookies in the **Netscape format (cookies.txt)**. A recommended extension is **cookies.txt**, which is available both on Chromium and FireFox.
2.  Navigate to the `jut.su` website.
3.  Click the extension's icon and export the cookies.
4.  Save the exported data into a file named `cookies.txt` in the same directory as the `main.py` script.

The script will automatically load and use these cookies for all requests.

## Usage

Run the script directly from your terminal:

```bash
python main.py
```

The script will prompt you to enter:
- The anime URL or name.
- The desired video quality.
- The starting season and episode number.
- Whether to download movies.

## Optional: Using Proxies

If you need to use a proxy, create a `proxies.txt` file and add your SOCKS5 proxy addresses, one per line. The script will automatically load and use them.

**Example `proxies.txt`:**
```
socks5://user:password@host:port
socks5://127.0.0.1:9050
```

---

***Disclaimer:** This script is intended for personal use only. Please respect the website's terms of service and avoid overwhelming their servers.*
