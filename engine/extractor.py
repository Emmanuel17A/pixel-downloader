import yt_dlp
import os
from engine.database import add_download, update_download

DOWNLOAD_DIR = os.path.expanduser("~/Downloads/PixelDownloader")

class VideoExtractor:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.download_id = None

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            progress = (downloaded / total * 100) if total else 0
            if self.download_id and self.progress_callback:
                self.progress_callback(self.download_id, downloaded, total, progress)

        elif d["status"] == "finished":
            if self.download_id:
                update_download(self.download_id, status="completed")

        elif d["status"] == "error":
            if self.download_id:
                update_download(self.download_id, status="failed")

    def get_info(self, url):
        """Extract video info without downloading"""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
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
        """Return clean list of available quality options"""
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
        """Download video or audio using yt-dlp"""
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        out_path = save_path or os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

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
            "outtmpl": out_path,
            "progress_hooks": [self._progress_hook],
            "postprocessors": postprocessors,
            "merge_output_format": "mp4",
            "quiet": False,
            "no_warnings": False,
        }

        # Register in DB before download starts
        info = self.get_info(url)
        filename = f"{info['title']}.mp4" if not audio_only else f"{info['title']}.mp3"
        final_path = os.path.join(DOWNLOAD_DIR, filename)
        self.download_id = add_download(
            url=url,
            filename=filename,
            save_path=final_path,
            total_size=0,
            segments=1
        )
        update_download(self.download_id, status="downloading")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return final_path

    def is_supported(self, url):
        """Check if URL is supported by yt-dlp"""
        extractors = yt_dlp.extractor.gen_extractors()
        for e in extractors:
            if e.suitable(url) and e.IE_NAME != "generic":
                return True
        return False
