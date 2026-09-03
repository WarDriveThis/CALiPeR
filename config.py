# Caliper — Configuration v1.5

# ── Camera ────────────────────────────────────────────────────────────────────
CAMERA_RESOLUTION       = (1920, 1080)
CAMERA_FRAMERATE        = 10
SHUTTER_SPEED_US        = 0
EXPOSURE_LOCK_DELAY_S   = 2.0

# ── OCR pipeline ──────────────────────────────────────────────────────────────
CAPTURE_INTERVAL_S      = 1.5      # min 0.25 — OCR inference takes ~1-2s so
                                   # values below that just drop frames, no risk
MIN_CONFIDENCE          = 0.70
OCR_DOWNSCALE_WIDTH     = 1600
CLAHE_ENABLED           = False
CLAHE_CLIP_LIMIT        = 2.0
CLAHE_TILE_SIZE         = 8

# ── Storage ───────────────────────────────────────────────────────────────────
PLATE_POOL_MAX          = 500
CAPTURE_BUFFER_MAX      = 50
DB_PATH                 = "plates/caliper.db"
CAPTURES_PATH           = "captures"

# ── Web UI ────────────────────────────────────────────────────────────────────
WEB_HOST                = "0.0.0.0"
WEB_PORT                = 5000

# ── E-ink display (Phase 2) ───────────────────────────────────────────────────
# Set to True to enable the e-ink display thread.
# Set to False to run without display (e.g. if display not connected).
EINK_ENABLED            = True

# Display dimensions — Waveshare 7.5" V2
EINK_WIDTH              = 800
EINK_HEIGHT             = 480

# How often to check the pool for a new plate to display (seconds).
EINK_POLL_INTERVAL_S    = 2.0

# Number of fast refreshes before forcing a full refresh to clear ghosting.
# Fast refresh: ~1-2s.  Full refresh: ~3-4s.
EINK_FULL_REFRESH_EVERY = 10

# Path to the Waveshare library — cloned to ~/e-Paper
EINK_LIB_PATH           = "/home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib"

# Plate rendering
# Margin around the plate image (pixels)
EINK_MARGIN             = 20

# How many seconds a plate stays on screen before cycling to the next pool entry.
EINK_CYCLE_SECONDS      = 8

# Plate pool aging — plates not seen within this window are expired from the pool.
# Set to 0 to disable expiry (plates stay until manually cleared or pool max hit).
# Default: 3600 seconds (1 hour).
PLATE_MAX_AGE_SECONDS   = 3600

# How often to run the expiry check (seconds).
PLATE_EXPIRY_INTERVAL_S = 60
