import os
import yt_dlp as youtube_dl

def get_yt_dlp_opts(is_download=False, format_id=None, is_audio=False, tmp_dir=None):
    """
    Centralized configuration for yt-dlp to bypass YouTube's 2026 blocks.
    """
    # Get secrets from Render/Environment Variables
    proxy_url = os.getenv("YT_PROXY_URL")
    po_token = os.getenv("YT_PO_TOKEN")
    
    # Cookie Path Logic
    render_cookies = "/etc/secrets/cookies.txt"
    local_cookies = os.path.join(os.getcwd(), "cookies.txt")
    cookie_file = render_cookies if os.path.exists(render_cookies) else local_cookies if os.path.exists(local_cookies) else None

    # Build Extractor Args (Crucial for PO Token)
    extractor_args = {'youtube': {'player_client': ['android', 'web']}}
    if po_token:
        # Note: In 2026, some clients need the 'web+' prefix
        extractor_args['youtube']['po_token'] = po_token

    opts = {
        'quiet': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        },
        'extractor_args': extractor_args,
        'proxy': proxy_url,
        'cookiefile': cookie_file,
    }

    if is_download:
        opts['outtmpl'] = os.path.join(tmp_dir, '%(title)s.%(ext)s')
        if is_audio:
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
            })
        else:
            opts.update({
                'format': f'{format_id}+bestaudio/best',
                'merge_output_format': 'mp4'
            })
    else:
        opts.update({
            'noplaylist': True,
            'format': 'bestvideo+bestaudio/best',
        })

    return opts
