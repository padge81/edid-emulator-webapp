import os
import subprocess
import hashlib
import base64
import difflib
import shutil
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "edid_Files")
EDID_RW_PATH = os.path.join(BASE_DIR, "edid-rw", "edid-rw")

USB_ROOT = "/media/mint"

DEFAULT_PORT = "2"
AVAILABLE_PORTS = ["0", "1", "2", "3"]

# ----------------------------
# Utility helpers
# ----------------------------

def run_command(cmd, input_data=None):
    p = subprocess.run(cmd, input=input_data, capture_output=True)
    return p.stdout, p.stderr.decode(errors="ignore"), p.returncode

def file_hash_bytes(data: bytes):
    return hashlib.sha256(data).hexdigest()

def file_hash(path):
    with open(path, "rb") as f:
        return file_hash_bytes(f.read())

def list_usb_mounts():
    if not os.path.isdir(USB_ROOT):
        return []
    return [
        os.path.join(USB_ROOT, d)
        for d in os.listdir(USB_ROOT)
        if os.path.isdir(os.path.join(USB_ROOT, d))
    ]

def is_read_only(path):
    try:
        test = os.path.join(path, ".write_test")
        with open(test, "w") as f:
            f.write("x")
        os.remove(test)
        return False
    except Exception:
        return True

# ----------------------------
# Main UI
# ----------------------------

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

# ----------------------------
# Version / Update
# ----------------------------

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

# ----------------------------
# EDID CORE (UNCHANGED)
# ----------------------------

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
    name = data.get("filename", "").strip()
    binary_b64 = data.get("binary")

    if not name:
        return jsonify({"error": "Filename required"}), 400

    if not name.lower().endswith(".bin"):
        name += ".bin"

    path = os.path.join(SAVE_DIR, name)
    if os.path.exists(path):
        return jsonify({"error": "File already exists"}), 400

    with open(path, "wb") as f:
        f.write(base64.b64decode(binary_b64))

    return jsonify({"saved": True, "filename": name})


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

# ----------------------------
# USB SUPPORT
# ----------------------------

@app.route("/usb/status")
def usb_status():
    mounts = list_usb_mounts()
    result = []
    for m in mounts:
        result.append({
            "path": m,
            "name": os.path.basename(m),
            "read_only": is_read_only(m)
        })
    return jsonify(result)

@app.route("/usb/scan")
def usb_scan():
    mount = request.args.get("mount")
    if not mount or not os.path.isdir(mount):
        return jsonify({"error": "Invalid mount"}), 400

    usb_bins = [
        f for f in os.listdir(mount)
        if f.lower().endswith(".bin")
        and os.path.isfile(os.path.join(mount, f))
    ]

    local_hashes = {
        f: file_hash(os.path.join(SAVE_DIR, f))
        for f in os.listdir(SAVE_DIR)
        if f.lower().endswith(".bin")
    }

    files = []
    for f in usb_bins:
        usb_path = os.path.join(mount, f)
        usb_hash = file_hash(usb_path)
        exists = usb_hash in local_hashes.values()

        files.append({
            "name": f,
            "exists": exists
        })

    return jsonify(files)

@app.route("/usb/import", methods=["POST"])
def usb_import():
    data = request.json
    mount = data.get("mount")
    files = data.get("files", [])

    imported = []

    for f in files:
        src = os.path.join(mount, f)
        dst = os.path.join(SAVE_DIR, f)

        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            imported.append(f)

    return jsonify({"imported": imported})

@app.route("/usb/export", methods=["POST"])
def usb_export():
    data = request.json
    mount = data.get("mount")
    files = data.get("files", [])

    exported = []

    for f in files:
        src = os.path.join(SAVE_DIR, f)
        dst = os.path.join(mount, f)

        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            exported.append(f)

    return jsonify({"exported": exported})

# ----------------------------
# Power
# ----------------------------

@app.route("/shutdown", methods=["POST"])
def shutdown():
    subprocess.Popen(["sudo", "shutdown", "-h", "now"])
    return jsonify({"ok": True})

@app.route("/reboot", methods=["POST"])
def reboot():
    subprocess.Popen(["sudo", "reboot"])
    return jsonify({"ok": True})

# ----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
