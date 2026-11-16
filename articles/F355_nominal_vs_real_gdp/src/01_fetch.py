"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。内閣府「四半期別GDP速報」2026年4-6月期2次速報。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/{}.csv"
FILES = {"gaku-mcy2622": "名目暦年（10億円）", "gaku-jcy2622": "実質暦年（2020暦年連鎖価格、10億円）", "def-cy2622": "暦年デフレーター（2020暦年＝100）"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for k, desc in FILES.items():
        url = BASE.format(k); name = f"esri_qe2026q2_2nd_{k}.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：内閣府「四半期別GDP速報」（2026年4-6月期2次速報）。CSV は Shift_JIS（cp932）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
