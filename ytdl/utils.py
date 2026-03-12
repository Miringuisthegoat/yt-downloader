import os
import yt_dlp


def get_yt_dlp_opts(is_download=False, format_id=None, is_audio=False, tmp_dir=None):
    """
    Updated for 2026: Automatic PO Token generation via bgutil-ytdlp-pot-provider.
    """
    proxy_url = os.getenv("YT_PROXY_URL")

    # Setup Cookie Path
    writable_cookies = "/tmp/cookies.txt"
    local_cookies = os.path.join(os.getcwd(), "cookies.txt")
    cookie_file = writable_cookies if os.path.exists(writable_cookies) else (
        local_cookies if os.path.exists(local_cookies) else None
    )

    extractor_args = {
        'youtube': {
            'player_client': ['android', 'web'],
        }
    }

    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        },
        'extractor_args': extractor_args,
        'cookiefile': cookie_file,
    }

    if proxy_url:
        opts['proxy'] = proxy_url

    if is_download:
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
            opts.update({
                'format': f'{format_id}+bestaudio/best',
                'merge_output_format': 'mp4',
            })
    else:
        opts.update({
            'noplaylist': True,
            'format': 'bestvideo+bestaudio/best',
        })

    return opts