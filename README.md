# toshiba_tv

Control and inspect a Toshiba Fire TV edition from Python. Run it from a machine on the same LAN as the TV, not from a cloud container.

## One-time TV setup
1. Settings → My Fire TV → About → click the device name 7 times to unlock Developer Options.
2. Settings → My Fire TV → Developer Options → turn on **ADB debugging**.
3. Find the IP: Settings → My Fire TV → About → Network.

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
