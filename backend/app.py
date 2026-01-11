from flask import Flask, request, jsonify, render_template
import subprocess
import os

app = Flask(__name__)

# Directory setup
script_dir = os.path.dirname(os.path.abspath(__file__))
save_dir = os.path.join(script_dir, 'edid_Files')
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# Path to edid-rw
edid_rw_path = os.path.join(script_dir, 'edid-rw', 'edid-rw')

# Your GitHub PAT
GITHUB_PAT = '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'

# Hardcoded version
VERSION = "1.0.0"

def run_command(command, cwd=None):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

@app.route('/')
def index():
    return render_template('index.html', version=VERSION)

@app.route('/detect_hdmi', methods=['GET'])
def detect_hdmi():
    return jsonify({'port': 2})

@app.route('/read_edid', methods=['GET'])
def read_edid():
    port = request.args.get('port', default='2')
    cmd = f"sudo \"{edid_rw_path}\" {port} | edid-decode"
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'decoded_edid': stdout})

# --- EDID Files Management ---

@app.route('/list_files', methods=['GET'])
def list_files():
    files = [f for f in os.listdir(save_dir) if os.path.isfile(os.path.join(save_dir, f))]
    return jsonify({'files': files})

@app.route('/read_edid_file', methods=['GET'])
def read_edid_file():
    filename = request.args.get('filename')
    filepath = os.path.join(save_dir, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        b64_data = base64.b64encode(data).decode('utf-8')
        return jsonify({'edid_content': b64_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/write_edid_from_file', methods=['POST'])
def write_edid_from_file():
    data = request.get_json()
    filename = data.get('filename')
    port = data.get('port', '2')
    filepath = os.path.join(save_dir, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    cmd = f"sudo \"{edid_rw_path}\" -w {port} < \"{filepath}\""
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'message': f'EDID written from {filename}.'})

@app.route('/verify_edid', methods=['POST'])
def verify_edid():
    data = request.get_json()
    filename = data.get('filename')
    port = data.get('port', '2')
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

# --- Repository update with PAT ---

@app.route('/update_repo', methods=['POST'])
def update_repo():
    passcode = request.get_json().get('passcode', '')
    # Optional: add passcode check for security
    # if passcode != 'your_secure_passcode':
    #     return jsonify({'error': 'Invalid passcode'}), 403

    if not GITHUB_PAT:
        return jsonify({'error': 'GitHub PAT not configured'}), 500

    # Directory is parent of app.py
    repo_dir = os.path.abspath(os.path.join(script_dir, '..'))

    repo_url = 'https://github.com/padge81/edid-emulator-webapp.git'
    auth_repo_url = repo_url.replace('https://', f'https://{GITHUB_PAT}@')

    # Run git pull
    cmd = f'git -C "{repo_dir}" pull {auth_repo_url}'
    stdout, stderr = run_command(cmd)
    if stderr:
        return jsonify({'error': stderr}), 500
    return jsonify({'message': 'Repository updated successfully.', 'output': stdout})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)