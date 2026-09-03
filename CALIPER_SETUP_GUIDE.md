# CALIPER — Installation & Setup Guide
# Phase 1: OCR Capture + Web UI + WiFi Access Point
# Hardware: Raspberry Pi 4B · UC-A37 Rev B Camera · 32GB SD

---
This file is part of CALiPeR. CALiPeR is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>. 


## OVERVIEW

This document covers the complete setup of Caliper Phase 1 from a blank SD card
to a running system accessible via WiFi from any phone or laptop. The Pi operates
as its own WiFi access point (no router required) so the system is fully
self-contained and field-deployable.

---

## PART 1 — OPERATING SYSTEM INSTALLATION

### 1.1 Requirements
- Raspberry Pi 4B (2GB minimum, 4GB recommended)
- 32GB microSD card (Class 10 / A1 or better)
- A computer with Raspberry Pi Imager installed
  Download: https://www.raspberrypi.com/software/
- UC-A37 Rev B camera module and ribbon cable

### 1.2 Flash the OS

1. Insert the SD card into your computer.

2. Open Raspberry Pi Imager.

3. Click "Choose Device" → select Raspberry Pi 4.

4. Click "Choose OS":
   - Select "Raspberry Pi OS (other)"
   - Select "Raspberry Pi OS Lite (64-bit)"
   - IMPORTANT: Must be 64-bit Lite. Do NOT select the Desktop version.
   - Confirm the description shows "Debian Bookworm" (2024 release)

5. Click "Choose Storage" → select your SD card.

6. Click the gear icon (⚙) or "Edit Settings" to configure:

   GENERAL tab:
   - Set hostname: caliper
   - Set username: pi
   - Set password: (choose a strong password, note it)
   - Do NOT configure WiFi here — the Pi will be its own AP

   SERVICES tab:
   - Enable SSH: checked
   - Use password authentication

7. Click "Save" then "Write". Confirm when prompted. Wait for write + verify.

8. Eject the SD card when complete.

---

## PART 2 — HARDWARE ASSEMBLY

### 2.1 Camera Connection

1. Power off the Pi (do not connect power yet).

2. Locate the camera connector on the Pi 4B — it is labeled "CAMERA" and
   is the smaller of the two ribbon cable connectors (the larger is DISPLAY).

3. Gently lift the plastic locking tab on the connector.

4. Insert the UC-A37 ribbon cable with the metal contacts facing the HDMI ports
   (away from the USB ports). The blue side of the cable faces toward USB.

5. Press the locking tab down firmly until it clicks.

6. The camera board can be mounted with the lens facing forward (toward the
   direction of travel) or adjusted as needed.

### 2.2 Power

- Use a quality USB-C power supply: 5V / 3A minimum.
- In vehicle deployment: use a 12V → 5V USB-C buck converter rated 3A+
  connected to an accessory (ignition-switched) circuit.

---

## PART 3 — FIRST BOOT AND INITIAL CONFIGURATION

### 3.1 First Boot

1. Insert the SD card into the Pi.
2. Connect a keyboard and HDMI monitor for initial setup (or use SSH — see 3.2).
3. Connect power. The Pi will boot. First boot takes 60–90 seconds.
4. Log in with username: pi and the password you set in Imager.

### 3.2 SSH Access (Alternative to Monitor/Keyboard)

If you configured SSH in Imager, you can access the Pi over a wired connection:

1. Connect Pi to a router/switch via Ethernet.
2. From your computer: ssh pi@caliper.local
   (On Windows, use PuTTY or Windows Terminal)
3. Accept the host key fingerprint when prompted.
4. Enter your password.

### 3.3 Enable the Camera Interface

Run the configuration tool:

    sudo raspi-config

Navigate:
  → 3 Interface Options
  → I1 Legacy Camera  → select NO (use modern libcamera stack)
  → Back to main menu

Then verify the camera overlay is set correctly:

    sudo nano /boot/firmware/config.txt

Check that these lines are present (add if missing):

    camera_auto_detect=1
    dtoverlay=imx477

If you see camera_auto_detect=1 already, the IMX477 overlay may be set
automatically. Save with Ctrl+O, Enter, Ctrl+X.

Reboot:

    sudo reboot

### 3.4 Verify Camera

After reboot, SSH back in and run:

    libcamera-hello --list-cameras

Expected output will show something like:
    Available cameras
    -----------------
    0 : imx477 [4056x3040]

If no camera is listed, check the ribbon cable connection and config.txt.

Take a test still to confirm the camera produces an image:

    libcamera-jpeg -o test.jpg --width 1920 --height 1080

Transfer test.jpg to your computer to verify image quality:
    (from your computer): scp pi@caliper.local:~/test.jpg .

---

## PART 4 — WIFI ACCESS POINT SETUP

The Pi will broadcast its own WiFi network named CaliperNet. Any device
connecting to that network can access the web UI at http://10.0.0.1:5000.
No internet router is needed in the field.

### 4.1 Install AP Software

    sudo apt update
    sudo apt install -y hostapd dnsmasq

### 4.2 Configure a Static IP for the AP Interface

    sudo nano /etc/dhcpcd.conf

Add at the END of the file:

    interface wlan0
        static ip_address=10.0.0.1/24
        nohook wpa_supplicant

Save and exit (Ctrl+O, Enter, Ctrl+X).

### 4.3 Configure DHCP Server (dnsmasq)

Back up the original config:

    sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig

Create a new config:

    sudo nano /etc/dnsmasq.conf

Paste the following:

    interface=wlan0
    dhcp-range=10.0.0.10,10.0.0.50,255.255.255.0,24h
    domain=local
    address=/caliper.local/10.0.0.1

Save and exit.

### 4.4 Configure the Access Point (hostapd)

    sudo nano /etc/hostapd/hostapd.conf

Paste the following — replace YOUR_PASSWORD with your chosen WiFi password
(minimum 8 characters):

    interface=wlan0
    driver=nl80211
    ssid=CaliperNet
    hw_mode=g
    channel=7
    wmm_enabled=0
    macaddr_acl=0
    auth_algs=1
    ignore_broadcast_ssid=0
    wpa=2
    wpa_passphrase=YOUR_PASSWORD
    wpa_key_mgmt=WPA-PSK
    wpa_pairwise=TKIP
    rsn_pairwise=CCMP

Save and exit.

Tell hostapd where its config file is:

    sudo nano /etc/default/hostapd

Find the line:
    #DAEMON_CONF=""

Change it to:
    DAEMON_CONF="/etc/hostapd/hostapd.conf"

Save and exit.

### 4.5 Enable and Start AP Services

    sudo systemctl unmask hostapd
    sudo systemctl enable hostapd
    sudo systemctl enable dnsmasq
    sudo reboot

### 4.6 Verify the Access Point

After reboot, on a phone or laptop, look for the WiFi network "CaliperNet".
Connect using the password you set.

The Pi will no longer appear on your home network's WiFi (wlan0 is now the AP).
To SSH into the Pi while using CaliperNet:

    ssh pi@10.0.0.1

NOTE: If you need internet access on the Pi for installation steps, use a wired
Ethernet connection (eth0). The AP and Ethernet can run simultaneously.

---

## PART 5 — CALIPER SOFTWARE INSTALLATION

### 5.1 Copy Project Files

From your computer, copy the caliper project folder to the Pi:

    scp -r caliper/ pi@10.0.0.1:~/caliper/

Or if still on home network before AP is set up:

    scp -r caliper/ pi@caliper.local:~/caliper/

Alternatively, clone from your repo if you have one:

    git clone https://YOUR_REPO_URL ~/caliper

### 5.2 Run the Installer

    cd ~/caliper
    chmod +x install.sh
    bash install.sh

The installer will:
- Verify 64-bit OS
- Update system packages
- Install python3-picamera2, python3-opencv, libatlas-base-dev
- Install Flask, PaddleOCR, and PaddlePaddle via pip
- Create captures/ and plates/ directories
- Install and enable the caliper systemd service

NOTE: PaddleOCR installation downloads model weights (~200MB) on first run,
not during install. First startup will be slow (1–3 minutes) while models load.

### 5.3 Manual Installation (if install.sh fails)

Run each step manually:

    sudo apt update && sudo apt upgrade -y

    sudo apt install -y \
      python3-pip python3-opencv python3-picamera2 \
      libopencv-dev libatlas-base-dev libhdf5-dev \
      git sqlite3

    pip3 install --break-system-packages flask paddlepaddle paddleocr

    mkdir -p ~/caliper/captures ~/caliper/plates

### 5.4 Start the Service

    sudo systemctl start caliper

Check it is running:

    sudo systemctl status caliper

View live logs:

    journalctl -u caliper -f

Expected startup log output:
    ... Caliper Phase 1 starting...
    ... Camera started (1920, 1080) @ 10fps
    (First run only): downloading OCR models...

### 5.5 Access the Web UI

From any device connected to CaliperNet:

    Open browser → http://10.0.0.1:5000

From a device on the same LAN as the Pi (during development):

    Open browser → http://caliper.local:5000
    or
    Open browser → http://[PI_IP_ADDRESS]:5000

The web UI polls automatically:
- Latest plate: every 1.5 seconds
- Pool grid: every 3 seconds
- Stats: every 5 seconds

---

## PART 6 — SERVICE MANAGEMENT

### Start / Stop / Restart

    sudo systemctl start caliper
    sudo systemctl stop caliper
    sudo systemctl restart caliper

### Enable / Disable Autostart on Boot

    sudo systemctl enable caliper    # start on boot (already set by install.sh)
    sudo systemctl disable caliper   # don't start on boot

### View Logs

    journalctl -u caliper -f         # live tail
    journalctl -u caliper -n 100     # last 100 lines
    journalctl -u caliper --since "1 hour ago"

### Run Manually (for development/testing, stops on Ctrl+C)

    cd ~/caliper
    python3 caliper.py

---

## PART 7 — TUNING AND CONFIGURATION

All tunable parameters are in ~/caliper/config.py:

    CAMERA_RESOLUTION   Resolution for capture. (1920,1080) default.
                        Reduce to (1280,720) if OCR is too slow.

    CAMERA_FRAMERATE    Frames per second. 10 default.

    CAPTURE_INTERVAL_S  Seconds between OCR attempts. 0.5 default.
                        Increase if Pi is overloaded.

    MIN_CONFIDENCE      PaddleOCR minimum confidence to store a read.
                        0.7 default. Lower = more reads, more noise.
                        Raise to 0.85 for fewer false positives.

    PLATE_POOL_MAX      Maximum plates retained in SQLite pool. 500 default.

    CAPTURE_BUFFER_MAX  Maximum crop image files kept on disk. 50 default.

After editing config.py, restart the service:

    sudo systemctl restart caliper

---

## PART 8 — TROUBLESHOOTING

### Camera not detected
- Check ribbon cable orientation and seating
- Verify /boot/firmware/config.txt has: camera_auto_detect=1
- Run: libcamera-hello --list-cameras
- Try: sudo raspi-config → Interface Options → Camera

### OCR never produces results
- PaddleOCR may still be downloading models on first run — wait 2-3 min
- Check logs: journalctl -u caliper -f
- Try lowering MIN_CONFIDENCE in config.py to 0.5 temporarily
- Point camera at a printed license plate at close range to test

### Web UI not loading
- Confirm service is running: sudo systemctl status caliper
- Check the port isn't blocked: sudo ufw status (disable if needed)
- Confirm you are connected to CaliperNet (IP should be 10.0.0.x)
- Try: curl http://10.0.0.1:5000 from the Pi itself

### WiFi AP not appearing
- Check hostapd status: sudo systemctl status hostapd
- Check for config errors: sudo hostapd /etc/hostapd/hostapd.conf
- Confirm /etc/default/hostapd has DAEMON_CONF set correctly
- Some USB WiFi adapters don't support AP mode — Pi 4B onboard WiFi does

### PaddleOCR import error / install failure
- Confirm 64-bit OS: uname -m (should show aarch64)
- Try installing with: pip3 install paddlepaddle==2.5.2 paddleocr
- Check available disk space: df -h (needs ~2GB free for models)

### Pi overheating / throttling
- Check CPU temp: vcgencmd measure_temp
- Add a heatsink or small fan if temp exceeds 80°C
- Reduce CAMERA_FRAMERATE and increase CAPTURE_INTERVAL_S in config.py

---

## PART 9 — PHASE 2 PREVIEW (E-INK DISPLAY)

Phase 2 will add e-ink display output. When the 7.3" Waveshare HAT arrives:

1. Connect HAT to Pi GPIO header (all 40 pins)
2. Install Waveshare library:
       git clone https://github.com/waveshare/e-Paper ~/e-Paper
       pip3 install --break-system-packages Pillow RPi.GPIO spidev
3. Enable SPI interface:
       sudo raspi-config → Interface Options → SPI → Enable
4. Download FHWA Series font (free, public domain highway font):
       https://github.com/usdot-fhwa-stcvd/fhwa-fonts
5. Plate rendering will use Pillow to draw plate-formatted images
   and push them to the display via the Waveshare Python driver.

IR LED strip (850nm) will be mounted around the display perimeter and
controlled via PWM from a Pi GPIO pin through a logic-level MOSFET.
Brightness tuning via PWM duty cycle in software.

---

## APPENDIX A — USEFUL COMMANDS REFERENCE

    # System
    sudo reboot                          Reboot
    sudo shutdown -h now                 Shutdown
    df -h                                Disk usage
    free -h                              RAM usage
    vcgencmd measure_temp                CPU temperature
    uname -m                             Architecture (should be aarch64)

    # Camera
    libcamera-hello --list-cameras       List detected cameras
    libcamera-jpeg -o test.jpg           Capture test image
    libcamera-vid -t 5000 -o test.h264   Capture 5s test video

    # Service
    sudo systemctl start caliper         Start service
    sudo systemctl stop caliper          Stop service
    sudo systemctl restart caliper       Restart service
    sudo systemctl status caliper        Service status
    journalctl -u caliper -f             Live log tail

    # Database
    sqlite3 ~/caliper/plates/caliper.db  Open DB shell
    (in sqlite3): SELECT * FROM plates ORDER BY last_seen DESC LIMIT 20;
    (in sqlite3): SELECT COUNT(*) FROM plates;
    (in sqlite3): .quit

    # Network
    hostname -I                          Show all IP addresses
    iwconfig wlan0                       WiFi interface status
    sudo systemctl status hostapd        AP status
    sudo systemctl status dnsmasq        DHCP status

---

## APPENDIX B — SECURITY NOTES

- The web UI has no authentication. It is accessible to anyone on CaliperNet.
- Use a strong WiFi password for CaliperNet to limit access.
- The Pi SSH password should be strong and unique.
- Consider disabling SSH once the system is deployed and stable:
      sudo systemctl disable ssh
- The plate pool database contains no PII beyond plate strings and timestamps.

---

Document version: Phase 1.0
Hardware: Pi 4B · UC-A37 Rev B · 7.3" e-ink HAT (pending)
