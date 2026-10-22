"""CLI for the Toshiba Fire TV toolkit.

ADB commands (need --host and ADB debugging on):
  info apps app key text launch url shell shot path pull
No-ADB commands (standard LAN protocols):
  discover           SSDP + port probe
  dial  ...          DIAL: list/launch/stop streaming apps over HTTP
"""
import argparse
import json
import sys

from . import discover
from .control import FireTV, KEYS


def main(argv=None):
    ap = argparse.ArgumentParser(prog="toshiba_tv")
    ap.add_argument("--host", help="TV IP address")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover")
    sub.add_parser("info")
    sub.add_parser("apps").add_argument("-3", dest="third", action="store_true")
    sub.add_parser("app")
    k = sub.add_parser("key"); k.add_argument("name", help=f"one of {', '.join(KEYS)} or a raw keycode")
    sub.add_parser("text").add_argument("text")
    sub.add_parser("launch").add_argument("package")
    sub.add_parser("url").add_argument("url")
    sub.add_parser("shell").add_argument("command", nargs="+")
    sub.add_parser("shot").add_argument("path")
    sub.add_parser("path").add_argument("package")
    p = sub.add_parser("pull"); p.add_argument("remote"); p.add_argument("local")

    d = sub.add_parser("dial"); d.add_argument("action", choices=["list", "launch", "stop", "status"])
    d.add_argument("app", nargs="?")
    m = sub.add_parser("matter")
    m.add_argument("action", choices=["commission", "nodes", "node", "on", "off", "toggle", "play", "pause", "stop", "key"])
    m.add_argument("value", nargs="?", help="setup code for `commission`, key name for `key`")
    m.add_argument("--server", default="ws://127.0.0.1:5580/ws", help="python-matter-server WS URL")
    m.add_argument("--node", type=int, help="commissioned node id (required except for commission/nodes)")

    a = ap.parse_args(argv)

    if a.cmd == "discover":
        print(json.dumps(discover.scan(), indent=2))
        return
    if a.cmd == "dial":
        _dial(a); return
    if a.cmd == "matter":
        _matter(a); return

    if not a.host:
        ap.error("--host is required (run `discover` first)")
    tv = FireTV(a.host)
    tv.connect()
    if a.cmd == "info":
        print(json.dumps(tv.info(), indent=2))
    elif a.cmd == "apps":
        print("\n".join(tv.packages(a.third)))
    elif a.cmd == "app":
        print(tv.current_app())
    elif a.cmd == "key":
        tv.key(a.name)
    elif a.cmd == "text":
        tv.text(a.text)
    elif a.cmd == "launch":
        tv.launch(a.package)
    elif a.cmd == "url":
        tv.open_url(a.url)
    elif a.cmd == "shell":
        print(tv.shell(" ".join(a.command)))
    elif a.cmd == "shot":
        tv.screenshot(a.path)
    elif a.cmd == "path":
        print(tv.apk_path(a.package))
    elif a.cmd == "pull":
        tv.pull(a.remote, a.local)


def _dial(a):
    from .dial import Dial
    if not a.host:
        raise SystemExit("--host is required for dial")
    dial = Dial.for_host(a.host)
    if a.action == "list":
        print(json.dumps(dial.installed(), indent=2))
    elif a.action == "status":
        print(dial.status(a.app))
    elif a.action == "launch":
        print("HTTP", dial.launch(a.app))
    elif a.action == "stop":
        print("HTTP", dial.stop(a.app))


def _matter(a):
    from .matter import MatterServer
    m = MatterServer(a.server)
    try:
        if a.action == "commission":
            print("node_id:", m.commission(a.value))
        elif a.action == "nodes":
            print(json.dumps(m.nodes(), indent=2))
        elif a.action == "node":
            print(json.dumps(m.endpoints(a.node), indent=2))
        else:
            if a.node is None:
                raise SystemExit("--node is required")
            if a.action == "on":
                m.power_on(a.node)
            elif a.action == "off":
                m.power_off(a.node)
            elif a.action == "toggle":
                m.power_toggle(a.node)
            elif a.action in ("play", "pause", "stop"):
                getattr(m, a.action)(a.node)
            elif a.action == "key":
                m.key(a.node, a.value)
    finally:
        m.close()


if __name__ == "__main__":
    sys.exit(main())
