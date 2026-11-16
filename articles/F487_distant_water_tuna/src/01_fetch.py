"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
農林水産省「漁業・養殖業生産統計」長期累年（e-Stat）：部門別（1979〜2024年）、海面漁業種類別（1956〜2024年）、海面漁業魚種別（1956〜2024年）。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    "gyogyo_bumon_1979_2024.xlsx": (E.format("000040416368"), "総括表1 漁業・養殖業部門別累年統計 生産量 全国（1979〜2024年）"),
    "gyogyo_shurui_1956_2024.xlsx": (E.format("000040416369"), "海面漁業の部2 海面漁業種類別漁獲量累年統計 全国（1956〜2024年）"),
    "gyogyo_gyoshu_1956_2024.xlsx": (E.format("000040416370"), "海面漁業の部3 海面漁業魚種別漁獲量累年統計 全国（1956〜2024年）"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "出典：農林水産省「漁業・養殖業生産統計」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00500216）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
