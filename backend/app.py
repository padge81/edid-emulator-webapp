#!/usr/bin/env python3
import os
import subprocess
import base64
import json
import difflib
import time
from flask import Flask, render_template, request, jsonify

APP_VERSION = "1.3.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EDID_DIR = os.path.join(BASE_DIR, "edid_files")
USB_MOUNT_BASE = "/media"

app = Flask(__name__)

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def list_ports():
    ports = []
    for i in range(0, 4):
        path = f"/dev/i2c-{i}"
        if os.path.exists(path):
            ports.append(path)
    return ports or ["/dev/i2c-1"]

def list_edid_files():
    if not os.path.exists(EDID_DIR):
        os.makedirs(EDID_DIR)
    return sorted(f for f in os.listdir(EDID_DIR) if f.endswith(".bin"))

def read_edid(port):
    out = run(["get-edid", "-b", port])
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return out.stdout.encode("latin1")

def decode_edid(bin_data):
    p = subprocess.Popen(
        ["edid-decode"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, _ = p.communicate(bin_data.decode("latin1"))
    return out

def compare_known(edid_bin):
    for fname in list_edid_files():
        with open(os.path.join(EDID_DIR, fname), "rb") as f:
            if f.read() == edid_bin:
                return fname
    return "UNKNOWN"

def find_usb_mounts():
    mounts = []
    if os.path.exists(USB_MOUNT_BASE):
        for d in os.listdir(USB_MOUNT_BASE):
            path = os.path.join(USB_MOUNT_BASE, d)
            if os.path.ismount(path):
                mounts.append(path)
    return mounts

# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        ports=list_ports(),
        default_port=list_ports()[0],
        files=list_edid_files(),
    )

@app.route("/version")
def version():
    return jsonify(version=APP_VERSION)

@app.route("/update_repo", methods=["POST"])
def update_repo():
    try:
        run(["git", "pull"])
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(error=str(e))

@app.route("/read_and_compare_edid")
def read_and_compare():
    try:
        port = request.args.get("port")
        edid_bin = read_edid(port)
        decoded = decode_edid(edid_bin)
        match = compare_known(edid_bin)

        return jsonify(
            binary_b64=base64.b64encode(edid_bin).decode(),
            decoded=decoded,
            match=match,
        )
    except Exception as e:
        return jsonify(error=str(e))

@app.route("/save_edid", methods=["POST"])
def save_edid():
    data = request.json
    fname = data["filename"]
    if not fname.endswith(".bin"):
        fname += ".bin"

    path = os.path.join(EDID_DIR, fname)
    if os.path.exists(path):
        return jsonify(error="File already exists")

    with open(path, "wb") as f:
        f.write(base64.b64decode(data["binary"]))

    return jsonify(ok=True)

@app.route("/write_edid", methods=["POST"])
def write_edid():
    data = request.json
    fname = data["filename"]
    port = data["port"]

    path = os.path.join(EDID_DIR, fname)
    if not os.path.exists(path):
        return jsonify(error="EDID file not found")

    run(["i2cset", "-f", "-y", port.split("-")[-1], "0x50", "0x00"])
    run(["edid-rw", "-w", path, port])
    time.sleep(1)

    # verify
    written = read_edid(port)
    with open(path, "rb") as f:
        original = f.read()

    if written == original:
        return jsonify(verified=True)

    diff = "\n".join(
        difflib.unified_diff(
            original.hex().split(),
            written.hex().split(),
            lineterm="",
        )
    )
    return jsonify(verified=False, diff=diff)

@app.route("/usb/import", methods=["POST"])
def usb_import():
    mounts = find_usb_mounts()
    imported = 0

    for m in mounts:
        for f in os.listdir(m):
            if f.endswith(".bin"):
                src = os.path.join(m, f)
                dst = os.path.join(EDID_DIR, f)
                if not os.path.exists(dst):
                    with open(src, "rb") as s, open(dst, "wb") as d:
                        d.write(s.read())
                    imported += 1

    return jsonify(message=f"Imported {imported} new EDID files")

@app.route("/usb/export", methods=["POST"])
def usb_export():
    mounts = find_usb_mounts()
    exported = 0

    for m in mounts:
        for f in list_edid_files():
            src = os.path.join(EDID_DIR, f)
            dst = os.path.join(m, f)
            if not os.path.exists(dst):
                with open(src, "rb") as s, open(dst, "wb") as d:
                    d.write(s.read())
                exported += 1

    return jsonify(message=f"Exported {exported} EDID files")

@app.route("/shutdown", methods=["POST"])
def shutdown():
    run(["sudo", "shutdown", "-h", "now"])
    return ("", 204)

# -------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
