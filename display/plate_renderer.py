"""
plate_renderer.py  —  Caliper Phase 2 v1.4
Renders a US license plate string as a proportionally correct plate image
for the Waveshare 7.5" V2 e-ink display (800x480, B/W).

Design philosophy:
  The entire 800x480 canvas IS the plate. All measurements are proportional
  fractions of W and H, derived from real AAMVA plate ratios (12" x 6").
  An LPR camera will read this as a plate at a slightly greater distance —
  not a sticker or bumper graphic — because all internal proportions match.

Font: DejaVu Sans Condensed (Regular, no added stroke)
  Best available match to FHWA Series E Modified on Raspberry Pi OS.
  Calibrated so a 7-char plate fills ~72% of usable width at natural spacing.
  8-char plates drop one font size gracefully. No character compression ever.

Key proportions (all from AAMVA License Plate Standard, Edition 3):
  Outer border inset:   0.25/12 = 2.1% of W,  0.125/6 = 2.1% of H
  Inner border inset:   0.5/12  = 4.2% of W,  0.25/6  = 4.2% of H
  Bolt hole X:          2.5/12  = 20.8% from each side
  Bolt hole Y:          0.5/6   = 8.3% from plate top (from border)
  Char vertical center: upper 44% of inner area (leaves state area below)
  State area:           bottom 12.5% of display (reserved, not filled)
"""

import os
from PIL import Image, ImageDraw, ImageFont
import config as cfg

# ── Font ──────────────────────────────────────────────────────────────────────
_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"
_FONT_FALLBACKS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]

def _find_font() -> str:
    if os.path.exists(_FONT_PATH):
        return _FONT_PATH
    for p in _FONT_FALLBACKS:
        if os.path.exists(p):
            return p
    return None

# ── Fixed font sizes (calibrated, do not change without re-testing) ───────────
# FS_PRIMARY:   7-char plate fills ~72% of usable width — natural, uncrowded
# FS_SECONDARY: 8-char plate fallback — modest size reduction, no compression
FS_PRIMARY   = 139
FS_SECONDARY = 120


def render_plate(plate_text: str) -> Image.Image:
    """
    Render plate_text as a proportionally correct US license plate image.
    Returns an 800x480 RGB image (white background, black ink).

    plate_text : OCR-read plate string, e.g. "ABC1234" or "AB-1234"
                 Rendered exactly as supplied, uppercased.
                 State text is intentionally omitted — we cannot confirm
                 the state from OCR alone and a wrong state would break
                 LPR correlation matching.
    """
    W = cfg.EINK_WIDTH    # 800
    H = cfg.EINK_HEIGHT   # 480

    def pw(f): return round(f * W)
    def ph(f): return round(f * H)

    img  = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    text = plate_text.upper().strip()

    # ── Borders ───────────────────────────────────────────────────────────────
    # Outer border: 2.1% inset from each edge (AAMVA: 0.25" on 12" plate)
    bx, by = pw(0.021), ph(0.021)
    draw.rectangle([bx, by, W-bx, H-by], outline="black", width=4)

    # Inner border: 4.2% inset (AAMVA: 0.5/12 wide)
    ix, iy = pw(0.042), ph(0.042)
    draw.rectangle([ix, iy, W-ix, H-iy], outline="black", width=2)

    # ── Bolt holes ────────────────────────────────────────────────────────────
    # AAMVA Appendix E: 2.5" from sides = 20.8% of W
    # 0.5" from top/bottom of border = 8.3% of H
    bolt_y = ph(0.083)
    bolt_r = ph(0.040)    # ~19px radius — proportional to real ~3/8" hole
    for bolt_x in [pw(0.208), pw(1 - 0.208)]:
        draw.ellipse(
            [bolt_x - bolt_r, bolt_y - bolt_r,
             bolt_x + bolt_r, bolt_y + bolt_r],
            fill="white", outline="black", width=2
        )

    # ── Characters ────────────────────────────────────────────────────────────
    font_path = _find_font()
    if font_path is None:
        font      = ImageFont.load_default()
        fs        = 16
    else:
        aw   = pw(0.72)   # usable text width: 72% of display
        fs   = FS_PRIMARY
        font = ImageFont.truetype(font_path, fs)
        bb   = draw.textbbox((0, 0), text, font=font)
        tw   = bb[2] - bb[0]

        if tw > aw:
            # Drop to secondary size for long plates — no compression
            fs   = FS_SECONDARY
            font = ImageFont.truetype(font_path, fs)
            bb   = draw.textbbox((0, 0), text, font=font)
            tw   = bb[2] - bb[0]

            # Final safety: if still over (unusual), step down until it fits
            while tw > aw and fs > 60:
                fs   -= 4
                font  = ImageFont.truetype(font_path, fs)
                bb    = draw.textbbox((0, 0), text, font=font)
                tw    = bb[2] - bb[0]

    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]

    # Horizontal: center in full display width
    tx = round((W - tw) / 2 - bb[0])

    # Vertical: center in upper 44% of inner area
    # (lower portion reserved for state name zone)
    inner_top = iy
    inner_h   = H - 2 * iy
    ty = round(inner_top + inner_h * 0.44 - th / 2 - bb[1])

    draw.text((tx, ty), text, font=font, fill="black")

    return img
