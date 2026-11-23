import yt_dlp
import os
from engine.database import add_download, update_download

DOWNLOAD_DIR = os.path.expanduser("~/Downloads/PixelDownloader")

class VideoExtractor:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.download_id = None
        self._resolved_filename = None

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            progress = (downloaded / total * 100) if total else 0

            # Grab real filename as soon as yt-dlp starts writing
            if d.get("filename") and not self._resolved_filename:
                raw = d["filename"]
                clean = raw.replace(".part", "").replace(".ytdl", "")
                basename = os.path.basename(clean)
                # Strip yt-dlp format suffixes like .f616.mp4 → .mp4
                import re
                basename = re.sub(r'\.f\d{3,4}(\.\w+)$', r'\1', basename)
                self._resolved_filename = basename
                if self.download_id:
                    update_download(
                        self.download_id,
                        filename=self._resolved_filename,
                        save_path=clean
                    )

            if self.download_id and self.progress_callback:
                self.progress_callback(self.download_id, downloaded, total, progress)

        elif d["status"] == "finished":
            if self.download_id:
                update_download(self.download_id, status="completed")
                if self.progress_callback:
                    self.progress_callback(self.download_id, 0, 0, 100)
                import subprocess
                fname = self._resolved_filename or "Video"
                subprocess.Popen([
                    "notify-send",
                    "Pixel Downloader",
                    f"Download complete: {fname}",
                    "--icon=folder-download",
                    "--urgency=normal"
                ])

        elif d["status"] == "error":
            if self.download_id:
                update_download(self.download_id, status="failed")
                if self.progress_callback:
                    self.progress_callback(self.download_id, 0, 0, 0)

    def get_info(self, url):
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": 15,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail", ""),
                "uploader": info.get("uploader", "Unknown"),
                "formats": self._parse_formats(info.get("formats", [])),
                "url": url,
            }

    def _parse_formats(self, formats):
        seen = set()
        result = []
        for f in formats:
            ext = f.get("ext", "")
            height = f.get("height")
            label = f"{height}p" if height else f.get("format_note", "unknown")
            key = (label, ext)
            if key not in seen and ext in ("mp4", "webm", "mkv", "mp3", "m4a"):
                seen.add(key)
                result.append({
                    "format_id": f.get("format_id"),
                    "label": label,
                    "ext": ext,
                    "filesize": f.get("filesize") or f.get("filesize_approx", 0),
                    "vcodec": f.get("vcodec", "none"),
                    "acodec": f.get("acodec", "none"),
                })
        return sorted(result, key=lambda x: x["label"], reverse=True)

    def download(self, url, format_id=None, save_path=None, audio_only=False):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        out_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

        if audio_only:
            ydl_format = "bestaudio/best"
            postprocessors = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        elif format_id:
            ydl_format = f"{format_id}+bestaudio/best"
            postprocessors = []
        else:
            ydl_format = "bestvideo+bestaudio/best"
            postprocessors = []

        ydl_opts = {
            "format": ydl_format,
            "outtmpl": {
                "default": out_template,
                "chapter": out_template,
            },
            "progress_hooks": [self._progress_hook],
            "postprocessors": postprocessors,
            "merge_output_format": "mp4",
            "quiet": False,
            "no_warnings": False,
            "socket_timeout": 30,
            "retries": 5,
            "fragment_retries": 5,
            # Prevent format ID from appearing in filename
            "restrictfilenames": False,
            "trim_filenames": 200,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        }

        # Get info first to set a real filename immediately
        try:
            info = self.get_info(url)
            title = info.get("title", "video")
            ext = "mp3" if audio_only else "mp4"
            safe_title = "".join(
                c for c in title if c not in r'\/:*?"<>|'
            ).strip() or "video"
            filename = f"{safe_title}.{ext}"
            final_path = os.path.join(DOWNLOAD_DIR, filename)
            print(f"[Extractor] Resolved title: {filename}")
        except Exception as e:
            print(f"[Extractor] Could not fetch info: {e}")
            # Try to get title from URL as fallback
            try:
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(url)
                qs = parse_qs(parsed.query)
                # YouTube video id as last resort
                vid = qs.get("v", ["video"])[0]
                filename = f"{vid}.mp4"
            except:
                filename = "video.mp4"
            final_path = os.path.join(DOWNLOAD_DIR, filename)

        # Update DB with real filename right away
        if not self.download_id:
            self.download_id = add_download(
                url=url,
                filename=filename,
                save_path=final_path,
                total_size=0,
                segments=1
            )
        else:
            update_download(
                self.download_id,
                filename=filename,
                save_path=final_path
            )

        update_download(self.download_id, status="downloading")

        # Push filename to GUI immediately via progress callback
        if self.progress_callback:
            self.progress_callback(self.download_id, 0, 0, 0)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"[Extractor] Download error: {e}")
            update_download(self.download_id, status="failed",
                          filename=f"Failed: {filename}")
            if self.progress_callback:
                self.progress_callback(self.download_id, 0, 0, 0)
            raise

        return final_path

    def is_supported(self, url):
        extractors = yt_dlp.extractor.gen_extractors()
        for e in extractors:
            if e.suitable(url) and e.IE_NAME != "generic":
                return True
        return False
