#!/bin/bash
set -e

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
SERVICE_DIR="$HOME/.config/systemd/user"

echo "=== EDID Emulator Kiosk Setup ==="

mkdir -p "$SERVICE_DIR"

# -------------------------------------------------
# Create kiosk startup script
# -------------------------------------------------
echo "Creating start_edid_ui.sh..."

cat > "$APP_DIR/start_edid_ui.sh" <<'EOF'
#!/bin/bash

LOG="$HOME/edid_kiosk.log"
exec >>"$LOG" 2>&1
echo "==== Kiosk start: $(date) ===="

APP_DIR="$HOME/edid-emulator-webapp"
BACKEND_DIR="$APP_DIR/backend"
URL="http://127.0.0.1:5000"

export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"

echo "DISPLAY=$DISPLAY"
echo "XAUTHORITY=$XAUTHORITY"

# -------------------------------------------------
# Wait for X session
# -------------------------------------------------
for i in {1..30}; do
    if xset q >/dev/null 2>&1; then
        echo "X is ready"
        break
    fi
    echo "Waiting for X..."
    sleep 1
done

# -------------------------------------------------
# Rotate display to portrait
# -------------------------------------------------
xrandr --output DSI-1 --rotate right || echo "xrandr rotate failed"

# -------------------------------------------------
# Map FT5x06 touchscreen to DSI-1
# -------------------------------------------------
TOUCH_ID=$(xinput list | grep -i 'ft5x06' | grep -o 'id=[0-9]*' | cut -d= -f2)
if [ -n "$TOUCH_ID" ]; then
    echo "Mapping touchscreen ID $TOUCH_ID"
    xinput map-to-output "$TOUCH_ID" DSI-1
else
    echo "Touchscreen device not found"
fi

# -------------------------------------------------
# Start Flask backend
# -------------------------------------------------
cd "$BACKEND_DIR" || exit 1
[ -f venv/bin/activate ] && source venv/bin/activate

echo "Starting Flask..."
python3 app.py &

# Wait for Flask
for i in {1..30}; do
    curl -s "$URL" >/dev/null && break
    echo "Waiting for Flask..."
    sleep 1
done

# -------------------------------------------------
# Launch Epiphany normally
# -------------------------------------------------
echo "Launching Epiphany..."
epiphany "$URL" &

# -------------------------------------------------
# Force fullscreen (PID-based, reliable)
# -------------------------------------------------
echo "Waiting for Epiphany window..."
for i in {1..30}; do
    EPIPHANY_PID=$(pgrep -n epiphany || true)
    if [ -n "$EPIPHANY_PID" ]; then
        WIN_ID=$(xdotool search --onlyvisible --pid "$EPIPHANY_PID" | head -n1)
        if [ -n "$WIN_ID" ]; then
            xdotool windowactivate --sync "$WIN_ID" key F11
            echo "Fullscreen applied"
            break
        fi
    fi
    sleep 0.5
done

echo "Kiosk startup complete"
wait
EOF

chmod +x "$APP_DIR/start_edid_ui.sh"

# -------------------------------------------------
# Create systemd user service
# -------------------------------------------------
echo "Creating systemd user service..."

cat > "$SERVICE_DIR/edid-emulator.service" <<EOF
[Unit]
Description=EDID Emulator Kiosk
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=$APP_DIR/start_edid_ui.sh
Restart=on-failure
Environment=DISPLAY=:0
Environment=XAUTHORITY=$HOME/.Xauthority

[Install]
WantedBy=default.target
EOF

# -------------------------------------------------
# Enable systemd user service
# -------------------------------------------------
echo "Enabling systemd service..."
systemctl --user daemon-reload
systemctl --user enable edid-emulator.service

# -------------------------------------------------
# Create desktop launcher
# -------------------------------------------------
echo "Creating desktop icon..."

mkdir -p "$HOME/Desktop"

cat > "$HOME/Desktop/EDID-Emulator.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=EDID Emulator
Exec=$APP_DIR/start_edid_ui.sh
Icon=utilities-terminal
Terminal=false
Categories=Utility;
EOF

chmod +x "$HOME/Desktop/EDID-Emulator.desktop"

echo
echo "=== Setup complete ==="
echo
echo "Reboot recommended:"
echo "  sudo reboot"
echo
echo "Startup log:"
echo "  cat ~/edid_kiosk.log"
