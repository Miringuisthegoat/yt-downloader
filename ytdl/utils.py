import os
import yt_dlp

def get_yt_dlp_opts(is_download=False, format_id=None, is_audio=False, tmp_dir=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_vr'],
            }
        },
    }
    if is_download:
        opts['outtmpl'] = os.path.join(tmp_dir, '%(title)s.%(ext)s')
        if is_audio:
            opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
        else:
            opts.update({'format': f'{format_id}+bestaudio/best', 'merge_output_format': 'mp4'})
    else:
        opts.update({'noplaylist': True, 'format': 'bestvideo+bestaudio/best'})
    return opts
