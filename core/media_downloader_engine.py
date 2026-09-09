"""
VASTUDA Media Downloader Engine (Ultra Edition) — Surpassing Snaptube & Y2Mate
Features:
- Multi-Platform Universal Support (YouTube, Shorts, Instagram Reels, TikTok No-Watermark, Twitter/X, Facebook)
- Zero Server Disk Fill (ephemeral temporary directories cleaned via stream generator finally block)
- True DASH 1080p, 2K & 4K Audio-Video Multiplexing via FFmpeg
- Smart Clip / Trim Engine (cut start_time to end_time via FFmpeg)
- Subtitles & Closed Captions Extractor (.SRT, .VTT, .TXT in any language)
- Ultra-HD 4K Thumbnail & Cover Art Downloader
- Audiophile & Lossless Audio Formats (MP3 320k/256k/192k/128k/64k, WAV, FLAC, M4A, OGG)
- In-browser Direct Video & Audio Stream Preview
- Playlist Interactive Selection & Batch .ZIP Bundling
"""

import os
import sys
import shutil
import tempfile
import zipfile
import re
import subprocess
import urllib.parse
from pathlib import Path
from flask import Blueprint, request, jsonify, Response, stream_with_context

import yt_dlp

# Detect FFmpeg executable
def get_ffmpeg_binary():
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

FFMPEG_PATH = get_ffmpeg_binary()
print(f"[MEDIA STUDIO ENGINE] Active FFmpeg Binary: {FFMPEG_PATH}")

media_bp = Blueprint("media_downloader", __name__)

def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    cleaned = cleaned.strip()
    return cleaned or "download"

def parse_time_to_seconds(t_str: str) -> float:
    """Parses mm:ss or hh:mm:ss or seconds to float."""
    if not t_str:
        return 0.0
    t_str = t_str.strip()
    parts = t_str.split(":")
    try:
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        else:
            return float(t_str)
    except Exception:
        return 0.0

def get_base_ydl_opts(quiet=True):
    opts = {
        'nocheckcertificate': True,
        'quiet': quiet,
        'no_warnings': True,
        'geo_bypass': True,
        'ignoreerrors': False,
        'source_address': '0.0.0.0',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }
    if FFMPEG_PATH:
        opts['ffmpeg_location'] = FFMPEG_PATH
    return opts


# ==============================================================================
# 1. ANALYZE MEDIA URL (MULTI-PLATFORM & SUBTITLES & THUMBNAILS)
# ==============================================================================
@media_bp.route("/api/analyze", methods=["POST"])
@media_bp.route("/api/media/analyze", methods=["POST"])
def analyze_url():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Please enter a valid video or playlist URL."}), 400

    opts = get_base_ydl_opts()
    opts['extract_flat'] = 'in_playlist'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        err_msg = str(e)
        if "Sign in to confirm you’re not a bot" in err_msg:
            return jsonify({"error": "Platform rate-limit or bot detection triggered. Please try again shortly."}), 429
        elif "Private video" in err_msg or "Video unavailable" in err_msg:
            return jsonify({"error": "The requested video or playlist is private, deleted, or unavailable."}), 404
        return jsonify({"error": f"Failed to analyze URL: {err_msg[:160]}"}), 400

    if not info:
        return jsonify({"error": "No media metadata found."}), 404

    is_playlist = info.get('_type') == 'playlist' or 'entries' in info

    if is_playlist:
        entries = info.get('entries', []) or []
        playlist_items = []
        for idx, entry in enumerate(entries[:100], start=1):
            if not entry:
                continue
            playlist_items.append({
                "index": idx,
                "id": entry.get("id"),
                "title": entry.get("title", f"Video {idx}"),
                "duration": entry.get("duration", 0),
                "duration_string": str(round(entry.get("duration", 0) / 60, 1)) + " min" if entry.get("duration") else "N/A",
                "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                "thumbnail": entry.get("thumbnails")[-1]["url"] if entry.get("thumbnails") else None
            })

        return jsonify({
            "type": "playlist",
            "id": info.get("id"),
            "title": info.get("title", "YouTube Playlist"),
            "uploader": info.get("uploader", "Various Artists / Creator"),
            "video_count": len(entries),
            "thumbnail": playlist_items[0]["thumbnail"] if playlist_items else None,
            "items": playlist_items,
            "batch_options": [5, 10, 20, 50]
        }), 200

    # Single Video Format Matrix Extraction
    raw_formats = info.get("formats", [])
    duration_sec = info.get("duration", 0)
    video_id = info.get("id")

    # High-Definition Video Resolutions
    desired_resolutions = [
        ("2160p (4K Ultra HD)", 2160),
        ("1440p (2K QHD)", 1440),
        ("1080p (Full HD 60fps)", 1080),
        ("720p (HD High Speed)", 720),
        ("480p (Standard)", 480),
        ("360p (Mobile Friendly)", 360),
        ("240p (Low Bandwidth)", 240),
        ("144p (Saver)", 144)
    ]

    video_formats = []
    for label, target_h in desired_resolutions:
        matching = [f for f in raw_formats if f.get('vcodec') != 'none' and f.get('height') == target_h]
        if matching:
            best_stream = max(matching, key=lambda x: x.get('tbr') or x.get('vbr') or 0)
            fmt_id = best_stream.get('format_id')
            needs_merge = best_stream.get('acodec') == 'none'
            fps = best_stream.get('fps')
            
            filesize = best_stream.get('filesize') or best_stream.get('filesize_approx')
            if not filesize and duration_sec and best_stream.get('tbr'):
                filesize = int((best_stream['tbr'] * 1024 * duration_sec) / 8)
            
            size_str = f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "Adaptive Size"

            video_formats.append({
                "resolution": label,
                "height": target_h,
                "fps": fps,
                "format_id": fmt_id,
                "ext": "mp4",
                "needs_merge": needs_merge,
                "filesize_approx": size_str
            })

    if not video_formats:
        video_formats.append({
            "resolution": "Best Available MP4",
            "height": 720,
            "format_id": "best",
            "ext": "mp4",
            "needs_merge": True,
            "filesize_approx": "Dynamic"
        })

    # Audiophile & Lossless Audio Formats
    audio_formats = [
        {"quality": "320 kbps (Studio MP3)", "ext": "mp3", "bitrate": "320k", "approx_size": f"{round(duration_sec * 320 / 8 / 1024, 1)} MB" if duration_sec else "Studio 320k"},
        {"quality": "256 kbps (HQ MP3)", "ext": "mp3", "bitrate": "256k", "approx_size": f"{round(duration_sec * 256 / 8 / 1024, 1)} MB" if duration_sec else "HQ 256k"},
        {"quality": "192 kbps (High MP3)", "ext": "mp3", "bitrate": "192k", "approx_size": f"{round(duration_sec * 192 / 8 / 1024, 1)} MB" if duration_sec else "High 192k"},
        {"quality": "128 kbps (Standard MP3)", "ext": "mp3", "bitrate": "128k", "approx_size": f"{round(duration_sec * 128 / 8 / 1024, 1)} MB" if duration_sec else "Standard 128k"},
        {"quality": "64 kbps (Speech / Audiobook)", "ext": "mp3", "bitrate": "64k", "approx_size": f"{round(duration_sec * 64 / 8 / 1024, 1)} MB" if duration_sec else "Compact 64k"},
        {"quality": "Lossless WAV (Uncompressed)", "ext": "wav", "bitrate": "wav", "approx_size": f"{round(duration_sec * 1411 / 8 / 1024, 1)} MB" if duration_sec else "Lossless PCM"},
        {"quality": "Lossless FLAC (Hi-Res Audio)", "ext": "flac", "bitrate": "flac", "approx_size": f"{round(duration_sec * 800 / 8 / 1024, 1)} MB" if duration_sec else "Hi-Res FLAC"},
        {"quality": "Original AAC / M4A", "ext": "m4a", "bitrate": "best", "approx_size": f"{round(duration_sec * 128 / 8 / 1024, 1)} MB" if duration_sec else "Original Stream"},
        {"quality": "OGG Vorbis", "ext": "ogg", "bitrate": "ogg", "approx_size": f"{round(duration_sec * 160 / 8 / 1024, 1)} MB" if duration_sec else "OGG Audio"}
    ]

    # Subtitles Metadata Extraction
    subtitles_raw = info.get("subtitles") or {}
    auto_subs_raw = info.get("automatic_captions") or {}
    subtitle_tracks = []

    for lang in subtitles_raw.keys():
        subtitle_tracks.append({"lang": lang, "type": "official", "label": lang.upper()})
    for lang in list(auto_subs_raw.keys())[:15]:  # Top 15 auto caption languages
        if not any(s['lang'] == lang for s in subtitle_tracks):
            subtitle_tracks.append({"lang": lang, "type": "auto", "label": f"{lang.upper()} (Auto)"})

    # High-Res Thumbnail Image Links
    thumbnails = []
    if video_id and ("youtube.com" in url or "youtu.be" in url):
        thumbnails = [
            {"label": "Ultra HD (4K / 1080p)", "resolution": "1920x1080", "url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"},
            {"label": "High Quality (HD)", "resolution": "640x480", "url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"},
            {"label": "Medium Quality", "resolution": "320x180", "url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"}
        ]
    elif info.get("thumbnail"):
        thumbnails = [{"label": "Original Cover", "resolution": "High Res", "url": info.get("thumbnail")}]

    # Direct In-Browser Progressive Preview Stream URL
    preview_url = None
    direct_progressive = [f for f in raw_formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4' and f.get('url')]
    if direct_progressive:
        preview_url = direct_progressive[0].get('url')

    return jsonify({
        "type": "video",
        "id": video_id,
        "title": info.get("title", "YouTube Video"),
        "uploader": info.get("uploader", "Creator"),
        "views": info.get("view_count", 0),
        "duration_seconds": duration_sec,
        "duration_string": f"{int(duration_sec // 60)}:{int(duration_sec % 60):02d}",
        "thumbnail": info.get("thumbnail"),
        "thumbnails_list": thumbnails,
        "subtitles_available": subtitle_tracks,
        "preview_url": preview_url,
        "video_formats": video_formats,
        "audio_formats": audio_formats,
        "ffmpeg_available": bool(FFMPEG_PATH)
    }), 200


# ==============================================================================
# 2. DIRECT STREAMING DOWNLOAD WITH CLIP/TRIM SUPPORT
# ==============================================================================
@media_bp.route("/api/download/video", methods=["GET"])
@media_bp.route("/api/media/download", methods=["GET"])
def download_video():
    url = (request.args.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    height_str = request.args.get("height")
    height = int(height_str) if height_str and height_str.isdigit() else None
    format_id = request.args.get("format_id")
    is_audio = request.args.get("is_audio", "").lower() in ("true", "1", "yes")
    audio_bitrate = request.args.get("audio_bitrate", "192k")
    audio_format = request.args.get("audio_format", "mp3")

    # Clip / Trim timestamps
    start_time = request.args.get("start_time", "").strip()
    end_time = request.args.get("end_time", "").strip()
    is_trim = bool(start_time and end_time)

    temp_dir = tempfile.mkdtemp(prefix="vastuda_dl_")
    output_template = os.path.join(temp_dir, "raw_media.%(ext)s")

    opts = get_base_ydl_opts(quiet=False)
    opts['outtmpl'] = output_template

    if is_audio:
        if audio_format in ("wav", "flac", "ogg", "m4a") and FFMPEG_PATH:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'vorbis' if audio_format == 'ogg' else audio_format,
            }]
        elif FFMPEG_PATH:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_bitrate.replace('k', '') if 'k' in audio_bitrate else '192',
            }]
        else:
            opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
    else:
        if height and FFMPEG_PATH:
            opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'
            opts['merge_output_format'] = 'mp4'
        elif format_id:
            opts['format'] = f'{format_id}+bestaudio/best'
            if FFMPEG_PATH:
                opts['merge_output_format'] = 'mp4'
        else:
            opts['format'] = 'best[ext=mp4]/best'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(url, download=True)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": f"Download processing failed: {str(e)[:180]}"}), 500

    downloaded_files = list(Path(temp_dir).glob("raw_media.*"))
    if not downloaded_files:
        downloaded_files = list(Path(temp_dir).glob("*"))
    if not downloaded_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": "Processed file could not be found."}), 500

    source_file = downloaded_files[0]
    final_file = source_file

    # Execute FFmpeg Trim / Clip if requested
    if is_trim and FFMPEG_PATH:
        trimmed_file = Path(temp_dir) / f"trimmed_{source_file.name}"
        s_sec = parse_time_to_seconds(start_time)
        e_sec = parse_time_to_seconds(end_time)
        duration = max(e_sec - s_sec, 1.0)

        cmd = [
            FFMPEG_PATH, "-y",
            "-ss", str(s_sec),
            "-t", str(duration),
            "-i", str(source_file),
            "-c", "copy",
            str(trimmed_file)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if trimmed_file.exists() and trimmed_file.stat().st_size > 1024:
                final_file = trimmed_file
        except Exception as trim_err:
            print(f"[TRIM NOTICE] Fast copy trim failed, trying transcode trim: {trim_err}")
            cmd_transcode = [
                FFMPEG_PATH, "-y",
                "-ss", str(s_sec),
                "-t", str(duration),
                "-i", str(source_file),
                str(trimmed_file)
            ]
            try:
                subprocess.run(cmd_transcode, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if trimmed_file.exists():
                    final_file = trimmed_file
            except Exception:
                pass

    raw_title = meta.get("title", "media")
    ext = final_file.suffix.lstrip(".")
    clip_suffix = f"_clip_{start_time.replace(':','-')}_to_{end_time.replace(':','-')}" if is_trim else ""
    final_filename = f"{sanitize_filename(raw_title)}{clip_suffix}.{ext}"
    encoded_filename = urllib.parse.quote(final_filename)

    file_size = final_file.stat().st_size
    media_type = "audio/mpeg" if ext == "mp3" else ("audio/wav" if ext == "wav" else ("audio/flac" if ext == "flac" else ("audio/mp4" if ext == "m4a" else "video/mp4")))

    def generate_and_clean():
        try:
            with open(final_file, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    response = Response(stream_with_context(generate_and_clean()), mimetype=media_type)
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
    response.headers["Content-Length"] = str(file_size)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ==============================================================================
# 3. SUBTITLES & CLOSED CAPTIONS EXTRACTION
# ==============================================================================
@media_bp.route("/api/download/subtitles", methods=["GET"])
@media_bp.route("/api/media/subtitles", methods=["GET"])
def download_subtitles():
    url = (request.args.get("url") or "").strip()
    lang = request.args.get("lang", "en").strip()
    sub_format = request.args.get("format", "srt").strip().lower()  # srt, vtt, txt

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    temp_dir = tempfile.mkdtemp(prefix="vastuda_sub_")
    opts = get_base_ydl_opts(quiet=True)
    opts['skip_download'] = True
    opts['writesubtitles'] = True
    opts['writeautomaticsub'] = True
    opts['subtitleslangs'] = [lang]
    opts['subtitlesformat'] = "srt" if sub_format == "txt" else sub_format
    opts['outtmpl'] = os.path.join(temp_dir, "caption.%(ext)s")

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(url, download=True)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": f"Subtitle extraction failed: {str(e)[:160]}"}), 500

    sub_files = list(Path(temp_dir).glob("*.srt")) + list(Path(temp_dir).glob("*.vtt"))
    if not sub_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": f"No subtitles available in language: {lang}"}), 404

    target_sub = sub_files[0]
    content = target_sub.read_text(encoding="utf-8", errors="ignore")

    # If TXT requested, strip timestamps and counters
    if sub_format == "txt":
        cleaned_lines = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.isdigit() or "-->" in line:
                continue
            cleaned_lines.append(line)
        content = "\n".join(cleaned_lines)
        ext = "txt"
        mime = "text/plain"
    else:
        ext = sub_format
        mime = "text/vtt" if ext == "vtt" else "application/x-subrip"

    shutil.rmtree(temp_dir, ignore_errors=True)

    title = sanitize_filename(meta.get("title", "transcript"))
    sub_filename = f"{title}_{lang}.{ext}"
    encoded_name = urllib.parse.quote(sub_filename)

    response = Response(content, mimetype=f"{mime}; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_name}"
    return response


# ==============================================================================
# 4. PLAYLIST BATCH ZIP DOWNLOAD (WITH CUSTOM ITEMS SELECTION)
# ==============================================================================
@media_bp.route("/api/download/playlist-zip", methods=["POST"])
@media_bp.route("/api/media/playlist-zip", methods=["POST"])
def download_playlist_zip():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing playlist url"}), 400

    limit = min(max(int(payload.get("limit") or 10), 1), 50)
    format_type = payload.get("format_type", "video")
    custom_items = payload.get("items") or []  # List of URLs or indices

    temp_dir = tempfile.mkdtemp(prefix="vastuda_playlist_")
    opts = get_base_ydl_opts(quiet=True)
    opts['outtmpl'] = os.path.join(temp_dir, "%(playlist_index)s - %(title).120s.%(ext)s")

    if custom_items and isinstance(custom_items, list):
        opts['playlist_items'] = ",".join(str(i) for i in custom_items[:50])
    else:
        opts['playlistend'] = limit

    if format_type == "audio":
        opts['format'] = 'bestaudio/best'
        if FFMPEG_PATH:
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
    else:
        opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        if FFMPEG_PATH:
            opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(url, download=True)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": f"Playlist batch download failed: {str(e)[:180]}"}), 500

    zip_path = os.path.join(temp_dir, "playlist_bundle.zip")
    downloaded_files = [f for f in Path(temp_dir).glob("*") if f.name != "playlist_bundle.zip"]

    if not downloaded_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": "No playlist items were downloaded."}), 500

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_item in downloaded_files:
            zipf.write(file_item, arcname=file_item.name)

    playlist_title = sanitize_filename(meta.get("title", "YouTube_Playlist"))
    zip_filename = f"{playlist_title}_batch_{len(downloaded_files)}_tracks.zip"
    encoded_zip_name = urllib.parse.quote(zip_filename)
    zip_size = os.path.getsize(zip_path)

    def generate_zip_and_clean():
        try:
            with open(zip_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    response = Response(stream_with_context(generate_zip_and_clean()), mimetype="application/zip")
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_zip_name}"
    response.headers["Content-Length"] = str(zip_size)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ==============================================================================
# 5. HEALTH CHECK
# ==============================================================================
@media_bp.route("/api/media/health", methods=["GET"])
def media_health():
    return jsonify({
        "status": "online",
        "service": "VASTUDA Media Downloader Engine (Ultra)",
        "features": ["4K DASH", "Clip/Trim", "Subtitles", "Audiophile MP3/WAV/FLAC", "Playlists"],
        "ffmpeg_detected": bool(FFMPEG_PATH),
        "ffmpeg_binary": FFMPEG_PATH,
        "yt_dlp_version": yt_dlp.version.__version__
    }), 200
