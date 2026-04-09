import os
import json
import re
import anthropic
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Serve static files from root of repo
app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# API key from Render environment variable
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ----------------------
# Root / health check
# ----------------------
@app.route("/", methods=["GET"])
def health():
    index_path = os.path.join(app.static_folder, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(app.static_folder, "index.html")
    return jsonify({"status": "STRIDE proxy is running"})

# ----------------------
# AI generation endpoint
# ----------------------
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"error": "Missing prompt field"}), 400

    prompt = data["prompt"]
    print(f"\n→ Sending to Anthropic...")

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        text = next((b.text for b in message.content if b.type == "text"), "")
        if not text:
            return jsonify({"error": "Empty response from Claude"}), 500

        print(f"← Claude responded ({len(text)} chars)")

        clean = re.sub(r"```json|```", "", text).strip()

        try:
            parsed = json.loads(clean)
            if isinstance(parsed, list):
                workouts = parsed
            elif "workouts" in parsed:
                workouts = parsed["workouts"]
            elif "plan" in parsed:
                workouts = parsed["plan"]
            else:
                workouts = parsed
        except json.JSONDecodeError:
            match = re.search(r"\[[\s\S]*\]", clean)
            if not match:
                return jsonify({"error": "Could not extract workout array"}), 500
            workouts = json.loads(match.group())

        return jsonify({"workouts": workouts})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ----------------------
# Serve any other static files
# ----------------------
@app.route("/<path:path>", methods=["GET"])
def serve_static(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    # Fallback to index.html for SPA
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
