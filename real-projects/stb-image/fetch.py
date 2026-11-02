"""Download stb_image and the images named in project.json into work/, checking every hash:
    python real-projects/stb-image/fetch.py

Nothing third-party is committed: the commit and the hashes are enough to get the same files."""

import hashlib
import json
import urllib.request
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
    get(p["url"], WORK / "stb_image.h", p["sha256"])
    for name, want in p["images"]["sha256"].items():
        get(p["images"]["url"] + name, WORK / "images" / name, want)
    print(f"ok: stb_image {p['commit'][:7]}, {len(p['images']['sha256'])} images")


if __name__ == "__main__":
    main()
