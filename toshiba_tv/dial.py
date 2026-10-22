"""DIAL client for the Fire TV (launch streaming apps by name over HTTP).

DIAL = DIscovery And Launch. Pure standard, pure stdlib: SSDP locates the DIAL
REST base URL, then you GET/POST/DELETE /<AppName> to query, launch, or stop an
app. Works with no ADB and no extra dependencies.
"""
import re
import socket
import urllib.error
import urllib.request

SSDP_ADDR = ("239.255.255.250", 1900)
DIAL_ST = "urn:dial-multiscreen-org:service:dial:1"
_MSEARCH = (
    "M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\nMX: 2\r\nST: ' + DIAL_ST + "\r\n\r\n"
).encode()

# Common DIAL app names. The TV advertises the canonical names; these are the
# ones most Fire TVs answer to.
APPS = ("YouTube", "Netflix", "PrimeVideo", "Hulu", "Disney", "HBOMax", "Max")


def _application_url(location, timeout=3.0):
    """The DIAL REST base is in the Application-URL header of a HEAD/GET to LOCATION."""
    req = urllib.request.Request(location, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        base = r.headers.get("Application-URL")
    return base.rstrip("/") if base else None


def discover(timeout=4.0):
    """Return a list of DIAL REST base URLs found on the LAN."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.sendto(_MSEARCH, SSDP_ADDR)
    bases, seen = [], set()
    try:
        while True:
            data, _ = sock.recvfrom(65507)
            m = re.search(r"^LOCATION:\s*(.+)$", data.decode(errors="replace"), re.I | re.M)
            if m and m.group(1).strip() not in seen:
                seen.add(m.group(1).strip())
                try:
                    if base := _application_url(m.group(1).strip()):
                        bases.append(base)
                except Exception:
                    pass
    except socket.timeout:
        pass
    return bases


class Dial:
    """DIAL REST against one base URL, e.g. http://192.168.1.163:<port>/apps."""

    def __init__(self, base_url):
        self.base = base_url.rstrip("/")

    @classmethod
    def for_host(cls, host, timeout=4.0):
        """Find the DIAL base belonging to a specific TV IP."""
        for base in discover(timeout):
            if host in base:
                return cls(base)
        raise RuntimeError(f"no DIAL endpoint advertised by {host}")

    def _req(self, app, method="GET", body=b""):
        url = f"{self.base}/{app}"
        req = urllib.request.Request(url, data=body or None, method=method)
        if body:
            req.add_header("Content-Type", "text/plain; charset=utf-8")
        with urllib.request.urlopen(req, timeout=5.0) as r:
            return r.status, r.read().decode(errors="replace")

    def status(self, app):
        """Return the app's DIAL state XML (running/stopped/installable)."""
        return self._req(app)[1]

    def launch(self, app, payload=""):
        """Launch (or foreground) an app. Returns the HTTP status."""
        return self._req(app, "POST", payload.encode())[0]

    def stop(self, app, instance="run"):
        """Stop a running app instance."""
        return self._req(f"{app}/{instance}", "DELETE")[0]

    def installed(self, apps=APPS):
        """Probe which known apps the TV reports as present."""
        out = {}
        for a in apps:
            try:
                xml = self.status(a)
                # DIAL app-info XML carries <state>running|stopped|installable</state>
                m = re.search(r"<state>\s*(\w+)", xml) or re.search(r'state="(\w+)"', xml)
                out[a] = m.group(1) if m else "unknown"
            except urllib.error.HTTPError as e:
                # 403 on GET is YouTube's known DIAL quirk; the app is present and
                # POST /YouTube (launch) still works.
                out[a] = "not-found" if e.code == 404 else ("present-403" if e.code == 403 else f"http-{e.code}")
            except Exception as e:
                out[a] = f"error:{type(e).__name__}"
        return out
