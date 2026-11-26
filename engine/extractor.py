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
                fname = self._resolved_filename or "Video"
                import sys
                if sys.platform == "win32":
                    try:
                        from plyer import notification
                        notification.notify(
                            title="Pixel Downloader",
                            message=f"Download complete: {fname}",
                            app_name="Pixel Downloader",
                            timeout=5
                        )
                    except:
                        pass
                else:
                    import subprocess
                    subprocess.Popen([
                        "notify-send", "Pixel Downloader",
                        f"Download complete: {fname}",
                        "--icon=folder-download", "--urgency=normal"
                    ])

        elif d["status"] == "error":
            if self.download_id:
                update_download(self.download_id, status="failed")
                if self.progress_callback:
                    self.progress_callback(self.download_id, 0, 0, 0)

    @staticmethod
    def _get_ytdlp_path():
        """Find yt-dlp executable — works both frozen and normal"""
        import sys, os, shutil
        if getattr(sys, "frozen", False):
            # Look next to the exe first
            base = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
            candidates = [
                os.path.join(os.path.dirname(sys.executable), "yt-dlp.exe"),
                os.path.join(base, "yt-dlp.exe"),
                os.path.join(os.path.dirname(sys.executable), "yt-dlp"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c
        # Fall back to system PATH
        found = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
        return found or "yt-dlp"

    def get_info(self, url):
        import sys, json, subprocess

        ytdlp = self._get_ytdlp_path()
        print(f"[Extractor] Using yt-dlp: {ytdlp}")

        try:
            result = subprocess.run(
                [ytdlp, "--dump-json", "--no-playlist",
                 "--no-warnings", url],
                capture_output=True, text=True, timeout=60,
                creationflags=0x08000000 if sys.platform == "win32" else 0
            )
            if result.returncode == 0 and result.stdout.strip():
                info = json.loads(result.stdout.strip().split("
")[0])
                return {
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "uploader": info.get("uploader", "Unknown"),
                    "formats": self._parse_formats(info.get("formats", [])),
                    "url": url,
                }
            else:
                print(f"[Extractor] yt-dlp stderr: {result.stderr}")
        except Exception as e:
            print(f"[Extractor] subprocess get_info failed: {e}")

        # Fallback — use yt_dlp library directly
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

        import sys
        try:
            # On Windows frozen exe — use yt-dlp subprocess
            if sys.platform == "win32":
                ytdlp = self._get_ytdlp_path()
                cmd = [
                    ytdlp,
                    "--format", ydl_format,
                    "--output", out_template,
                    "--merge-output-format", "mp4",
                    "--no-playlist",
                    "--newline",
                ]
                if audio_only:
                    cmd += ["--extract-audio", "--audio-format", "mp3",
                            "--audio-quality", "192K"]
                cmd.append(url)

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=0x08000000
                )

                import re
                for line in process.stdout:
                    line = line.strip()
                    print(f"[yt-dlp] {line}")

                    # Parse progress from yt-dlp output
                    # e.g. [download]  45.6% of 123.45MiB at 1.23MiB/s
                    match = re.search(
                        r"\[download\]\s+([\d.]+)%\s+of\s+([\d.]+)(\w+)",
                        line
                    )
                    if match and self.download_id and self.progress_callback:
                        percent = float(match.group(1))
                        size_val = float(match.group(2))
                        size_unit = match.group(3)
                        unit_map = {"B": 1, "KiB": 1024, "MiB": 1024**2,
                                    "GiB": 1024**3}
                        total = int(size_val * unit_map.get(size_unit, 1))
                        downloaded = int(total * percent / 100)
                        self.progress_callback(
                            self.download_id, downloaded, total, percent
                        )

                    # Grab filename
                    fname_match = re.search(
                        r"\[(?:download|Merger)\] Destination: (.+)", line
                    )
                    if fname_match and not self._resolved_filename:
                        raw = fname_match.group(1).strip()
                        self._resolved_filename = os.path.basename(raw)
                        if self.download_id:
                            update_download(
                                self.download_id,
                                filename=self._resolved_filename,
                                save_path=raw
                            )

                process.wait()
                if process.returncode != 0:
                    raise Exception(f"yt-dlp exited with code {process.returncode}")
            else:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

        except Exception as e:
            print(f"[Extractor] Download error: {e}")
            update_download(self.download_id, status="failed",
                          filename=f"Failed: {filename}")
            if self.progress_callback:
                self.progress_callback(self.download_id, 0, 0, 0)
            raise

        # Mark completed
        update_download(self.download_id, status="completed")
        if self.progress_callback:
            self.progress_callback(self.download_id, 0, 0, 100)

        return final_path

    def is_supported(self, url):
        extractors = yt_dlp.extractor.gen_extractors()
        for e in extractors:
            if e.suitable(url) and e.IE_NAME != "generic":
                return True
        return False
