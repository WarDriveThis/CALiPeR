#!/bin/bash
# Caliper Phase 1 - Dependency Installer
# Run as: bash install.sh
set -e

echo "========================================"
echo "  CALIPER - Phase 1 Install"
echo "========================================"

# Verify 64-bit OS
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ]; then
  echo "ERROR: 64-bit OS required. Detected: $ARCH"
  echo "Please flash Raspberry Pi OS Lite 64-bit and retry."
  exit 1
fi

echo "[1/6] System update..."
sudo apt update
sudo apt upgrade -y

echo "[2/6] System packages..."
sudo apt install -y \
  python3-pip \
  python3-opencv \
  python3-picamera2 \
  libopencv-dev \
  libatlas-base-dev \
  libhdf5-dev \
  git \
  sqlite3

echo "[3/6] Python packages..."
pip3 install --break-system-packages \
  flask \
  paddlepaddle \
  paddleocr

echo "[4/6] Creating directories..."
mkdir -p captures plates

echo "[5/6] Verifying camera..."
if libcamera-hello --list-cameras 2>&1 | grep -q "Available cameras"; then
  echo "  Camera detected OK"
else
  echo "  WARNING: No camera detected. Check raspi-config and cable."
fi

echo "[6/6] Installing systemd service..."
# Patch service file with actual home dir
ACTUAL_HOME=$(eval echo ~$USER)
ACTUAL_USER=$USER
sed "s|/home/pi/caliper|$ACTUAL_HOME/caliper|g; s|User=pi|User=$ACTUAL_USER|g" \
  caliper.service | sudo tee /etc/systemd/system/caliper.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable caliper

echo ""
echo "========================================"
echo "  Installation complete."
echo ""
echo "  Start service:  sudo systemctl start caliper"
echo "  View logs:      journalctl -u caliper -f"
echo "  Web UI:         http://$(hostname -I | awk '{print $1}'):5000"
echo "========================================"
