"""Find a Toshiba Fire TV on the LAN: SSDP M-SEARCH plus a TCP probe of common ports."""
import re
import socket
import urllib.request

SSDP_ADDR = ("239.255.255.250", 1900)
MSEARCH = (
    "M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\nMX: 2\r\nST: ssdp:all\r\n\r\n'
).encode()

# port -> what it usually means on a Fire TV edition
PORTS = {
    5555: "adb (needs ADB debugging enabled)",
    8009: "chromecast / google cast",
    8008: "cast http",
    8060: "roku ecp (not a Fire TV)",
    8080: "http alt",
    1900: "upnp",
    9197: "dial / amazon",
    55442: "amazon device service",
    55443: "amazon device service (tls)",
}


def ssdp(timeout=4.0):
    """Return {ip: {header: value}} for every SSDP responder."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.sendto(MSEARCH, SSDP_ADDR)
    found = {}
    try:
        while True:
            data, (ip, _) = sock.recvfrom(65507)
            headers = dict(
                m.groups()
                for m in re.finditer(r"^([\w-]+):\s*(.*)$", data.decode(errors="replace"), re.M)
            )
            found.setdefault(ip, {}).update({k.upper(): v for k, v in headers.items()})
    except socket.timeout:
        pass
    return found


def describe(location, timeout=3.0):
    """Fetch the UPnP device description XML (manufacturer, model, friendly name)."""
    try:
        with urllib.request.urlopen(location, timeout=timeout) as r:
            xml = r.read().decode(errors="replace")
    except Exception:
        return {}
    return {
        tag: m.group(1)
        for tag in ("friendlyName", "manufacturer", "modelName", "modelNumber", "UDN")
        if (m := re.search(rf"<{tag}>(.*?)</{tag}>", xml))
    }


def probe(ip, ports=PORTS, timeout=0.6):
    open_ports = {}
    for port, label in ports.items():
        with socket.socket() as s:
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                open_ports[port] = label
    return open_ports


def scan():
    """SSDP sweep; returns candidate devices that look like Toshiba / Fire TV."""
    results = []
    for ip, hdr in ssdp().items():
        info = describe(hdr["LOCATION"]) if "LOCATION" in hdr else {}
        blob = " ".join([*hdr.values(), *info.values()]).lower()
        if any(k in blob for k in ("toshiba", "amazon", "fire", "aft")):
            results.append({"ip": ip, "ssdp": hdr, "upnp": info, "ports": probe(ip)})
    return results
