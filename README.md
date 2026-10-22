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
`ADB shell` gives you the same view the platform tools would: `getprop`, `pm list packages`, `dumpsys`, `logcat`. To pull an APK for static analysis (jadx):
```
python -m toshiba_tv.cli --host 192.168.1.50 path com.amazon.tv.devicecontrol
python -m toshiba_tv.cli --host 192.168.1.50 pull /system/.../base.apk devicecontrol.apk
```

## Cloud-free control (no ADB)

These use standard LAN protocols the TV already speaks, so they work even with
ADB debugging off.

**DIAL** — launch/stop streaming apps by name over HTTP:
```
python -m toshiba_tv.cli --host 192.168.1.50 dial list
python -m toshiba_tv.cli --host 192.168.1.50 dial launch YouTube
python -m toshiba_tv.cli --host 192.168.1.50 dial stop YouTube
```

**Google Cast** — playback + volume (needs `pip install PyChromecast`):
```
python -m toshiba_tv.cli --host 192.168.1.50 cast status
python -m toshiba_tv.cli --host 192.168.1.50 cast vol 0.3
python -m toshiba_tv.cli --host 192.168.1.50 cast pause
```

**Matter** — cloud-free power / transport / navigation. Needs a Matter controller;
the simplest is [python-matter-server](https://github.com/home-assistant-libs/python-matter-server)
as a WebSocket service (`pip install websocket-client` for the client here):
```
# one-time: run the controller
docker run -d --name matter-server --network host -v matter-data:/data \
  ghcr.io/home-assistant-libs/python-matter-server:stable

# one-time: pair the TV (get the setup code on the TV:
#   Settings > Device & Software > enable Matter / "Add to Matter", it shows a code)
python -m toshiba_tv.cli matter commission MT:xxxxxxxxxxxx

# then control it (node id is printed by `commission` / `matter nodes`)
python -m toshiba_tv.cli matter off  --node 4
python -m toshiba_tv.cli matter on   --node 4
python -m toshiba_tv.cli matter key vol_up --node 4
python -m toshiba_tv.cli matter node --node 4     # dump endpoints/clusters
```

See [`docs/FINDINGS.md`](docs/FINDINGS.md) for the full reverse-engineering writeup
(ports, services, APK analysis) and [`docs/ir_emitter_directive.proto`](docs/ir_emitter_directive.proto)
for the reconstructed IR blaster directive format.

Scope: only run this against a TV you own, on a network you control.
