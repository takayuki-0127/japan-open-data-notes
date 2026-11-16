"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
外務省「海外在留邦人数調査統計」（e-Stat 掲載の Excel）。令和7年・令和元年・平成27年の3年分。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("000040394912", "mofa_overseas_2025.xlsx", "令和7年（2025年）版：邦人数推移（1991〜2025年、長期滞在者・永住者・男女別）、国（地域）別の一覧表（2025年10月1日）"),
    ("000032018181", "mofa_overseas_2019.xlsx", "令和元年（2019年）版：国（地域）別の一覧表（2019年10月1日）"),
    ("000031418175", "mofa_overseas_2015.xlsx", "平成27年（2015年）版：地域別の在留邦人数・長期滞在者数・永住者数の推移（2006〜2015年）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for sid, name, desc in FILES:
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | 外務省「海外在留邦人数調査統計」{desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "出典：外務省「海外在留邦人数調査統計」（e-Stat）。外務省のサイトは自動取得に 403 を返すため、e-Stat 掲載のファイルを使った。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
