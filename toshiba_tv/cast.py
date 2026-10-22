"""Google Cast control for the Fire TV (playback + volume), via pychromecast.

The Fire TV runs FireTVDefaultMediaReceiver on tcp/8009, so it behaves as a Cast
receiver. This needs no ADB. pychromecast is an optional dependency:
    pip install PyChromecast
"""


def _require():
    try:
        import pychromecast  # noqa: F401
    except ImportError as e:
        raise RuntimeError("pip install PyChromecast to use the cast module") from e
    return __import__("pychromecast")


class Cast:
    def __init__(self, cc):
        self._cc = cc
        self.mc = cc.media_controller

    @classmethod
    def connect(cls, host, timeout=10.0):
        """Connect to the TV's Cast receiver by IP."""
        pychromecast = _require()
        cc = pychromecast.Chromecast(host, timeout=timeout)
        cc.wait(timeout=timeout)
        return cls(cc)

    @classmethod
    def discover(cls, timeout=6.0):
        """Return (friendly_name, host) for every Cast receiver on the LAN."""
        pychromecast = _require()
        casts, browser = pychromecast.get_chromecasts(timeout=timeout)
        browser.stop_discovery()
        return [(c.cast_info.friendly_name, c.cast_info.host) for c in casts]

    # --- status ---
    def status(self):
        s = self._cc.status
        return {
            "display_name": s.display_name,
            "app_id": s.app_id,
            "volume_level": round(s.volume_level, 3),
            "volume_muted": s.volume_muted,
            "is_active_input": s.is_active_input,
        }

    # --- volume ---
    def set_volume(self, level):       # 0.0 - 1.0
        self._cc.set_volume(max(0.0, min(1.0, level)))

    def volume_up(self, step=0.1):
        self._cc.volume_up(step)

    def volume_down(self, step=0.1):
        self._cc.volume_down(step)

    def mute(self, on=True):
        self._cc.set_volume_muted(on)

    # --- playback ---
    def play(self):
        self.mc.play()

    def pause(self):
        self.mc.pause()

    def stop(self):
        self.mc.stop()

    def seek(self, seconds):
        self.mc.seek(seconds)

    def play_url(self, url, content_type="video/mp4", title=None):
        """Cast a media URL straight to the default receiver."""
        self.mc.play_media(url, content_type, title=title)
        self.mc.block_until_active()

    def quit(self):
        """Return the receiver to its home screen."""
        self._cc.quit_app()
