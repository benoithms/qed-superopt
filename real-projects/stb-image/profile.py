"""Share of PNG decoding spent in rows filtered with Paeth, on the images of project.json:
    PYTHONPATH=. python real-projects/stb-image/profile.py --machine "<conditions>" --out <file>

The time-stamp counter is read around the filter switch of each row, so the share is an upper
bound on what a faster stbi__paeth can give. It adds two counter reads per row, not per byte.
--smoke only checks that this builds and runs on another machine: its numbers mean nothing."""

import argparse
import json
import platform
import statistics
import subprocess
from pathlib import Path

from qed import config

HERE = Path(__file__).parent
WORK = HERE / "work"
SWITCH = "      // perform actual filtering\n      switch (filter) {"
AFTER = "      raw += nk;\n\n      // expand decoded bits"
DRIVER = r"""
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#include <stdio.h>
#if defined(__x86_64__)
#include <x86intrin.h>
#define QED_NOW() __rdtsc()
#else
#include <time.h>
static unsigned long long QED_NOW(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000000000ull + t.tv_nsec;
}
#endif
static unsigned long long qed_paeth;
#include "stb_timed.h"
int main(int argc, char **argv) {
    unsigned long long total = 0;
    for (int i = 1; i < argc; i++) {
        FILE *f = fopen(argv[i], "rb");
        fseek(f, 0, SEEK_END);
        long n = ftell(f);
        rewind(f);
        unsigned char *buf = malloc(n);
        if (fread(buf, 1, n, f) != (size_t)n) return 1;
        fclose(f);
        int w, h, c;
        for (int r = 0; r < 5; r++) {
            unsigned long long t0 = QED_NOW();
            unsigned char *d = stbi_load_from_memory(buf, n, &w, &h, &c, 0);
            total += QED_NOW() - t0;
            if (!d) return 1;
            stbi_image_free(d);
        }
        free(buf);
    }
    printf("%llu %llu\n", total, qed_paeth);
    return 0;
}
"""


def build(smoke: bool) -> Path:
    s = (WORK / "stb_image.h").read_text()
    if s.count(SWITCH) != 1 or s.count(AFTER) != 1:
        raise SystemExit("stb_image.h does not match the expected filter loop")
    s = s.replace(SWITCH, "      unsigned long long qed_t0 = QED_NOW();\n" + SWITCH)
    s = s.replace(
        AFTER, "      if (filter == STBI__F_paeth) qed_paeth += QED_NOW() - qed_t0;\n" + AFTER
    )
    (WORK / "stb_timed.h").write_text(s)
    (WORK / "profile.c").write_text(DRIVER)
    flags = ["-O3", "-g0"]
    if not smoke:
        flags += [f"--target={config.TRIPLE}", f"-march={config.CPU}"]
    else:
        sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True, text=True).stdout
        flags += ["-isysroot", sdk.strip()]
    exe = WORK / "profile"
    subprocess.run([config.CLANG, *flags, WORK / "profile.c", "-o", exe, "-lm"], check=True)
    return exe


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--machine", help="turbo on/off, power plan, what else runs")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--launches", type=int, default=5)
    ap.add_argument("--cpu", type=int, default=2, help="CPU to pin with taskset")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if not args.smoke and not (args.machine and args.out):
        ap.error("--machine and --out are required")
    exe = build(args.smoke)
    images = sorted(str(p) for p in (WORK / "images").glob("*.png"))
    pin = [] if args.smoke else ["taskset", "-c", str(args.cpu)]
    rows = []
    for _ in range(args.launches):
        out = subprocess.run([*pin, exe, *images], capture_output=True, text=True, check=True)
        total, paeth = map(int, out.stdout.split())
        rows.append({"total": total, "paeth": paeth, "share": paeth / total})
    shares = [r["share"] for r in rows]
    mid, low, high = statistics.median(shares), min(shares), max(shares)
    print(f"Paeth rows: {mid:.1%} (min {low:.1%}, max {high:.1%})")
    if args.out:
        rec = {"machine": args.machine, "cpu": platform.processor(), "images": len(images)}
        rec["launches"] = rows
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()
