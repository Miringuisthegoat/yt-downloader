from django.shortcuts import render
from django.http import HttpResponse, FileResponse
import yt_dlp as youtube_dl
import tempfile
import os
import re
import shutil
from .forms import DownloadForm
from .utils import get_yt_dlp_opts  # Ensure utils.py is in the same folder

# ==========================================================
# FIX: Handle Read-Only File System for Render
# ==========================================================
SECRET_COOKIE_PATH = '/etc/secrets/cookies.txt'
WRITABLE_COOKIE_PATH = '/tmp/cookies.txt'

# Copy the cookies to /tmp/ where the app has write permissions.
# This prevents the [Errno 30] Read-only file system error.
if os.path.exists(SECRET_COOKIE_PATH):
    try:
        shutil.copy2(SECRET_COOKIE_PATH, WRITABLE_COOKIE_PATH)
    except Exception as e:
        print(f"Warning: Could not copy cookies to writable path: {e}")
# ==========================================================

def download_video(request):
    form = DownloadForm(request.POST or None)
    context = {'form': form}

    if request.method == 'POST' and form.is_valid():
        video_url = form.cleaned_data.get("url")
        
        # 1. Validation
        if not re.match(r'^(http(s)?:\/\/)?((w){3}\.)?youtu(be|\.be)?(\.com)?\/.+', video_url):
            context['error'] = 'Please enter a valid YouTube URL.'
            return render(request, 'index.html', context)

        # 2. Fetch Metadata using our centralized utility
        ydl_opts = get_yt_dlp_opts(is_download=False)

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(video_url, download=False)
                
                # Filter and sort streams (Highest resolution first)
                streams = []
                for f in meta.get('formats', []):
                    # Only show formats with video+audio or distinct resolutions
                    if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                        file_size = f.get('filesize') or f.get('filesize_approx') or 0
                        streams.append({
                            'format_id': f['format_id'],
                            'resolution': f"{f.get('height')}p" if f.get('height') else 'Audio Only',
                            'extension': f.get('ext', 'mp4'),
                            'file_size': f'{round(int(file_size)/1_000_000, 2)} MB' if file_size else 'Unknown'
                        })

                # Prepare context for the template
                context.update({
                    'title': meta.get('title', 'Video Download'),
                    'streams': streams[::-1],  # Reverse to show highest quality first
                    'thumb': meta.get('thumbnails', [{}])[-1].get('url', ''),
                    'video_url': video_url,
                    'duration': round(meta.get('duration', 0) / 60, 2),
                    'views': f"{meta.get('view_count', 0):,}",
                })

        except Exception as e:
            error_str = str(e)
            if "Sign in to confirm" in error_str:
                context['error'] = "YouTube is blocking this request. Please update your cookies."
            elif "Read-only file system" in error_str:
                context['error'] = "File system error. Please check the /tmp/ cookie configuration."
            else:
                context['error'] = f"Could not fetch video info: {error_str[:100]}"
            
    return render(request, 'index.html', context)

def start_download(request):
    """
    Handles the actual file generation and streaming to the user.
    """
    video_url = request.GET.get('url')
    format_id = request.GET.get('format_id')
    is_audio = request.GET.get('audio') == 'true'

    if not video_url or not format_id:
        return HttpResponse("Invalid download request.", status=400)
    
    # Create a unique temporary directory for this specific download
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
            
            # Adjust filename if post-processor changed extension (e.g., to .mp3)
            if is_audio:
                filename = os.path.splitext(filename)[0] + '.mp3'

            # Stream the file back to the user
            response = FileResponse(
                open(filename, 'rb'), 
                as_attachment=True, 
                filename=os.path.basename(filename)
            )
            
            return response

    except Exception as e:
        # Cleanup on failure
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return HttpResponse(f"Download error: {str(e)}", status=500)
