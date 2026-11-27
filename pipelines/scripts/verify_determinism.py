"""Verify `player derive` produces byte-identical output across runs.

Runs the artifact generation twice in separate processes with different PYTHONHASHSEED
values (so set/dict ordering bugs on str keys surface) and different TZ values
(so naive datetimes read as local time surface), each writing to its own temp
dir, then compares the two output trees byte-for-byte.

Usage (from repo root): uv run pipelines/scripts/verify_determinism.py [--keep]
"""
import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# (PYTHONHASHSEED, TZ) per run. Kathmandu's +05:45 offset is unlikely to cancel out by accident
RUN_ENVS = (("1", "UTC"), ("2", "Asia/Kathmandu"))


def worker(out_dir: str) -> int:
    """Run the artifact generation into out_dir."""
    from player import derive

    derive.run(out_dir=Path(out_dir))
    return 0


def run_once(out_dir: Path, seed: str, tz: str) -> None:
    """Spawn a fresh interpreter running the worker; raise on failure."""
    env = {**os.environ, "PYTHONHASHSEED": seed, "TZ": tz}
    proc = subprocess.run(
        [sys.executable, __file__, "--_worker", str(out_dir)],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout, proc.stderr, sep="\n")
        raise RuntimeError(f"player derive failed (PYTHONHASHSEED={seed}, TZ={tz})")


def list_files(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}


def first_diff_offset(a: Path, b: Path) -> int:
    da, db = a.read_bytes(), b.read_bytes()
    return next((i for i, (x, y) in enumerate(zip(da, db, strict=False)) if x != y), min(len(da), len(db)))


def compare(a: Path, b: Path) -> bool:
    """Print differences between two output trees; return True if identical."""
    files_a, files_b = list_files(a), list_files(b)
    ok = True

    for name in sorted(files_a ^ files_b):
        print(f"  only in {'run1' if name in files_a else 'run2'}: {name}")
        ok = False

    common = sorted(files_a & files_b)
    for name in common:
        fa, fb = a / name, b / name
        if not filecmp.cmp(fa, fb, shallow=False):
            off = first_diff_offset(fa, fb)
            ctx_a = fa.read_bytes()[max(0, off - 40):off + 40]
            ctx_b = fb.read_bytes()[max(0, off - 40):off + 40]
            print(f"  DIFF {name} @ byte {off}\n    run1: {ctx_a!r}\n    run2: {ctx_b!r}")
            ok = False

    print(f"Compared {len(common)} files")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Check `player derive` output is deterministic")
    parser.add_argument("--keep", action="store_true", help="Keep output dirs for inspection")
    parser.add_argument("--_worker", metavar="OUT_DIR", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args._worker:
        return worker(args._worker)

    tmp = Path(tempfile.mkdtemp(prefix="determinism_"))
    runs = [tmp / f"run{i + 1}" for i in range(len(RUN_ENVS))]
    try:
        for out_dir, (seed, tz) in zip(runs, RUN_ENVS, strict=True):
            print(f"Running player derive -> {out_dir} (PYTHONHASHSEED={seed}, TZ={tz})")
            run_once(out_dir, seed, tz)

        identical = compare(*runs)
        print("PASS: outputs byte-identical" if identical else "FAIL: outputs differ")
        return 0 if identical else 1
    finally:
        if args.keep:
            print(f"Outputs kept in {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
