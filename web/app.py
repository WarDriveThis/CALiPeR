from flask import Flask, render_template, jsonify, send_from_directory, request
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from plates.db import (get_all_plates, get_latest_plate, get_stats,
                       clear_pool, delete_plate, add_plate)
import config as cfg

app = Flask(__name__)
_captures_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), cfg.CAPTURES_PATH)

# Signal flag: set True when UI requests a display refresh
_display_refresh_flag = False
_display_refresh_lock = None   # injected by caliper.py at startup


def _live():
    import caliper
    return caliper.live, caliper.live_lock


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/plates")
def api_plates():
    return jsonify(get_all_plates())

@app.route("/api/latest")
def api_latest():
    return jsonify(get_latest_plate())

@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())

@app.route("/api/clear", methods=["POST"])
def api_clear():
    clear_pool()
    return jsonify({"status": "ok"})

@app.route("/api/plate/delete", methods=["POST"])
def api_delete_plate():
    """Delete a single plate by plate_text."""
    data = request.get_json(silent=True) or {}
    plate_text = data.get("plate_text", "").strip()
    if not plate_text:
        return jsonify({"status": "error", "message": "plate_text required"}), 400
    delete_plate(plate_text)
    return jsonify({"status": "ok", "deleted": plate_text})

@app.route("/api/plate/add", methods=["POST"])
def api_add_plate():
    """Manually add a plate string to the pool."""
    data = request.get_json(silent=True) or {}
    plate_text = data.get("plate_text", "").strip().upper()
    if not plate_text:
        return jsonify({"status": "error", "message": "plate_text required"}), 400
    ok = add_plate(plate_text, confidence=1.0)
    return jsonify({"status": "ok" if ok else "error", "plate_text": plate_text})

@app.route("/api/display/refresh", methods=["POST"])
def api_display_refresh():
    """Signal the display thread to pick a new plate immediately."""
    import caliper
    try:
        caliper.display_refresh_event.set()
        return jsonify({"status": "ok"})
    except AttributeError:
        return jsonify({"status": "ok", "note": "display not running"})

@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    live, lock = _live()
    with lock:
        return jsonify(dict(live))

@app.route("/api/settings", methods=["POST"])
def api_settings_post():
    live, lock = _live()
    data = request.get_json(silent=True) or {}
    allowed = {
        "exposure_locked":  bool,
        "min_confidence":   float,
        "capture_interval": float,
        "shutter_speed_us": int,
        "ocr_downscale":    int,
        "clahe_enabled":    bool,
        "eink_enabled":     bool,
        "eink_cycle_secs":  float,
        "plate_max_age":    int,
    }
    import logging
    with lock:
        for key, cast in allowed.items():
            if key in data:
                try:
                    live[key] = cast(data[key])
                    logging.getLogger("caliper").info(f"Setting: {key} = {live[key]}")
                except (ValueError, TypeError):
                    pass
        return jsonify(dict(live))

@app.route("/captures/<filename>")
def capture_image(filename):
    return send_from_directory(_captures_dir, filename)
