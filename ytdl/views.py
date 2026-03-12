from django.shortcuts import render
from django.http import HttpResponse, FileResponse
import yt_dlp as youtube_dl
import tempfile
import os
import re
import shutil
from .forms import DownloadForm
from .utils import get_yt_dlp_opts

# ==========================================================
# Handle Read-Only File System for Render
# ==========================================================
SECRET_COOKIE_PATH = '/etc/secrets/cookies.txt'
WRITABLE_COOKIE_PATH = '/tmp/cookies.txt'


def sync_cookies():
    """Ensures a writable copy of cookies exists in /tmp/."""
    if os.path.exists(SECRET_COOKIE_PATH):
        try:
            shutil.copy2(SECRET_COOKIE_PATH, WRITABLE_COOKIE_PATH)
            return True
        except Exception as e:
            print(f"Warning: Could not copy cookies to writable path: {e}")
    return False


# Initial sync on app startup
sync_cookies()


def download_video(request):
    form = DownloadForm(request.POST or None)
    context = {'form': form}

    if request.method == 'POST' and form.is_valid():
        video_url = form.cleaned_data.get("url")

        # Validation
        if not re.match(r'^(http(s)?:\/\/)?((w){3}\.)?youtu(be|\.be)?(\.com)?\/.+', video_url):
            context['error'] = 'Please enter a valid YouTube URL.'
            return render(request, 'index.html', context)

        # Refresh cookies and get options
        sync_cookies()
        ydl_opts = get_yt_dlp_opts(is_download=False)

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(video_url, download=False)

                streams = []
                for f in meta.get('formats', []):
                    if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                        file_size = f.get('filesize') or f.get('filesize_approx') or 0
                        streams.append({
                            'format_id': f['format_id'],
                            'resolution': f"{f.get('height')}p" if f.get('height') else 'Audio Only',
                            'extension': f.get('ext', 'mp4'),
                            'file_size': f'{round(int(file_size)/1_000_000, 2)} MB' if file_size else 'Unknown',
                        })

                thumbnails = meta.get('thumbnails', [{}])
                thumb_url = thumbnails[-1].get('url', '') if thumbnails else ''

                likes = meta.get('like_count', 'N/A')
                dislikes = meta.get('dislike_count', 'N/A')

                context.update({
                    'title': meta.get('title', 'Video Download'),
                    'streams': streams[::-1],
                    'thumb': thumb_url,
                    'video_url': video_url,
                    'duration': round(meta.get('duration', 0) / 60, 2),
                    'views': f"{meta.get('view_count', 0):,}",
                    'likes': likes,
                    'dislikes': dislikes,
                    'description': meta.get('description', ''),
                })

        except Exception as e:
            error_str = str(e)
            if "Sign in to confirm" in error_str:
                context['error'] = "YouTube blocked the request. Please update your cookies."
            elif "Read-only file system" in error_str:
                context['error'] = "Critical: System tried writing to a read-only path. Check /tmp/ config."
            else:
                context['error'] = f"Could not fetch video: {error_str[:200]}"

    return render(request, 'index.html', context)


def start_download(request):
    """Handles file generation and streaming."""
    video_url = request.GET.get('url')
    format_id = request.GET.get('format_id')
    is_audio = request.GET.get('audio') == 'true'

    if not video_url or not format_id:
        return HttpResponse("Invalid download request.", status=400)

    # Ensure fresh cookies are available in /tmp/
    sync_cookies()

    tmp_dir = tempfile.mkdtemp()
    ydl_opts = get_yt_dlp_opts(
        is_download=True,
        format_id=format_id,
        is_audio=is_audio,
        tmp_dir=tmp_dir
    )

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)

            if is_audio:
                filename = os.path.splitext(filename)[0] + '.mp3'

            if not os.path.exists(filename):
                files = os.listdir(tmp_dir)
                if not files:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    return HttpResponse('Download failed — file not found.', status=500)
                filename = os.path.join(tmp_dir, files[0])

            return FileResponse(
                open(filename, 'rb'),
                as_attachment=True,
                filename=os.path.basename(filename)
            )

    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return HttpResponse(f"Download error: {str(e)}", status=500)