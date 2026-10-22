# toshiba_tv

Control and inspect a Toshiba Fire TV edition from Python. Run it from a machine on the same LAN as the TV, not from a cloud container.

## One-time TV setup
1. Settings → **Device & Software** → **About** → press OK on the model name 7 times until it says "You are now a developer".
2. Back in **Device & Software** → **Developer Options** (now visible) → turn on **ADB Debugging**.
3. Find the IP: **Device & Software** → **About** → **Network**.

(Older Fire OS builds put the same items under "My Fire TV" instead of "Device & Software".)

## Use
```
pip install -r requirements.txt
python -m toshiba_tv.cli discover                 # SSDP + port probe
python -m toshiba_tv.cli --host 192.168.1.50 info # accept the on-TV "Allow USB debugging?" prompt (tick "always")
python -m toshiba_tv.cli --host 192.168.1.50 key home
python -m toshiba_tv.cli --host 192.168.1.50 apps -3
python -m toshiba_tv.cli --host 192.168.1.50 launch com.netflix.ninja
python -m toshiba_tv.cli --host 192.168.1.50 shell "dumpsys package | head"
python -m toshiba_tv.cli --host 192.168.1.50 shot out.png
```
`ADB shell` gives you the same view the platform tools would: `getprop`, `pm list packages`, `dumpsys`, `logcat`, and `pull` for APKs under `/system/app` and `/data/app` (for static analysis with jadx).

Scope: only run this against a TV you own, on a network you control.
