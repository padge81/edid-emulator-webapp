from flask import Flask, request, jsonify, render_template
import subprocess
import os

app = Flask(__name__)

# Determine the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Directory to save EDID files
save_dir = os.path.join(script_dir, 'edid_Files')

# Ensure the save directory exists
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# Path to edid-rw executable
edid_rw_path = os.path.join(script_dir, 'edid-rw', 'edid-rw')

def run_command(command):
    """Execute shell command safely, return stdout and stderr."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect_hdmi', methods=['GET'])
def detect_hdmi():
    port = 2  # default port
    return jsonify({'port': port})

@app.route('/read_edid', methods=['GET'])
def read_edid():
    port = request.args.get('port', default='2')
    cmd = f"sudo \"{edid_rw_path}\" {port} | edid-decode"
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'decoded_edid': stdout})

@app.route('/save_edid', methods=['POST'])
def save_edid():
    data = request.get_json()
    port = data.get('port', '2')
    filename = data.get('filename', 'EDID.bin').strip()

    # Save directory and filename handling
    save_path = os.path.join(save_dir, filename)

    # Avoid overwriting files
    base, ext = os.path.splitext(save_path)
    count = 1
    while os.path.exists(save_path):
        save_path = f"{base}_{count}{ext}"
        count += 1

    # Save command
    cmd = f"sudo \"{edid_rw_path}\" {port} > \"{save_path}\""
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500

    relative_path = os.path.relpath(save_path, script_dir)
    return jsonify({'message': f'EDID saved to {relative_path}.'})

@app.route('/write_edid', methods=['POST'])
def write_edid():
    data = request.get_json()
    port = data.get('port', '2')
    filename = data.get('filename', 'EDID.bin')
    filepath = os.path.join(save_dir, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found.'}), 400
    cmd = f"sudo \"{edid_rw_path}\" -w {port} < \"{filepath}\""
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'message': f'EDID written from {filename}.'})

@app.route('/verify_edid', methods=['POST'])
def verify_edid():
    data = request.get_json()
    port = data.get('port', '2')
    filename = data.get('filename', 'EDID.bin')
    filepath = os.path.join(save_dir, filename)
    temp_file = os.path.join(save_dir, 'current_EDID.bin')

    # Save current EDID
    cmd_read = f"sudo \"{edid_rw_path}\" {port} > \"{temp_file}\""
    run_command(cmd_read)

    # Compare with saved file
    cmd_diff = f"diff \"{filepath}\" \"{temp_file}\""
    stdout, _ = run_command(cmd_diff)

    match = (stdout.strip() == '')
    return jsonify({'match': match})

if __name__ == '__main__':
    # Run Flask app
    app.run(host='0.0.0.0', port=5000)
    