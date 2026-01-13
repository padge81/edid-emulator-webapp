import os
import subprocess
import hashlib
import base64
import difflib
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "edid_Files")
EDID_RW_PATH = os.path.join(BASE_DIR, "edid-rw", "edid-rw")

DEFAULT_PORT = "2"
AVAILABLE_PORTS = ["0", "1", "2", "3"]


def run_command(cmd, input_data=None):
    p = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True
    )
    return p.stdout, p.stderr.decode(errors="ignore"), p.returncode


def file_hash_bytes(data: bytes):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    with open(path, "rb") as f:
        return file_hash_bytes(f.read())


@app.route("/")
def index():
    files = sorted(
        f for f in os.listdir(SAVE_DIR)
        if os.path.isfile(os.path.join(SAVE_DIR, f))
    )
    return render_template(
        "index.html",
        files=files,
        ports=AVAILABLE_PORTS,
        default_port=DEFAULT_PORT
    )


@app.route("/version")
def version():
    try:
        out = subprocess.check_output(
            ["git", "describe", "--tags", "--dirty", "--always"],
            cwd=BASE_DIR
        )
        return jsonify({"version": out.decode().strip()})
    except Exception:
        return jsonify({"version": "unknown"})


@app.route("/update_repo", methods=["POST"])
def update_repo():
    try:
        subprocess.check_call(["git", "pull"], cwd=BASE_DIR)
        return jsonify({"updated": True})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/read_and_compare_edid")
def read_and_compare_edid():
    port = request.args.get("port", DEFAULT_PORT)

    stdout, stderr, rc = run_command([EDID_RW_PATH, port])
    if rc != 0:
        return jsonify({"error": stderr}), 500

    binary_data = stdout

    decode = subprocess.run(
        ["edid-decode"],
        input=binary_data,
        capture_output=True
    )

    current_hash = file_hash_bytes(binary_data)
    match = "UNKNOWN"

    for fname in os.listdir(SAVE_DIR):
        path = os.path.join(SAVE_DIR, fname)
        if os.path.isfile(path) and file_hash(path) == current_hash:
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

    path = os.path.join(SAVE_DIR, name)
    if os.path.exists(path):
        return jsonify({"error": "File already exists"}), 400

    with open(path, "wb") as f:
        f.write(base64.b64decode(binary_b64))

    return jsonify({"saved": True})


@app.route("/write_edid", methods=["POST"])
def write_edid():
    data = request.json
    filename = data.get("filename")
    port = data.get("port", DEFAULT_PORT)

    path = os.path.join(SAVE_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "EDID file not found"}), 404

    with open(path, "rb") as f:
        intended = f.read()

    _, stderr, rc = run_command(
        [EDID_RW_PATH, "-w", "-f", port],
        input_data=intended
    )
    if rc != 0:
        return jsonify({"error": stderr}), 500

    read_back, _, rc = run_command([EDID_RW_PATH, port])
    if rc != 0:
        return jsonify({"written": True, "verified": False})

    ok = file_hash_bytes(intended) == file_hash_bytes(read_back)

    diff = None
    if not ok:
        diff = "\n".join(
            difflib.unified_diff(
                intended.hex().split(),
                read_back.hex().split(),
                fromfile="intended",
                tofile="read-back",
                lineterm=""
            )
        )

    return jsonify({"written": True, "verified": ok, "diff": diff})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
