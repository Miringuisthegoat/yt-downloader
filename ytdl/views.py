from django.shortcuts import render
from django.http import HttpResponse, FileResponse
import yt_dlp as youtube_dl
from .forms import DownloadForm
import re
import os
import tempfile

# Headers to bypass YouTube bot detection
YDL_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# ---------------------------
# UPDATED COOKIE SUPPORT
# ---------------------------
# 1. Check Render's Secret File location first
# 2. Check local path for development
RENDER_SECRETS_PATH = "/etc/secrets/cookies.txt"
LOCAL_COOKIES_PATH = os.path.join(os.getcwd(), "cookies.txt")

if os.path.exists(RENDER_SECRETS_PATH):
    COOKIES_PATH = RENDER_SECRETS_PATH
elif os.path.exists(LOCAL_COOKIES_PATH):
    COOKIES_PATH = LOCAL_COOKIES_PATH
else:
    COOKIES_PATH = None

# ---------------------------
# PO TOKEN SUPPORT
# ---------------------------
PO_TOKEN = os.getenv("YT_PO_TOKEN")

def get_extractor_args():
    """Return extractor args with optional PO token."""
    args = {
        'player_client': ['android', 'web'],
        'player_skip': ['configs', 'webpage']
    }
    if PO_TOKEN:
        args['po_token'] = PO_TOKEN
    return {'youtube': args}

def download_video(request):
    form = DownloadForm(request.POST or None)
    context = {'form': form}

    if form.is_valid():
        video_url = form.cleaned_data.get("url")
        regex = r'^(http(s)?:\/\/)?((w){3}\.)?youtu(be|\.be)?(\.com)?\/.+'

        if not re.match(regex, video_url):
            return HttpResponse('Enter correct URL.')

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'http_headers': YDL_HEADERS,
            'extractor_args': get_extractor_args(),
            'nocheckcertificate': True,
            'noplaylist': True,
        }

        # Use the COOKIES_PATH we defined above
        if COOKIES_PATH:
            ydl_opts['cookiefile'] = COOKIES_PATH

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(video_url, download=False)
        except Exception as e:
            context['error'] = f'Could not fetch video: {str(e)}'
            return render(request, 'index.html', context)

        streams = []
        for f in meta['formats']:
            file_size = f.get('filesize') or f.get('filesize_approx') or 0
            if file_size:
                file_size = f'{round(int(file_size)/1_000_000,2)} MB'
            else:
                file_size = 'Unknown'

            resolution = f"{f['height']}p" if f.get('height') else 'Audio'
            streams.append({
                'format_id': f['format_id'],
                'resolution': resolution,
                'extension': f.get('ext', 'N/A'),
                'file_size': file_size
            })

        streams = streams[::-1]
        thumbnails = meta.get('thumbnails', [{}])
        thumb_url = thumbnails[-1]['url'] if thumbnails else ''

        context.update({
            'form': form,
            'title': meta.get('title', 'N/A'),
            'streams': streams,
            'description': meta.get('description', ''),
            'thumb': thumb_url,
            'video_url': video_url,
            'duration': round(int(meta.get('duration', 0))/60, 2),
            'views': f'{int(meta.get("view_count", 0)):,}'
        })

    return render(request, 'index.html', context)

def start_download(request):
    video_url = request.GET.get('url')
    format_id = request.GET.get('format_id')
    is_audio = request.GET.get('audio') == 'true'

    if not video_url or not format_id:
        return HttpResponse('Missing url or format.', status=400)

    tmp_dir = tempfile.mkdtemp()
    base_opts = {
        'quiet': True,
        'http_headers': YDL_HEADERS,
        'extractor_args': get_extractor_args(),
        'concurrent_fragment_downloads': 5,
        'noplaylist': True,
        'nocheckcertificate': True,
        'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s')
    }

    if COOKIES_PATH:
        base_opts['cookiefile'] = COOKIES_PATH

    if is_audio:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': f'{format_id}+bestaudio/best',
            'merge_output_format': 'mp4',
        }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)

        if is_audio:
            filename = os.path.splitext(filename)[0] + '.mp3'

        if not os.path.exists(filename):
            files = os.listdir(tmp_dir)
            if not files:
                return HttpResponse('Download failed.', status=500)
            filename = os.path.join(tmp_dir, files[0])

        return FileResponse(
            open(filename, 'rb'),
            as_attachment=True,
            filename=os.path.basename(filename)
        )
    except Exception as e:
        return HttpResponse(f'Download error: {str(e)}', status=500)