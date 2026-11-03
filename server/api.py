from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

_queue_ref = None
_progress_callback = None

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

def set_queue(queue, progress_callback=None):
    global _queue_ref, _progress_callback
    _queue_ref = queue
    _progress_callback = progress_callback

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
            # Use yt-dlp extractor in background thread
            def run():
                from engine.extractor import VideoExtractor
                ext = VideoExtractor(progress_callback=_progress_callback)
                try:
                    ext.download(url)
                except Exception as e:
                    print(f"[API Extractor] Error: {e}")

            threading.Thread(target=run, daemon=True).start()
            return jsonify({
                "status": "queued",
                "type": "video",
                "url": url
            })
        else:
            # Regular file download
            _queue_ref.add(url=url, filename=filename)
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

def start_server(queue, progress_callback=None, host="127.0.0.1", port=6969):
    set_queue(queue, progress_callback)
    thread = threading.Thread(
        target=lambda: app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False
        ),
        daemon=True
    )
    thread.start()
    print(f"[API] Server running on http://{host}:{port}")
