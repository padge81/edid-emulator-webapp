from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

# Determine the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Full path to the edid-rw executable
edid_rw_path = os.path.join(script_dir, 'edid-rw', 'edid-rw')

# Helper function to run shell commands with the correct path
def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

# Root route to confirm server is running
@app.route('/')
def index():
    return "EDID Management API is running."

# Detect HDMI port (stub implementation)
@app.route('/detect_hdmi', methods=['GET'])
def detect_hdmi():
    port = 2
    return jsonify({'port': port})

# Read EDID data from HDMI port
@app.route('/read_edid', methods=['GET'])
def read_edid():
    port = request.args.get('port', default='2')
    # Run edid-rw to read EDID and decode
    cmd = f"sudo \"{edid_rw_path}\" {port} | edid-decode"
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'decoded_edid': stdout})

# Save EDID to a file
@app.route('/save_edid', methods=['POST'])
def save_edid():
    data = request.get_json()
    port = data.get('port', '2')
    filename = data.get('filename', 'EDID.bin')
    # Save EDID to file
    cmd = f"sudo \"{edid_rw_path}\" {port} > {filename}"
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'message': f'EDID saved to {filename}.'})

# Write EDID from a file
@app.route('/write_edid', methods=['POST'])
def write_edid():
    data = request.get_json()
    port = data.get('port', '2')
    filename = data.get('filename', 'EDID.bin')
    # Write EDID from file
    cmd = f"sudo \"{edid_rw_path}\" -w {port} < {filename}"
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'message': f'EDID written from {filename}.'})

# Verify if current EDID matches a file
@app.route('/verify_edid', methods=['POST'])
def verify_edid():
    data = request.get_json()
    port = data.get('port', '2')
    filename = data.get('filename', 'EDID.bin')

    # Save current EDID to a temp file
    temp_file = 'current_EDID.bin'
    cmd_read = f"sudo \"{edid_rw_path}\" {port} > {temp_file}"
    run_command(cmd_read)

    # Compare the saved EDID file with the provided one
    cmd_diff = f"diff {filename} {temp_file}"
    stdout, stderr = run_command(cmd_diff)

    # If stdout is empty, files are identical
    match = (stdout.strip() == '')
    return jsonify({'match': match})

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000)