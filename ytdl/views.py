from django.shortcuts import render
from django.http import HttpResponse, FileResponse
import yt_dlp as youtube_dl
import tempfile
import os
import re
from .forms import DownloadForm
from .utils import get_yt_dlp_opts  # Import the new logic

def download_video(request):
    form = DownloadForm(request.POST or None)
    context = {'form': form}

    if form.is_valid():
        video_url = form.cleaned_data.get("url")
        if not re.match(r'^(http(s)?:\/\/)?((w){3}\.)?youtu(be|\.be)?(\.com)?\/.+', video_url):
            return HttpResponse('Enter correct URL.')

        # Call the utility for metadata
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
                            'resolution': f"{f.get('height')}p" if f.get('height') else 'Audio',
                            'extension': f.get('ext', 'N/A'),
                            'file_size': f'{round(int(file_size)/1_000_000,2)} MB' if file_size else 'Unknown'
                        })

                context.update({
                    'title': meta.get('title', 'N/A'),
                    'streams': streams[::-1],
                    'thumb': meta.get('thumbnails', [{}])[-1].get('url', ''),
                    'video_url': video_url,
                })

        except Exception as e:
            context['error'] = f"YouTube blocked the request. Verify Proxy/Cookies: {str(e)}"
            
    return render(request, 'index.html', context)

def start_download(request):
    video_url = request.GET.get('url')
    format_id = request.GET.get('format_id')
    is_audio = request.GET.get('audio') == 'true'
    
    tmp_dir = tempfile.mkdtemp()
    # Call utility for actual download
    ydl_opts = get_yt_dlp_opts(is_download=True, format_id=format_id, is_audio=is_audio, tmp_dir=tmp_dir)

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            if is_audio: filename = os.path.splitext(filename)[0] + '.mp3'
            
            return FileResponse(open(filename, 'rb'), as_attachment=True)
    except Exception as e:
        return HttpResponse(f"Download Error: {str(e)}", status=500)
