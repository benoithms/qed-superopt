"""Steps 3 and 4 of the protocol: put a proven rewrite back into the whole program and time it.
    PYTHONPATH=. python real-projects/stb-image/whole.py paeth-int rewrite.ll \
        --machine "<conditions>" --out results/real-projects/stb-image/whole-<cpu>.json

rewrite.ll holds @f, proven again here against the function's src.c: nothing else is accepted.
Both binaries come from the same unoptimized module, then opt -O3 and llc, and differ only by
the body of stbi__paeth. They must decode every image to the same bytes before any timing.
--smoke checks all this on another machine, without timing."""

import argparse
import json
import platform
import re
import statistics
import subprocess
from pathlib import Path

from qed import config
from qed.extract import body, extract, function
from qed.verify import Status, verify

HERE = Path(__file__).parent
WORK = HERE / "work"
MIN_SPEEDUP = 1.02
DRIVER = r"""
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#include <stdio.h>
#include <time.h>
#include "stb_image.h"
static unsigned long long now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000000000ull + t.tv_nsec;
}
int main(int argc, char **argv) {
    unsigned long long total = 0, sum = 14695981039346656037ull;
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
            unsigned long long t0 = now();
            unsigned char *d = stbi_load_from_memory(buf, n, &w, &h, &c, 0);
            total += now() - t0;
            if (!d) return 1;
            if (r == 0)
                for (long k = 0; k < (long)w * h * c; k++) sum = (sum ^ d[k]) * 1099511628211ull;
            stbi_image_free(d);
        }
        free(buf);
    }
    printf("%llu %llu\n", total, sum);
    return 0;
}
"""
PAETH = re.compile(r"^define internal i32 @stbi__paeth\((.*?)\)([^{]*)\{.*?^\}", re.S | re.M)


def tools(smoke: bool) -> tuple[list, list]:
    if not smoke:
        return [f"--target={config.TRIPLE}", f"-march={config.CPU}"], [f"-mcpu={config.CPU}"]
    sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True, text=True).stdout
    return ["-isysroot", sdk.strip()], []


def module(flags: list) -> str:
    (WORK / "whole.c").write_text(DRIVER)
    cmd = [config.CLANG, "-O3", "-g0", "-fdiscard-value-names", *flags, "-I", WORK]
    cmd += ["-Xclang", "-disable-llvm-passes", "-S", "-emit-llvm", WORK / "whole.c", "-o", "-"]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def replaced(ir: str, entry: str, tgt_body: str, declares: list[str]) -> str:
    """The program with this body in stbi__paeth, behind a truncation to bytes for paeth-u8."""
    m = PAETH.search(ir)
    if not m:
        raise SystemExit("stbi__paeth not found in the module")
    attrs = m.group(2)
    args = "i32 noundef %0, i32 noundef %1, i32 noundef %2"
    if entry == "paeth-int":
        new = f"define internal i32 @stbi__paeth({args}){attrs}{{\n{tgt_body}\n}}"
    else:
        u8 = "i8 noundef zeroext %0, i8 noundef zeroext %1, i8 noundef zeroext %2"
        new = (
            f"define internal i32 @qed_paeth({u8}){attrs}{{\n{tgt_body}\n}}\n"
            f"define internal i32 @stbi__paeth({args}){attrs}{{\n"
            "  %4 = trunc i32 %0 to i8\n  %5 = trunc i32 %1 to i8\n  %6 = trunc i32 %2 to i8\n"
            "  %7 = call i32 @qed_paeth(i8 zeroext %4, i8 zeroext %5, i8 zeroext %6)\n"
            "  ret i32 %7\n}"
        )
    known = [d for d in declares if d.split("(")[0].split()[-1] not in ir]
    return ir[: m.start()] + new + ir[m.end() :] + "\n" + "\n".join(known) + "\n"


def binary(ir: str, name: str, flags: list, llc_cpu: list) -> Path:
    ll, asm, exe = WORK / f"{name}.ll", WORK / f"{name}.s", WORK / name
    ll.write_text(ir)
    opt = [config.OPT, "-O3", "-S", *llc_cpu, ll, "-o", WORK / f"{name}.o3.ll"]
    subprocess.run(opt, check=True)
    subprocess.run([config.LLC, "-O3", *llc_cpu, WORK / f"{name}.o3.ll", "-o", asm], check=True)
    sys_flags = [f for f in flags if not f.startswith("-march")]
    subprocess.run([config.CLANG, *sys_flags, asm, "-o", exe, "-lm"], check=True)
    return exe


def run(exe: Path, images: list[str], pin: list) -> tuple[int, str]:
    out = subprocess.run([*pin, exe, *images], capture_output=True, text=True, check=True)
    total, digest = out.stdout.split()
    return int(total), digest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("entry", choices=["paeth-int", "paeth-u8"])
    ap.add_argument("rewrite", type=Path)
    ap.add_argument("--machine", help="turbo on/off, power plan, what else runs")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--launches", type=int, default=5)
    ap.add_argument("--cpu", type=int, default=2, help="CPU to pin with taskset")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if not args.smoke and not (args.machine and args.out):
        ap.error("--machine and --out are required")

    src_ll = extract(HERE / "functions" / args.entry / "src.c")
    tgt_ll = args.rewrite.read_text()
    proof = verify(src_ll, tgt_ll)
    if proof.status is not Status.PROVEN:
        raise SystemExit(f"rewrite refused, not proven: {proof.status.value}")

    flags, llc_cpu = tools(args.smoke)
    ir = module(flags)
    declares = [line for line in tgt_ll.splitlines() if line.startswith("declare ")]
    base = binary(ir, "base", flags, llc_cpu)
    new_ir = replaced(ir, args.entry, body(function(tgt_ll)), declares)
    new = binary(new_ir, "rewrite", flags, llc_cpu)

    images = sorted(str(p) for p in (WORK / "images").glob("*.png"))
    pin = [] if args.smoke else ["taskset", "-c", str(args.cpu)]
    _, want = run(base, images, pin)
    _, got = run(new, images, pin)
    if want != got:
        raise SystemExit("the two binaries decode to different bytes: stopped")
    print(f"proven, and both binaries decode {len(images)} images to the same bytes ({want})")
    if args.smoke:
        return

    rows = []
    for _ in range(args.launches):
        before, _ = run(base, images, pin)
        after, _ = run(new, images, pin)
        rows.append({"base_ns": before, "rewrite_ns": after, "speedup": before / after})
    speedups = [r["speedup"] for r in rows]
    win = all(s > MIN_SPEEDUP for s in speedups)
    print(f"speedup {statistics.median(speedups):.3f}x ({min(speedups):.3f}-{max(speedups):.3f})")
    print("every launch above", MIN_SPEEDUP, "on this CPU" if win else "NOT met on this CPU")
    rec = {"entry": args.entry, "machine": args.machine, "cpu": platform.processor()}
    rec |= {"images": len(images), "min_speedup": MIN_SPEEDUP, "win_on_this_cpu": win}
    rec |= {"launches": rows, "tgt_ll": tgt_ll, "alive2": proof.output}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()
