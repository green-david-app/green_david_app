from flask import Flask, send_from_directory, render_template_string
import os

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Serve index.html from the repo root
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# Health check (Render)
@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
