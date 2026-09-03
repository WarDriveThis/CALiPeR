"""
eink_driver.py  —  Caliper Phase 2
Waveshare 7.5" V2 display driver wrapper.
Handles init, fast vs full refresh cycling, sleep, and graceful cleanup.
"""

import sys
import os
import logging
import threading
from PIL import Image
import config as cfg

log = logging.getLogger("caliper.eink")


class EinkDriver:
    """
    Wraps the Waveshare epd7in5_V2 driver.
    Call display(image) to push a new plate image.
    Automatically cycles between fast and full refresh.
    Thread-safe — all display operations are serialised by an internal lock.
    """

    def __init__(self):
        self._lock         = threading.Lock()
        self._refresh_count = 0
        self._epd          = None
        self._initialised  = False
        self._sleeping     = False

    def init(self):
        """Import Waveshare lib and initialise the display."""
        lib_path = cfg.EINK_LIB_PATH
        if lib_path not in sys.path:
            sys.path.insert(0, lib_path)

        try:
            from waveshare_epd import epd7in5_V2
            self._epd = epd7in5_V2.EPD()
            log.info(f"E-ink: {cfg.EINK_WIDTH}x{cfg.EINK_HEIGHT} "
                     f"fast-refresh every {cfg.EINK_FULL_REFRESH_EVERY} frames")
            # Full init on startup — clears any residual image
            self._epd.init()
            self._epd.Clear()
            self._initialised = True
            self._sleeping    = False
            log.info("E-ink initialised and cleared.")
        except Exception as e:
            log.error(f"E-ink init failed: {e}")
            self._initialised = False

    def display(self, image: Image.Image):
        """
        Push image to the display.
        Uses fast refresh (init_fast) for most updates; falls back to full
        refresh every EINK_FULL_REFRESH_EVERY calls to clear ghosting.
        """
        if not self._initialised or self._epd is None:
            return

        with self._lock:
            try:
                # Wake from sleep if needed
                if self._sleeping:
                    log.debug("E-ink waking from sleep.")
                    self._epd.init()
                    self._sleeping = False

                self._refresh_count += 1
                use_fast = (self._refresh_count % cfg.EINK_FULL_REFRESH_EVERY != 0)

                # Convert to 1-bit buffer expected by driver
                buf = self._epd.getbuffer(image.convert("1"))

                if use_fast:
                    log.debug(f"E-ink fast refresh #{self._refresh_count}")
                    self._epd.init_fast()
                    self._epd.display(buf)
                else:
                    log.info(f"E-ink full refresh (#{self._refresh_count}, ghosting clear)")
                    self._epd.init()
                    self._epd.display(buf)

            except Exception as e:
                log.error(f"E-ink display error: {e}")

    def clear(self):
        """Clear display to white."""
        if not self._initialised or self._epd is None:
            return
        with self._lock:
            try:
                self._epd.init()
                self._epd.Clear()
                log.info("E-ink cleared.")
            except Exception as e:
                log.error(f"E-ink clear error: {e}")

    def sleep(self):
        """Put display into low-power sleep mode."""
        if not self._initialised or self._epd is None:
            return
        with self._lock:
            try:
                self._epd.sleep()
                self._sleeping = True
                log.info("E-ink sleeping.")
            except Exception as e:
                log.error(f"E-ink sleep error: {e}")

    def shutdown(self):
        """Clean shutdown — clear and sleep."""
        if not self._initialised:
            return
        log.info("E-ink shutdown.")
        self.clear()
        self.sleep()
        try:
            from waveshare_epd import epdconfig
            epdconfig.module_exit(cleanup=True)
        except Exception:
            pass
