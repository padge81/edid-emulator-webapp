#!/bin/bash

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
URL="http://127.0.0.1:5000"

# Ensure DISPLAY is set (important for startup)
export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"

# Start Flask backend
cd "$BACKEND_DIR"
source venv/bin/activate 2>/dev/null || true
python3 app.py &

FLASK_PID=$!

# Wait for Flask to come up
echo "Waiting for Flask..."
for i in {1..15}; do
    curl -s "$URL" >/dev/null && break
    sleep 1
done

# Launch Epiphany
epiphany "$URL" &

BROWSER_PID=$!

# Wait for window
sleep 5

# Fullscreen (F11)
xdotool search --onlyvisible --class epiphany windowactivate --sync key F11

wait $FLASK_PID
