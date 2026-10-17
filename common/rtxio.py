"""RTX Container gemeinsame E/A (v1.0, 17.10.2026). Eingaben nur per URL (z. B. vorsignierte Wasabi-GET-URL),
Ausgaben per HTTP PUT auf vorsignierte URLs. Keine Zugangsdaten im Image."""
import hashlib, os, tempfile, urllib.request, urllib.parse

MAX_BYTES = int(os.environ.get("RTX_MAX_INPUT_BYTES", str(4 * 1024 ** 3)))

def _check_url(url: str) -> str:
    u = urllib.parse.urlparse(url)
    if u.scheme != "https":
        raise ValueError("nur https-URLs erlaubt")
    return url

def download(url: str, suffix: str = "") -> str:
    _check_url(url)
    fd, path = tempfile.mkstemp(suffix=suffix, dir=os.environ.get("RTX_WORK", "/tmp"))
    n = 0
    with urllib.request.urlopen(url, timeout=600) as r, os.fdopen(fd, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            n += len(b)
            if n > MAX_BYTES:
                raise ValueError("Eingabe zu groß")
            f.write(b)
    return path

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def upload(path: str, put_url: str, content_type: str = "application/octet-stream") -> dict:
    _check_url(put_url)
    size = os.path.getsize(path)
    sha = sha256_file(path)
    with open(path, "rb") as f:
        req = urllib.request.Request(put_url, data=f, method="PUT", headers={"Content-Type": content_type, "Content-Length": str(size)})
        with urllib.request.urlopen(req, timeout=600) as r:
            status = r.status
    return {"bytes": size, "sha256": sha, "http": status}

def ext_of(url: str, default: str) -> str:
    p = urllib.parse.urlparse(url).path
    e = os.path.splitext(p)[1].lower()
    return e if e and len(e) <= 6 else default
