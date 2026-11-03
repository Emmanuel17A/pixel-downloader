from flask import Flask, request, jsonify
import threading

app = Flask(__name__)
_queue_ref = None

def set_queue(queue):
    global _queue_ref
    _queue_ref = queue

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "app": "Pixel Downloader"})

@app.route("/add", methods=["POST"])
def add_download():
    global _queue_ref
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data.get("url")
    filename = data.get("filename")

    if _queue_ref is None:
        return jsonify({"error": "Download queue not ready"}), 503

    try:
        downloader = _queue_ref.add(url=url, filename=filename)
        return jsonify({
            "status": "queued",
            "url": url,
            "filename": filename or url.split("/")[-1]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/status", methods=["GET"])
def status():
    global _queue_ref
    if _queue_ref is None:
        return jsonify({"error": "Queue not ready"}), 503
    return jsonify({
        "active": _queue_ref.get_active_ids(),
        "queued": _queue_ref.queue_size()
    })

@app.route("/pause/<int:download_id>", methods=["POST"])
def pause(download_id):
    if _queue_ref:
        _queue_ref.pause(download_id)
    return jsonify({"status": "paused", "id": download_id})

@app.route("/resume/<int:download_id>", methods=["POST"])
def resume(download_id):
    if _queue_ref:
        _queue_ref.resume(download_id)
    return jsonify({"status": "resumed", "id": download_id})

@app.route("/cancel/<int:download_id>", methods=["POST"])
def cancel(download_id):
    if _queue_ref:
        _queue_ref.cancel(download_id)
    return jsonify({"status": "cancelled", "id": download_id})

def start_server(queue, host="127.0.0.1", port=6969):
    set_queue(queue)
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True
    )
    thread.start()
    print(f"[API] Server running on http://{host}:{port}")
