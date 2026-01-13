#!/usr/bin/env python3

import os
import hashlib
import subprocess
from pathlib import Path
from flask import Flask, jsonify, request, render_template

BASE = Path(__file__).resolve().parent
EDID_DIR = BASE / "edid_files"
EDID_DIR.mkdir(exist_ok=True)

app = Flask(__name__, template_folder="templates")


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)
    return h.hexdigest()


def usb_mounts():
    mounts = []
    for root in ("/media", "/run/media"):
        p = Path(root)
        if p.exists():
            for u in p.iterdir():
                if u.is_dir():
                    for d in u.iterdir():
                        if d.is_dir():
                            mounts.append(str(d))
    return mounts


def edid_index():
    idx = {}
    for f in EDID_DIR.glob("*.bin"):
        idx[f.name] = sha256(f)
    return idx


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/usb")
def list_usb():
    return jsonify(usb_mounts())


@app.route("/usb_scan")
def usb_scan():
    path = Path(request.args.get("path", ""))
    if not path.exists():
        return jsonify({"error": "USB not found"}), 400

    local_hashes = edid_index()
    results = []

    for f in path.glob("*.bin"):
        h = sha256(f)
        status = "new"
        for name, lh in local_hashes.items():
            if lh == h:
                status = "duplicate"
                break
        results.append({
            "name": f.name,
            "size": f.stat().st_size,
            "hash": h,
            "status": status
        })

    return jsonify(results)


@app.route("/usb_import", methods=["POST"])
def usb_import():
    data = request.json
    path = Path(data["path"])
    selected = data["files"]

    local_hashes = edid_index()
    imported, skipped = [], []

    for name in selected:
        src = path / name
        h = sha256(src)
        if h in local_hashes.values():
            skipped.append(name)
            continue

        dst = EDID_DIR / name
        if dst.exists():
            dst = EDID_DIR / f"imported_{name}"

        dst.write_bytes(src.read_bytes())
        imported.append(dst.name)

    return jsonify({"imported": imported, "skipped": skipped})


@app.route("/usb_export", methods=["POST"])
def usb_export():
    path = Path(request.json["path"])
    exported, skipped = [], []

    for f in EDID_DIR.glob("*.bin"):
        dst = path / f.name
        if dst.exists():
            skipped.append(f.name)
            continue
        dst.write_bytes(f.read_bytes())
        exported.append(f.name)

    return jsonify({"exported": exported, "skipped": skipped})


@app.route("/usb_eject", methods=["POST"])
def usb_eject():
    path = request.json["path"]
    subprocess.run(["udisksctl", "unmount", "-b", path], stderr=subprocess.DEVNULL)
    return jsonify({"ok": True})


@app.route("/shutdown", methods=["POST"])
def shutdown():
    subprocess.Popen(["sudo", "shutdown", "-h", "now"])
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
