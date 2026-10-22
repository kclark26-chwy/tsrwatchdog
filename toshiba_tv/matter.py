"""Matter control for the Fire TV (cloud-free power / transport / navigation).

The TV runs `com.amazon.tv.mattercohost` (a Matter "Casting Video Player"), so it
can be commissioned onto a Matter fabric and driven locally with no Amazon cloud
and no ADB.

Matter needs a real controller (the CHIP stack). Rather than vendor that here, this
module is a thin synchronous client for **python-matter-server**, which wraps the
official SDK behind a WebSocket. Run it once via Docker:

    docker run -d --name matter-server --network host \
      -v matter-data:/data \
      ghcr.io/home-assistant-libs/python-matter-server:stable

Then from this module:

    from toshiba_tv.matter import MatterServer
    m = MatterServer("ws://127.0.0.1:5580/ws")
    node = m.commission("MT:...setup-code-from-TV...")   # one-time pairing
    m.power_off(node); m.power_on(node)

Dependency: `pip install websocket-client`.

Cluster/command IDs are the Matter spec defaults. A Casting Video Player exposes its
app-platform clusters on endpoint 1; power (On/Off) is usually there too. Use
`nodes()` / `endpoints()` to confirm for your unit, and `device_command()` for
anything these wrappers don't cover.
"""
import itertools
import json

# Matter cluster IDs
ON_OFF = 0x0006
LEVEL_CONTROL = 0x0008
MEDIA_PLAYBACK = 0x0506   # 1286
KEYPAD_INPUT = 0x0509     # 1289
CONTENT_LAUNCHER = 0x050A  # 1290
APPLICATION_LAUNCHER = 0x050C  # 1292

# KeypadInput SendKey CEC key codes (subset)
KEYS = {
    "select": 0x00, "up": 0x01, "down": 0x02, "left": 0x03, "right": 0x04,
    "back": 0x0D, "exit": 0x0D, "home": 0x09, "menu": 0x0A,
    "vol_up": 0x41, "vol_down": 0x42, "mute": 0x43,
    "play": 0x44, "stop": 0x45, "pause": 0x46, "rewind": 0x48, "ff": 0x49,
    "channel_up": 0x30, "channel_down": 0x31,
}


def _ws():
    try:
        import websocket  # websocket-client
    except ImportError as e:
        raise RuntimeError("pip install websocket-client to use the matter module") from e
    return websocket


class MatterServer:
    def __init__(self, url="ws://127.0.0.1:5580/ws", timeout=30.0):
        websocket = _ws()
        self.ws = websocket.create_connection(url, timeout=timeout)
        self._ids = (str(i) for i in itertools.count(1))
        # First frame is the server-info message; keep it for reference.
        self.server_info = json.loads(self.ws.recv())

    def _cmd(self, command, **args):
        """Send a command and block until its matching response arrives.

        Unrelated event frames (node_added, attribute updates, ...) are skipped.
        """
        mid = next(self._ids)
        self.ws.send(json.dumps({"message_id": mid, "command": command, "args": args}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("message_id") != mid:
                continue  # an event or another command's reply
            if "error_code" in msg:
                raise RuntimeError(f"{command} failed: {msg.get('error_code')} {msg.get('details', '')}")
            return msg.get("result")

    # --- discovery / commissioning ---
    def commission(self, setup_code, network_only=True):
        """Pair the TV using the setup code it shows on screen. Returns its node_id."""
        node = self._cmd("commission_with_code", code=setup_code, network_only=network_only)
        return node["node_id"] if isinstance(node, dict) else node

    def nodes(self):
        """List commissioned nodes (id + basic info)."""
        return self._cmd("get_nodes")

    def endpoints(self, node_id):
        """Return the node's full attribute tree (endpoints, clusters, attributes)."""
        return self._cmd("get_node", node_id=node_id)

    # --- generic escape hatch ---
    def device_command(self, node_id, cluster_id, command_name, endpoint_id=1, **payload):
        return self._cmd(
            "device_command",
            node_id=node_id, endpoint_id=endpoint_id,
            cluster_id=cluster_id, command_name=command_name, payload=payload,
        )

    # --- power (On/Off cluster) ---
    def power_on(self, node_id, endpoint_id=1):
        return self.device_command(node_id, ON_OFF, "On", endpoint_id)

    def power_off(self, node_id, endpoint_id=1):
        return self.device_command(node_id, ON_OFF, "Off", endpoint_id)

    def power_toggle(self, node_id, endpoint_id=1):
        return self.device_command(node_id, ON_OFF, "Toggle", endpoint_id)

    # --- transport (Media Playback cluster) ---
    def play(self, node_id, endpoint_id=1):
        return self.device_command(node_id, MEDIA_PLAYBACK, "Play", endpoint_id)

    def pause(self, node_id, endpoint_id=1):
        return self.device_command(node_id, MEDIA_PLAYBACK, "Pause", endpoint_id)

    def stop(self, node_id, endpoint_id=1):
        return self.device_command(node_id, MEDIA_PLAYBACK, "Stop", endpoint_id)

    # --- navigation / volume (Keypad Input cluster) ---
    def key(self, node_id, name, endpoint_id=1):
        """Send a remote key by name (see KEYS), incl. vol_up/vol_down/mute."""
        code = KEYS.get(name, name)
        return self.device_command(node_id, KEYPAD_INPUT, "SendKey", endpoint_id, keyCode=code)

    # --- app launch (Application Launcher cluster) ---
    def launch_app(self, node_id, catalog_vendor_id, application_id, endpoint_id=1):
        return self.device_command(
            node_id, APPLICATION_LAUNCHER, "LaunchApp", endpoint_id,
            application={"catalogVendorID": catalog_vendor_id, "applicationID": application_id},
        )

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
