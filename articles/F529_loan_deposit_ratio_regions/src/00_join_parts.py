"""data/ の中で、GitHub の1ファイルの上限に合わせて分けて置いたファイル（<名前>.part000, .part001, …）を、
元のファイルがなければ1つにつなぎ直す。つないだあと sha256 を <名前>.sha256 と照らす。"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p0 in sorted((ROOT / "data").rglob("*.part000")):
    base = p0.with_name(p0.name[: -len(".part000")])
    if base.exists():
        continue
    parts = sorted(p0.parent.glob(base.name + ".part[0-9][0-9][0-9]"))
    with open(base, "wb") as w:
        for p in parts:
            w.write(p.read_bytes())
    want = (base.parent / (base.name + ".sha256")).read_text().split()[0]
    got = hashlib.sha256(base.read_bytes()).hexdigest()
    assert got == want, f"sha256 mismatch: {base}"
