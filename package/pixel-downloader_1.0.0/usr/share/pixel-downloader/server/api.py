from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

_queue_ref = None
_progress_callback = None
_new_download_callback = None

VIDEO_DOMAINS = [
    "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
    "tiktok.com", "instagram.com", "twitter.com", "x.com",
    "facebook.com", "twitch.tv", "bilibili.com"
]

def is_video_url(url):
    try:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        host = host.replace("www.", "")
        return any(d in host for d in VIDEO_DOMAINS)
    except:
        return False

def set_queue(queue, progress_callback=None, new_download_callback=None):
    global _queue_ref, _progress_callback, _new_download_callback
    _queue_ref = queue
    _progress_callback = progress_callback
    _new_download_callback = new_download_callback

@app.route("/ping", methods=["GET", "OPTIONS"])
def ping():
    return jsonify({"status": "ok", "app": "Pixel Downloader"})

@app.route("/add", methods=["POST", "OPTIONS"])
def add_download():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data.get("url")
    filename = data.get("filename")

    if _queue_ref is None:
        return jsonify({"error": "Download queue not ready"}), 503

    try:
        if is_video_url(url):
            def run():
                from engine.extractor import VideoExtractor
                from gi.repository import GLib
                ext = VideoExtractor(progress_callback=_progress_callback)
                try:
                    # Register in DB first so GUI row appears immediately
                    from engine.database import add_download as db_add, update_download
                    from engine.downloader import DOWNLOAD_DIR
                    import os
                    fname = "Fetching title..."
                    save_path = os.path.join(DOWNLOAD_DIR, fname)
                    dl_id = db_add(url, fname, save_path, 0, 1)
                    ext.download_id = dl_id
                    update_download(dl_id, status="downloading")
                    if _new_download_callback:
                        GLib.idle_add(_new_download_callback, dl_id)
                    ext.download(url)
                except Exception as e:
                    print(f"[API Extractor] Error: {e}")

            threading.Thread(target=run, daemon=True).start()
            return jsonify({"status": "queued", "type": "video", "url": url})

        else:
            # Regular file — add to queue then notify GUI
            downloader = _queue_ref.add(url=url, filename=filename)

            def notify():
                import time
                from gi.repository import GLib
                from engine.database import get_all_downloads
                # Wait briefly for DB row to be created
                time.sleep(0.5)
                downloads = get_all_downloads()
                if downloads and _new_download_callback:
                    GLib.idle_add(_new_download_callback, downloads[0]["id"])

            threading.Thread(target=notify, daemon=True).start()

            return jsonify({
                "status": "queued",
                "type": "file",
                "url": url,
                "filename": filename or url.split("/")[-1]
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/status", methods=["GET", "OPTIONS"])
def status():
    if _queue_ref is None:
        return jsonify({"error": "Queue not ready"}), 503
    return jsonify({
        "active": _queue_ref.get_active_ids(),
        "queued": _queue_ref.queue_size()
    })

@app.route("/pause/<int:download_id>", methods=["POST", "OPTIONS"])
def pause(download_id):
    if _queue_ref:
        _queue_ref.pause(download_id)
    return jsonify({"status": "paused", "id": download_id})

@app.route("/resume/<int:download_id>", methods=["POST", "OPTIONS"])
def resume(download_id):
    if _queue_ref:
        _queue_ref.resume(download_id)
    return jsonify({"status": "resumed", "id": download_id})

@app.route("/cancel/<int:download_id>", methods=["POST", "OPTIONS"])
def cancel(download_id):
    if _queue_ref:
        _queue_ref.cancel(download_id)
    return jsonify({"status": "cancelled", "id": download_id})

def start_server(queue, progress_callback=None, new_download_callback=None, host="127.0.0.1", port=6969):
    set_queue(queue, progress_callback, new_download_callback)
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True
    )
    thread.start()
    print(f"[API] Server running on http://{host}:{port}")
