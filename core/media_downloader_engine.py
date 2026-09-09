"""
VASTUDA Media Downloader Engine — Production-grade YouTube Video, Audio & Playlist Extractor
Features:
- Zero Server Disk Fill (ephemeral temporary directories cleaned via stream generator finally block)
- True DASH 1080p, 2K & 4K Audio-Video Multiplexing via FFmpeg
- Studio-grade Audio Extraction (320kbps, 192kbps, 128kbps MP3)
- Batch Playlist .ZIP Bundling with resource ceilings
"""

import os
import sys
import shutil
import tempfile
import zipfile
import re
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
# 1. ANALYZE MEDIA URL (VIDEO / PLAYLIST)
# ==============================================================================
@media_bp.route("/api/analyze", methods=["POST"])
@media_bp.route("/api/media/analyze", methods=["POST"])
def analyze_url():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Please enter a valid YouTube URL."}), 400

    opts = get_base_ydl_opts()
    opts['extract_flat'] = 'in_playlist'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        err_msg = str(e)
        if "Sign in to confirm you’re not a bot" in err_msg:
            return jsonify({"error": "YouTube rate-limit or bot detection triggered. Please try again shortly."}), 429
        elif "Private video" in err_msg or "Video unavailable" in err_msg:
            return jsonify({"error": "The requested video or playlist is private, deleted, or unavailable."}), 404
        return jsonify({"error": f"Failed to analyze URL: {err_msg[:160]}"}), 400

    if not info:
        return jsonify({"error": "No media metadata found."}), 404

    is_playlist = info.get('_type') == 'playlist' or 'entries' in info

    if is_playlist:
        entries = info.get('entries', []) or []
        playlist_items = []
        for idx, entry in enumerate(entries[:50], start=1):
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
            "batch_options": [5, 10, 20]
        }), 200

    # Single Video Format Matrix Extraction
    raw_formats = info.get("formats", [])
    duration_sec = info.get("duration", 0)

    desired_resolutions = [
        ("2160p (4K)", 2160),
        ("1440p (2K QHD)", 1440),
        ("1080p (Full HD)", 1080),
        ("720p (HD)", 720),
        ("480p (SD)", 480),
        ("360p", 360)
    ]

    video_formats = []
    for label, target_h in desired_resolutions:
        matching = [f for f in raw_formats if f.get('vcodec') != 'none' and f.get('height') == target_h]
        if matching:
            best_stream = max(matching, key=lambda x: x.get('tbr') or x.get('vbr') or 0)
            fmt_id = best_stream.get('format_id')
            needs_merge = best_stream.get('acodec') == 'none'
            
            filesize = best_stream.get('filesize') or best_stream.get('filesize_approx')
            if not filesize and duration_sec and best_stream.get('tbr'):
                filesize = int((best_stream['tbr'] * 1024 * duration_sec) / 8)
            
            size_str = f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "Adaptive Size"

            video_formats.append({
                "resolution": label,
                "height": target_h,
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

    audio_formats = [
        {"quality": "320 kbps (Studio MP3)", "ext": "mp3", "bitrate": "320k", "approx_size": f"{round(duration_sec * 320 / 8 / 1024, 1)} MB" if duration_sec else "High Quality"},
        {"quality": "192 kbps (High MP3)", "ext": "mp3", "bitrate": "192k", "approx_size": f"{round(duration_sec * 192 / 8 / 1024, 1)} MB" if duration_sec else "Standard Quality"},
        {"quality": "128 kbps (Standard MP3)", "ext": "mp3", "bitrate": "128k", "approx_size": f"{round(duration_sec * 128 / 8 / 1024, 1)} MB" if duration_sec else "Standard Quality"},
        {"quality": "Original Audio (M4A/AAC)", "ext": "m4a", "bitrate": "best", "approx_size": f"{round(duration_sec * 128 / 8 / 1024, 1)} MB" if duration_sec else "Original Track"}
    ]

    return jsonify({
        "type": "video",
        "id": info.get("id"),
        "title": info.get("title", "YouTube Video"),
        "uploader": info.get("uploader", "YouTube Creator"),
        "views": info.get("view_count", 0),
        "duration_seconds": duration_sec,
        "duration_string": f"{int(duration_sec // 60)}:{int(duration_sec % 60):02d}",
        "thumbnail": info.get("thumbnail"),
        "video_formats": video_formats,
        "audio_formats": audio_formats,
        "ffmpeg_available": bool(FFMPEG_PATH)
    }), 200


# ==============================================================================
# 2. DIRECT STREAMING DOWNLOAD (ZERO SERVER DISK RETENTION)
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

    temp_dir = tempfile.mkdtemp(prefix="vastuda_dl_")
    output_template = os.path.join(temp_dir, "%(title).200s.%(ext)s")

    opts = get_base_ydl_opts(quiet=False)
    opts['outtmpl'] = output_template

    if is_audio:
        target_ext = "mp3" if audio_bitrate != "best" else "m4a"
        if target_ext == "mp3" and FFMPEG_PATH:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_bitrate.replace('k', '') if audio_bitrate else '192',
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

    downloaded_files = list(Path(temp_dir).glob("*"))
    if not downloaded_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": "Processed file could not be found."}), 500

    file_path = downloaded_files[0]
    raw_title = meta.get("title", "media")
    ext = file_path.suffix.lstrip(".")
    final_filename = f"{sanitize_filename(raw_title)}.{ext}"
    encoded_filename = urllib.parse.quote(final_filename)

    file_size = file_path.stat().st_size
    media_type = "audio/mpeg" if ext == "mp3" else ("audio/mp4" if ext == "m4a" else "video/mp4")

    # Streaming generator with automated temp dir cleanup on stream finish/break
    def generate_and_clean():
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    yield chunk
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"[CLEANUP] Deleted temp folder: {temp_dir}")
            except Exception as ce:
                print(f"[CLEANUP ERROR] {ce}")

    response = Response(stream_with_context(generate_and_clean()), mimetype=media_type)
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
    response.headers["Content-Length"] = str(file_size)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ==============================================================================
# 3. PLAYLIST BATCH ZIP DOWNLOAD
# ==============================================================================
@media_bp.route("/api/download/playlist-zip", methods=["POST"])
@media_bp.route("/api/media/playlist-zip", methods=["POST"])
def download_playlist_zip():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing playlist url"}), 400

    limit = min(max(int(payload.get("limit") or 10), 1), 25)
    format_type = payload.get("format_type", "video")

    temp_dir = tempfile.mkdtemp(prefix="vastuda_playlist_")
    opts = get_base_ydl_opts(quiet=True)
    opts['playlistend'] = limit
    opts['outtmpl'] = os.path.join(temp_dir, "%(playlist_index)s - %(title).120s.%(ext)s")

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
    zip_filename = f"{playlist_title}_batch_{len(downloaded_files)}_videos.zip"
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
                print(f"[CLEANUP] Deleted playlist temp folder: {temp_dir}")
            except Exception as ce:
                print(f"[CLEANUP ERROR] {ce}")

    response = Response(stream_with_context(generate_zip_and_clean()), mimetype="application/zip")
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_zip_name}"
    response.headers["Content-Length"] = str(zip_size)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ==============================================================================
# 4. HEALTH CHECK
# ==============================================================================
@media_bp.route("/api/media/health", methods=["GET"])
def media_health():
    return jsonify({
        "status": "online",
        "service": "VASTUDA Media Downloader Engine",
        "ffmpeg_detected": bool(FFMPEG_PATH),
        "ffmpeg_binary": FFMPEG_PATH,
        "yt_dlp_version": yt_dlp.version.__version__
    }), 200
