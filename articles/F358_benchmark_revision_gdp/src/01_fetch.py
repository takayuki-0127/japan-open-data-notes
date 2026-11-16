"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。内閣府「四半期別GDP速報」の二つの公表回。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
B = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2025/{}/tables/{}.csv"
FILES = {}
for qe, s, desc in [("qe253", "2531", "2025年7-9月期1次速報（2015年基準）"), ("qe253_2", "2532", "2025年7-9月期2次速報（2020年基準）")]:
    for k, kd in [("gaku-mcy", "名目暦年"), ("gaku-jcy", "実質暦年"), ("def-cy", "暦年デフレーター")]:
        FILES[f"esri_{k}{s}.csv"] = (B.format(qe, f"{k}{s}"), f"{desc} {kd}")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：内閣府「四半期別GDP速報」。CSV は Shift_JIS（cp932）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
