"""CLI: python -m toshiba_tv.cli {discover|info|key|text|launch|url|apps|app|shell|shot} ..."""
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
    a = ap.parse_args(argv)

    if a.cmd == "discover":
        print(json.dumps(discover.scan(), indent=2))
        return
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


if __name__ == "__main__":
    sys.exit(main())
