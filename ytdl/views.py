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


def download_video(request):
    form = DownloadForm(request.POST or None)
    context = {'form': form}

    if form.is_valid():
        video_url = form.cleaned_data.get("url")
        regex = r'^(http(s)?:\/\/)?((w){3}.)?youtu(be|.be)?(\.com)?\/.+'

        if not re.match(regex, video_url):
            return HttpResponse('Enter correct url.')

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'http_headers': YDL_HEADERS,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(video_url, download=False)
        except Exception as e:
            context['error'] = f'Could not fetch video: {str(e)}'
            return render(request, 'index.html', context)

        video_audio_streams = []
        for m in meta['formats']:
            file_size = m.get('filesize') or m.get('filesize_approx') or 0
            if file_size:
                file_size = f'{round(int(file_size) / 1000000, 2)} mb'
            else:
                file_size = 'Unknown'

            resolution = 'Audio'
            if m.get('height') is not None:
                resolution = f"{m['height']}x{m['width']}"

            video_audio_streams.append({
                'resolution': resolution,
                'extension': m.get('ext', 'N/A'),
                'file_size': file_size,
                'format_id': m.get('format_id', ''),
                'video_url': m.get('url', '')
            })

        video_audio_streams = video_audio_streams[::-1]

        thumbnails = meta.get('thumbnails', [{}])
        thumb_url = thumbnails[3]['url'] if len(thumbnails) > 3 else ''

        context = {
            'form': form,
            'title': meta.get('title', 'N/A'),
            'streams': video_audio_streams,
            'description': meta.get('description', ''),
            'likes': meta.get('like_count', 'N/A'),
            'dislikes': meta.get('dislike_count', 'N/A'),
            'thumb': thumb_url,
            'video_url': video_url,
            'duration': round(int(meta.get('duration', 0)) / 60, 2),
            'views': f'{int(meta.get("view_count", 0)):,}'
        }

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
    }

    if is_audio:
        ydl_opts = {
            **base_opts,
            'format': format_id,
            'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': format_id,
            'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
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

        response = FileResponse(
            open(filename, 'rb'),
            as_attachment=True,
            filename=os.path.basename(filename)
        )
        return response

    except Exception as e:
        return HttpResponse(f'Download error: {str(e)}', status=500)