import os
import subprocess
import hashlib
import base64
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "edid_Files")
EDID_RW_PATH = os.path.join(BASE_DIR, "edid-rw", "edid-rw")
DEFAULT_PORT = "2"


def run_command(cmd, input_data=None):
    p = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True
    )
    return p.stdout, p.stderr.decode(errors="ignore"), p.returncode


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


@app.route("/")
def index():
    files = sorted(os.listdir(SAVE_DIR))
    return render_template("index.html", files=files)


@app.route("/read_and_compare_edid", methods=["GET"])
def read_and_compare_edid():
    port = request.args.get("port", DEFAULT_PORT)

    # Read EDID
    stdout, stderr, rc = run_command([EDID_RW_PATH, port])
    if rc != 0:
        return jsonify({"error": stderr}), 500

    binary_data = stdout

    # Decode
    decode = subprocess.run(
        ["edid-decode"],
        input=binary_data,
        capture_output=True
    )

    # Compare
    current_hash = hashlib.sha256(binary_data).hexdigest()
    match = "UNKNOWN"

    for fname in os.listdir(SAVE_DIR):
        path = os.path.join(SAVE_DIR, fname)
        if os.path.isfile(path):
            if file_hash(path) == current_hash:
                match = fname
                break

    return jsonify({
        "match": match,
        "binary_b64": base64.b64encode(binary_data).decode(),
        "decoded": decode.stdout.decode(errors="ignore")
    })


@app.route("/save_edid", methods=["POST"])
def save_edid():
    data = request.json
    name = data.get("filename")
    binary_b64 = data.get("binary")

    if not name or not binary_b64:
        return jsonify({"error": "Invalid request"}), 400

    path = os.path.join(SAVE_DIR, name)
    if os.path.exists(path):
        return jsonify({"error": "File already exists"}), 400

    binary = base64.b64decode(binary_b64)
    with open(path, "wb") as f:
        f.write(binary)

    return jsonify({"saved": True})


@app.route("/write_edid", methods=["POST"])
def write_edid():
    data = request.json
    filename = data.get("filename")
    port = data.get("port", DEFAULT_PORT)

    path = os.path.join(SAVE_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "EDID file not found"}), 404

    # Load EDID binary
    with open(path, "rb") as f:
        edid_data = f.read()

    # WRITE (stdin pipe is REQUIRED)
    stdout, stderr, rc = run_command(
        [EDID_RW_PATH, "-w", "-f", port],
        input_data=edid_data
    )

    if rc != 0:
        return jsonify({"error": stderr}), 500

    # VERIFY (read back)
    stdout, stderr, rc = run_command([EDID_RW_PATH, port])
    if rc != 0:
        return jsonify({"written": True, "verified": False})

    verified = (
        file_hash(path) ==
        hashlib.sha256(stdout).hexdigest()
    )

    return jsonify({
        "written": True,
        "verified": verified
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
