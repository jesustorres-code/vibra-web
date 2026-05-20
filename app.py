import os
import json
import subprocess
import tempfile
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

VIBRA = "/home/ubuntu/Documents/SkyNodeOps/tools/vibra/build/cli/vibra"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/recognize", methods=["POST"])
def recognize():
    audio = request.files.get("audio")
    if not audio:
        return jsonify({"error": "No audio received"}), 400

    with tempfile.TemporaryDirectory() as tmp:
        raw_path = os.path.join(tmp, "input.webm")
        wav_path = os.path.join(tmp, "input.wav")
        audio.save(raw_path)

        # Convert to WAV (16kHz mono, what vibra handles well)
        convert = subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path,
             "-ar", "44100", "-ac", "1", wav_path],
            capture_output=True
        )
        if convert.returncode != 0:
            return jsonify({"error": "Audio conversion failed",
                            "detail": convert.stderr.decode()}), 500

        result = subprocess.run(
            [VIBRA, "--recognize", "--file", wav_path],
            capture_output=True, text=True
        )

        if result.returncode != 0 or not result.stdout.strip():
            return jsonify({"error": "Song not recognized"}), 404

        try:
            data = json.loads(result.stdout)
            track = data.get("track", {})
            images = track.get("images", {})
            return jsonify({
                "title": track.get("title", "Unknown"),
                "artist": track.get("subtitle", "Unknown"),
                "album": track.get("sections", [{}])[0].get("metadata", [{}])[0].get("text", "") if track.get("sections") else "",
                "cover": images.get("coverarthq") or images.get("coverart", ""),
                "shazam_url": track.get("url", ""),
                "genre": track.get("genres", {}).get("primary", ""),
            })
        except (json.JSONDecodeError, KeyError) as e:
            return jsonify({"error": f"Parse error: {e}", "raw": result.stdout}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7777, debug=False)
