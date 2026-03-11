import os
import yt_dlp as youtube_dl

def get_yt_dlp_opts(is_download=False, format_id=None, is_audio=False, tmp_dir=None):
    """
    Centralized configuration for yt-dlp to bypass YouTube's 2026 blocks.
    Configured specifically for Render's read-only environment.
    """
    # 1. Fetch secrets from Environment Variables (set these in Render Dashboard)
    proxy_url = os.getenv("YT_PROXY_URL")
    po_token = os.getenv("YT_PO_TOKEN")
    
    # 2. Setup Cookie Path
    # Render's /etc/secrets/ is read-only. 
    # We use the copy created in /tmp/ by views.py.
    writable_cookies = "/tmp/cookies.txt"
    local_cookies = os.path.join(os.getcwd(), "cookies.txt")
    
    # Priority: 1. Writable Temp (Render) -> 2. Local File (Dev) -> 3. None
    if os.path.exists(writable_cookies):
        cookie_file = writable_cookies
    elif os.path.exists(local_cookies):
        cookie_file = local_cookies
    else:
        cookie_file = None

    # 3. Build Extractor Args
    # Using 'web.player' with the PO Token is the most stable method for 2026.
    extractor_args = {
        'youtube': {
            'player_client': ['android', 'web'],
            'po_token': f"web.player+{po_token}" if po_token else None
        }
    }

    # 4. Base Options
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        },
        'extractor_args': extractor_args,
        'proxy': proxy_url,
        'cookiefile': cookie_file,
    }

    # 5. Logic for Downloading vs. Fetching Metadata
    if is_download:
        # outtmpl handles the path and filename formatting
        opts['outtmpl'] = os.path.join(tmp_dir, '%(title)s.%(ext)s')
        
        if is_audio:
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            })
        else:
            # Merges the specific video stream with the best audio available
            opts.update({
                'format': f'{format_id}+bestaudio/best',
                'merge_output_format': 'mp4'
            })
    else:
        # Standard settings for initial link analysis
        opts.update({
            'noplaylist': True,
            'format': 'bestvideo+bestaudio/best',
        })

    return opts
