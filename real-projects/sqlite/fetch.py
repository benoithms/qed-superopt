"""Download SQLite and its benchmark into work/, checking every hash:
    python real-projects/sqlite/fetch.py

Nothing third-party is committed: the version and the hashes are enough to get the same files."""

import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
WORK = HERE / "work"


def get(url: str, path: Path, want: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as r:
            path.write_bytes(r.read())
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != want:
        path.unlink()
        raise SystemExit(f"{path.name}: hash mismatch, removed")


def main() -> None:
    p = json.loads((HERE / "project.json").read_text())
    get(p["amalgamation"]["url"], WORK / "sq.zip", p["amalgamation"]["sha256"])
    get(p["speedtest1"]["url"], WORK / "speedtest1.c", p["speedtest1"]["sha256"])
    with zipfile.ZipFile(WORK / "sq.zip") as z:
        for name in z.namelist():
            if name.endswith(("/sqlite3.c", "/sqlite3.h")):
                (WORK / Path(name).name).write_bytes(z.read(name))
    print(f"ok: SQLite {p['version']}")


if __name__ == "__main__":
    main()
