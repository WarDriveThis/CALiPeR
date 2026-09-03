#!/usr/bin/env python3
"""
Caliper - License Plate OCR Capture + E-ink Display Service
Phase 2 v1.5
"""

import os
import time
import threading
import queue
import logging
import datetime
import cv2
import numpy as np
from picamera2 import Picamera2
from paddleocr import PaddleOCR
from plates.db import init_db, upsert_plate, get_all_plates
import config as cfg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger("caliper")

# ── Shared state ──────────────────────────────────────────────────────────────
latest_frame  = None
latest_plate  = None
frame_lock    = threading.Lock()

live = {
    "exposure_locked":  False,
    "min_confidence":   cfg.MIN_CONFIDENCE,
    "capture_interval": cfg.CAPTURE_INTERVAL_S,
    "shutter_speed_us": cfg.SHUTTER_SPEED_US,
    "ocr_downscale":    cfg.OCR_DOWNSCALE_WIDTH,
    "clahe_enabled":    cfg.CLAHE_ENABLED,
    "eink_enabled":     cfg.EINK_ENABLED,
    "eink_cycle_secs":  cfg.EINK_CYCLE_SECONDS,
    "plate_max_age":    cfg.PLATE_MAX_AGE_SECONDS,
}
live_lock = threading.Lock()

frame_queue = queue.Queue(maxsize=2)

# Event that the UI can set to trigger an immediate display refresh
display_refresh_event = threading.Event()

# ── OCR engine ────────────────────────────────────────────────────────────────
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    use_gpu=False,
    show_log=False,
    det_db_thresh=0.3,
    det_db_box_thresh=0.5,
    rec_batch_num=1,
    max_text_length=8,
)

_clahe = cv2.createCLAHE(
    clipLimit=cfg.CLAHE_CLIP_LIMIT,
    tileGridSize=(cfg.CLAHE_TILE_SIZE, cfg.CLAHE_TILE_SIZE)
)

# ── E-ink driver (lazy init inside display_loop) ──────────────────────────────
_eink = None


def _get_eink():
    global _eink
    if _eink is None:
        from display.eink_driver import EinkDriver
        _eink = EinkDriver()
        _eink.init()
    return _eink


# ── Preprocessing ─────────────────────────────────────────────────────────────
def preprocess_for_ocr(frame):
    with live_lock:
        downscale_w = live["ocr_downscale"]
        clahe_on    = live["clahe_enabled"]

    orig_w = frame.shape[1]
    scale  = 1.0

    if downscale_w > 0 and orig_w > downscale_w:
        scale  = downscale_w / orig_w
        new_h  = int(frame.shape[0] * scale)
        frame  = cv2.resize(frame, (downscale_w, new_h),
                            interpolation=cv2.INTER_AREA)

    if clahe_on:
        channels = cv2.split(frame)
        frame    = cv2.merge([_clahe.apply(c) for c in channels])

    return frame, scale


def is_valid_plate(text):
    import re
    t = text.strip().upper().replace(" ", "").replace("-", "")
    if len(t) < 2 or len(t) > 8:
        return False
    return bool(re.match(r'^[A-Z0-9]+$', t))


def prune_captures():
    try:
        files = sorted(
            [os.path.join(cfg.CAPTURES_PATH, f)
             for f in os.listdir(cfg.CAPTURES_PATH)],
            key=os.path.getmtime
        )
        while len(files) > cfg.CAPTURE_BUFFER_MAX:
            os.remove(files.pop(0))
    except Exception as e:
        log.warning(f"Prune error: {e}")


def save_crop(frame, bbox, filename):
    try:
        pts  = np.array(bbox, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(pts)
        pad  = 10
        x    = max(0, x - pad)
        y    = max(0, y - pad)
        w    = min(frame.shape[1] - x, w + 2 * pad)
        h    = min(frame.shape[0] - y, h + 2 * pad)
        crop = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_RGB2BGR)
        cv2.imwrite(os.path.join(cfg.CAPTURES_PATH, filename), crop)
        prune_captures()
        return filename
    except Exception as e:
        log.warning(f"Crop save failed: {e}")
        return None


# ── OCR thread ────────────────────────────────────────────────────────────────
def process_frame(frame):
    global latest_plate

    with live_lock:
        min_conf = live["min_confidence"]

    original = frame.copy()
    processed, scale = preprocess_for_ocr(frame)

    try:
        results = ocr.ocr(processed, cls=True)
    except Exception as e:
        log.warning(f"OCR error: {e}")
        return

    if not results or not results[0]:
        return

    for line in results[0]:
        bbox, (text, confidence) = line
        text_clean = text.strip().upper().replace(" ", "")

        if confidence < min_conf:
            continue
        if not is_valid_plate(text_clean):
            continue

        log.info(f"Plate: {text_clean}  conf={confidence:.2f}")

        scaled_bbox = ([[int(p[0]/scale), int(p[1]/scale)] for p in bbox]
                       if scale != 1.0 else bbox)

        ts         = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_file = f"{text_clean}_{ts}.jpg"
        save_crop(original, scaled_bbox, image_file)
        upsert_plate(text_clean, float(confidence), image_file)

        with frame_lock:
            latest_plate = {
                "text":       text_clean,
                "confidence": confidence,
                "image":      image_file
            }


def ocr_loop():
    log.info("OCR thread started.")
    while True:
        try:
            frame = frame_queue.get(timeout=5)
            process_frame(frame)
        except queue.Empty:
            continue
        except Exception as e:
            log.error(f"OCR loop error: {e}")


# ── Camera thread ─────────────────────────────────────────────────────────────
def camera_loop():
    global latest_frame

    with live_lock:
        shutter = live["shutter_speed_us"]

    controls = {"FrameRate": cfg.CAMERA_FRAMERATE}
    if shutter > 0:
        controls["ExposureTime"] = shutter

    cam = Picamera2()
    cam_cfg = cam.create_preview_configuration(
        main={"size": cfg.CAMERA_RESOLUTION, "format": "RGB888"},
        controls=controls
    )
    cam.configure(cam_cfg)
    cam.start()
    log.info(f"Camera started {cfg.CAMERA_RESOLUTION} @ {cfg.CAMERA_FRAMERATE}fps")

    log.info(f"Waiting {cfg.EXPOSURE_LOCK_DELAY_S}s for AE/AWB convergence...")
    time.sleep(cfg.EXPOSURE_LOCK_DELAY_S)
    log.info("AE/AWB ready.")

    _cam_locked = False

    try:
        while True:
            frame = cam.capture_array()
            with frame_lock:
                latest_frame = frame.copy()

            with live_lock:
                want_locked = live["exposure_locked"]
                interval    = live["capture_interval"]

            if want_locked and not _cam_locked:
                try:
                    meta = cam.capture_metadata()
                    cam.set_controls({
                        "AeEnable":     False,
                        "AwbEnable":    False,
                        "ExposureTime": meta["ExposureTime"],
                        "AnalogueGain": meta["AnalogueGain"],
                        "ColourGains":  meta.get("ColourGains", (1.5, 1.5)),
                    })
                    _cam_locked = True
                    log.info(f"Exposure LOCKED: "
                             f"exp={meta['ExposureTime']}us "
                             f"gain={meta['AnalogueGain']:.2f}")
                except Exception as e:
                    log.warning(f"Lock failed: {e}")

            elif not want_locked and _cam_locked:
                cam.set_controls({"AeEnable": True, "AwbEnable": True})
                _cam_locked = False
                log.info("Exposure UNLOCKED.")

            try:
                frame_queue.put_nowait(frame)
            except queue.Full:
                pass

            time.sleep(interval)

    except KeyboardInterrupt:
        log.info("Camera loop stopping.")
    finally:
        cam.stop()
        log.info("Camera stopped.")


# ── Display thread ────────────────────────────────────────────────────────────

def expiry_loop():
    """
    Periodically removes plates from the pool whose last_seen timestamp
    is older than PLATE_MAX_AGE_SECONDS. Runs independently of OCR and display.
    Disabled if PLATE_MAX_AGE_SECONDS == 0.
    """
    from plates.db import expire_plates
    if cfg.PLATE_MAX_AGE_SECONDS <= 0:
        log.info("Plate expiry disabled (PLATE_MAX_AGE_SECONDS=0).")
        return
    log.info(f"Expiry thread started — max age {cfg.PLATE_MAX_AGE_SECONDS}s, "
             f"check every {cfg.PLATE_EXPIRY_INTERVAL_S}s.")
    while True:
        time.sleep(cfg.PLATE_EXPIRY_INTERVAL_S)
        try:
            # Read max_age from live dict so UI changes take effect immediately
            with live_lock:
                max_age = live.get("plate_max_age", cfg.PLATE_MAX_AGE_SECONDS)
            if max_age <= 0:
                continue
            removed = expire_plates(max_age)
            if removed:
                log.info(f"Expiry: removed {removed} aged plate(s).")
        except Exception as e:
            log.error(f"Expiry loop error: {e}")


def display_loop():
    """
    Randomly cycles through the plate pool and renders each plate to the
    e-ink display, independent of OCR activity.

    Design:
    - Takes a snapshot of the pool at the start of each cycle.
    - Shuffles the snapshot randomly — new OCR reads do not interrupt the
      current shuffle order. They appear in the NEXT shuffle after the
      current pass completes.
    - Each plate is shown for EINK_CYCLE_SECONDS (live-adjustable).
    - Runs expiry-aware: if the pool shrinks mid-shuffle, missing plates
      are skipped silently.
    - Full refresh every EINK_FULL_REFRESH_EVERY plate changes to clear ghosting.
    """
    import random
    from display.plate_renderer import render_plate

    log.info("Display thread started.")

    if not cfg.EINK_ENABLED:
        log.info("E-ink disabled in config — display thread idle.")
        # Still run loop so live toggle can enable it later
        while True:
            with live_lock:
                if live["eink_enabled"]:
                    break
            time.sleep(2)

    eink = _get_eink()
    if not eink._initialised:
        log.error("E-ink failed to initialise — display thread exiting.")
        return

    shuffle = []      # current shuffled snapshot of plate texts
    shown   = set()   # plates shown in current shuffle pass

    while True:
        try:
            with live_lock:
                enabled    = live["eink_enabled"]
                cycle_secs = live["eink_cycle_secs"]

            if not enabled:
                time.sleep(2)
                continue

            # Build / rebuild shuffle when exhausted or empty
            if not shuffle:
                from plates.db import get_plate_texts
                pool = get_plate_texts()
                if not pool:
                    time.sleep(cfg.EINK_POLL_INTERVAL_S)
                    continue
                shuffle = pool[:]
                random.shuffle(shuffle)
                shown   = set()
                log.info(f"Display: new shuffle — {len(shuffle)} plates.")

            # Pick next plate from shuffle
            plate_text = shuffle.pop(0)
            shown.add(plate_text)

            log.info(f"Display: rendering {plate_text} "
                     f"({len(shown)}/{len(shown)+len(shuffle)} in pass)")
            img = render_plate(plate_text)
            eink.display(img)

            # Hold the plate on screen for cycle_secs,
            # checking live settings every second so changes feel responsive.
            # display_refresh_event breaks out immediately for a UI-triggered refresh.
            elapsed = 0.0
            while elapsed < cycle_secs:
                if display_refresh_event.wait(timeout=1.0):
                    display_refresh_event.clear()
                    log.info("Display: refresh triggered by UI.")
                    break
                elapsed += 1.0
                with live_lock:
                    cycle_secs = live["eink_cycle_secs"]
                    enabled    = live["eink_enabled"]
                if not enabled:
                    break

        except Exception as e:
            log.error(f"Display loop error: {e}")
            time.sleep(cfg.EINK_POLL_INTERVAL_S)


if __name__ == "__main__":
    os.makedirs(cfg.CAPTURES_PATH, exist_ok=True)
    os.makedirs("plates", exist_ok=True)
    init_db()
    log.info("Caliper v1.4 starting...")

    threading.Thread(target=ocr_loop,     daemon=True).start()
    threading.Thread(target=camera_loop,  daemon=True).start()
    threading.Thread(target=display_loop, daemon=True).start()
    threading.Thread(target=expiry_loop,  daemon=True).start()

    from web.app import app
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
