from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)
@app.route("/")
def index():
    return send_from_directory("C:\\viddrop", "index.html")
CORS(app)

DOWNLOAD_DIR = "C:\\viddrop\\downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}

def cleanup_file(filepath, delay=3600):
    def _del():
        time.sleep(delay)
        if os.path.exists(filepath):
            os.remove(filepath)
    threading.Thread(target=_del, daemon=True).start()

@app.route("/api/convert", methods=["POST"])
def convert():
    data = request.json
    url = data.get("url", "").strip()
    fmt = data.get("format", "mp3")
    quality = data.get("quality", "320")
    if not url:
        return jsonify({"error": "URL manquante"}), 400
    job_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_DIR, job_id)
    if fmt == "mp3":
        bitrate = quality.replace(" kbps", "").replace("kbps", "").strip()
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_path + ".%(ext)s",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": bitrate}],
            "quiet": True,
            "ffmpeg_location": "C:\\ffmpeg2\\ffmpeg-8.1.1-essentials_build\\bin",
        }
    else:
        res_map = {"4K": "2160", "1080p": "1080", "720p": "720", "480p": "480"}
        res = res_map.get(quality, "1080")
        ydl_opts = {
            "format": "best",
            "outtmpl": output_path + ".%(ext)s",
            "merge_output_format": "mp4",
            "quiet": True,
            "w": "C:\\ffmpeg2\\ffmpeg-8.1.1-essentials_build\\bin",
        }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "fichier")
            ext = "mp3" if fmt == "mp3" else "mp4"
            final_path = output_path + "." + ext
        cleanup_file(final_path)
        jobs[job_id] = {"path": final_path, "title": title, "ext": ext}
        return jsonify({"job_id": job_id, "title": title, "format": ext, "download_url": "/api/download/" + job_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or not os.path.exists(job["path"]):
        return jsonify({"error": "Fichier introuvable ou expire"}), 404
        
    return send_file(job["path"], as_attachment=True, download_name=job["title"] + "." + job["ext"])

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
