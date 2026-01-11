#!/bin/bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== EDID Emulator Web App Setup ==="

# ----------------------------
# Clone edid-rw if missing
# ----------------------------
if [ ! -d "$APP_DIR/edid-rw" ]; then
    echo "Cloning edid-rw repository..."
    git clone https://github.com/bulletmark/edid-rw "$APP_DIR/edid-rw"
else
    echo "edid-rw already exists, skipping clone."
fi

# ----------------------------
# Test EDID read
# ----------------------------
echo "Running test read..."
cd "$APP_DIR/edid-rw"
sudo ./edid-rw 2 | edid-decode || echo "Warning: test read failed"
cd "$APP_DIR"
echo "Test read completed."

# ----------------------------
# Create .env file if missing
# ----------------------------
ENV_FILE="$APP_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    echo ".env already exists — skipping token setup."
else
    echo ""
    echo "GitHub Personal Access Token is required for repo updates."
    echo "The token will be stored locally in .env and NOT committed."
    echo ""

    read -s -p "Enter GitHub PAT: " GITHUB_PAT
    echo ""
    read -s -p "Confirm GitHub PAT: " GITHUB_PAT_CONFIRM
    echo ""

    if [ "$GITHUB_PAT" != "$GITHUB_PAT_CONFIRM" ]; then
        echo "ERROR: Tokens do not match."
        exit 1
    fi

    echo "GITHUB_PAT=$GITHUB_PAT" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"

    echo ".env file created at $ENV_FILE"
    echo "Permissions set to 600 (owner read/write only)."
fi

echo ""
echo "Setup complete."
echo "Next steps:"
echo "  1) Install Python requirements: pip3 install -r requirements.txt"
echo "  2) Configure and start the systemd service"
echo ""
