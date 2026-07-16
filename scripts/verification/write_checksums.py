from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "replication" / "checksums" / "SHA256SUMS.txt"
SCIENTIFIC_ROOTS = [
    ROOT / "data" / "processed",
    ROOT / "data" / "metadata",
    ROOT / "results" / "tables",
    ROOT / "results" / "figures",
    ROOT / "results" / "diagnostics",
    ROOT / "docs" / "methodology",
    ROOT / "docs" / "provenance",
    ROOT / "manuscript",
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    files = sorted(
        (path for base in SCIENTIFIC_ROOTS for path in base.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    lines = [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in files]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} checksums to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
