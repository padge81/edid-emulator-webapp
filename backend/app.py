from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

# Helper function to run shell commands
def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr

@app.route('/detect_hdmi', methods=['GET'])
def detect_hdmi():
    # Implement detection logic here
    # For now, assume port 2
    port = 2
    return jsonify({'port': port})

@app.route('/read_edid', methods=['GET'])
def read_edid():
    port = request.args.get('port', default='2')
    # Read EDID using edid-rw
    cmd = f"sudo ./edid-rw {port} | edid-decode"
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'decoded_edid': stdout})

@app.route('/save_edid', methods=['POST'])
def save_edid():
    port = request.json.get('port', '2')
    filename = request.json.get('filename', 'EDID.bin')
    # Save EDID to file
    cmd = f"sudo ./edid-rw {port} > {filename}"
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'message': f'EDID saved to {filename}'})

@app.route('/write_edid', methods=['POST'])
def write_edid():
    port = request.json.get('port', '2')
    filename = request.json.get('filename', 'EDID.bin')
    # Write EDID from file
    cmd = f"sudo ./edid-rw -w {port} < {filename}"
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'message': f'EDID written from {filename}'})

@app.route('/verify_edid', methods=['POST'])
def verify_edid():
    port = request.json.get('port', '2')
    filename = request.json.get('filename', 'EDID.bin')
    # Read current EDID
    cmd_read = f"sudo ./edid-rw {port} > current_EDID.bin"
    run_command(cmd_read)
    # Compare files (simple checksum or binary compare)
    # For simplicity, check if files are identical
    cmd_diff = f"diff {filename} current_EDID.bin"
    stdout, stderr = run_command(cmd_diff)
    match = stdout.strip() == ''
    return jsonify({'match': match})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)