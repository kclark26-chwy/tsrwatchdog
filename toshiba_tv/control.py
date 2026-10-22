"""Fire TV control over ADB (TCP) using adb-shell. First connect shows an on-TV auth prompt."""
import os
import re

from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_cryptography import CryptographySigner

KEYFILE = os.path.expanduser("~/.android/toshiba_tv_adbkey")

KEYS = {
    "home": 3, "back": 4, "up": 19, "down": 20, "left": 21, "right": 22,
    "ok": 23, "menu": 82, "play_pause": 85, "play": 126, "pause": 127,
    "next": 87, "prev": 88, "ff": 90, "rew": 89, "vol_up": 24, "vol_down": 25,
    "mute": 164, "power": 26, "sleep": 223, "wakeup": 224, "search": 84,
}


def _signer():
    if not os.path.exists(KEYFILE):
        os.makedirs(os.path.dirname(KEYFILE), exist_ok=True)
        keygen(KEYFILE)
    return CryptographySigner(KEYFILE)


class FireTV:
    def __init__(self, host, port=5555):
        self.dev = AdbDeviceTcp(host, port, default_transport_timeout_s=9.0)

    def connect(self, auth_timeout=30.0):
        return self.dev.connect(rsa_keys=[_signer()], auth_timeout_s=auth_timeout)

    def shell(self, cmd):
        return self.dev.shell(cmd)

    def key(self, name):
        self.shell(f"input keyevent {KEYS.get(name, name)}")

    def text(self, s):
        self.shell("input text " + s.replace(" ", "%s"))

    def launch(self, package):
        self.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")

    def open_url(self, url):
        self.shell(f"am start -a android.intent.action.VIEW -d '{url}'")

    def stop(self, package):
        self.shell(f"am force-stop {package}")

    def packages(self, third_party=False):
        out = self.shell("pm list packages" + (" -3" if third_party else ""))
        return sorted(l.split(":", 1)[1] for l in out.splitlines() if ":" in l)

    def info(self):
        props = ("ro.product.manufacturer", "ro.product.model", "ro.build.version.release",
                 "ro.build.fingerprint", "ro.build.version.security_patch", "ro.serialno")
        return {p: self.shell(f"getprop {p}").strip() for p in props}

    def current_app(self):
        out = self.shell("dumpsys window windows | grep mCurrentFocus")
        m = re.search(r"(\S+)/(\S+)\}", out)
        return m.group(1) if m else out.strip()

    def screenshot(self, path):
        data = self.dev.exec_out("screencap -p")
        with open(path, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("latin1"))

    def apk_path(self, package):
        """Resolve the on-device APK path(s) for a package (for pulling)."""
        out = self.shell(f"pm path {package}")
        return "\n".join(l.split(":", 1)[1] for l in out.splitlines() if ":" in l)

    def pull(self, remote, local):
        self.dev.pull(remote, local)

    def push(self, local, remote):
        self.dev.push(local, remote)
