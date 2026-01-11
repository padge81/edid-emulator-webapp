from flask import Flask, request, jsonify, render_template
import subprocess
import os
import signal
import base64

app = Flask(__name__)

# ----------------------------
# Configuration
# ----------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(SCRIPT_DIR, "edid_Files")
EDID_RW_PATH = os.path.join(SCRIPT_DIR, "edid-rw", "edid-rw")
VERSION = "1.0.11"

GITHUB_PAT = os.environ.get("GITHUB_PAT")  # MUST be set in environment

DEFAULT_PORT = "2"

os.makedirs(SAVE_DIR, exist_ok=True)

# ----------------------------
# Helpers
# ----------------------------

def safe_filename(name: str) -> bool:
    return name and "/" not in name and ".." not in name

def run_command(cmd, stdin_file=None):
    try:
        with open(stdin_file, "rb") if stdin_file else subprocess.DEVNULL as stdin:
            result = subprocess.run(
                cmd,
                stdin=stdin,
                capture_output=True,
                text=True
            )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

# ----------------------------
# Routes
# ----------------------------

@app.route("/")
def index():
    return render_template("index.html", version=VERSION)

@app.route("/detect_hdmi", methods=["GET"])
def detect_hdmi():
    return jsonify({"port": DEFAULT_PORT})

@app.route("/read_edid", methods=["GET"])
def read_edid():
    port = request.args.get("port", DEFAULT_PORT)
    cmd = [EDID_RW_PATH, port]
    stdout, stderr, rc = run_command(cmd)
    if rc != 0:
        return jsonify({"error": stderr}), 500
    return jsonify({"raw_edid": stdout})

# ----------------------------
# EDID File Management
# ----------------------------

@app.route("/list_files", methods=["GET"])
def list_files():
    files = sorted(
        f for f in os.listdir(SAVE_DIR)
        if os.path.isfile(os.path.join(SAVE_DIR, f))
    )
    return jsonify({"files": files})

@app.route("/read_edid_file", methods=["GET"])
def read_edid_file():
    filename = request.args.get("filename", "")
    if not safe_filename(filename):
        return jsonify({"error": "Invalid filename"}), 400

    path = os.path.join(SAVE_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return jsonify({"edid_content": encoded})

@app.route("/write_edid_from_file", methods=["POST"])
def write_edid_from_file():
    data = request.get_json(force=True)
    filename = data.get("filename")
    port = data.get("port", DEFAULT_PORT)

    if not safe_filename(filename):
        return jsonify({"error": "Invalid filename"}), 400

    path = os.path.join(SAVE_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    cmd = [EDID_RW_PATH, "-w", port]
    stdout, stderr, rc = run_command(cmd, stdin_file=path)

    if rc != 0:
        return jsonify({"error": stderr}), 500

    return jsonify({"message": f"EDID written from {filename}."})

@app.route("/verify_edid", methods=["POST"])
def verify_edid():
    data = request.get_json(force=True)
    filename = data.get("filename")
    port = data.get("port", DEFAULT_PORT)

    if not safe_filename(filename):
        return jsonify({"error": "Invalid filename"}), 400

    reference = os.path.join(SAVE_DIR, filename)
    current = os.path.join(SAVE_DIR, "_current_edid.bin")

    # Read current EDID
    cmd = [EDID_RW_PATH, port]
    stdout, stderr, rc = run_command(cmd)
    if rc != 0:
        return jsonify({"error": stderr}), 500

    with open(current, "wb") as f:
        f.write(stdout.encode())

    match = subprocess.run(
        ["diff", reference, current],
        capture_output=True
    ).returncode == 0

    return jsonify({"match": match})

# ----------------------------
# Repository Update
# ----------------------------

@app.route("/update_repo", methods=["POST"])
def update_repo():
    if not GITHUB_PAT:
        return jsonify({"error": "GITHUB_PAT not set"}), 500

    repo_dir = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    repo_url = "https://github.com/padge81/edid-emulator-webapp.git"
    auth_url = repo_url.replace("https://", f"https://{GITHUB_PAT}@")

    result = subprocess.run(
        ["git", "-C", repo_dir, "pull", auth_url],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return jsonify({"error": result.stderr}), 500

    # Graceful restart (let systemd/docker restart us)
    os.kill(os.getpid(), signal.SIGTERM)

    return jsonify({"message": "Repository updated, restarting..."})

# ----------------------------
# Main
# ----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
