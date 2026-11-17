"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
環境省「一般廃棄物処理実態調査結果」施設整備状況の「焼却施設」の表（施設ごと）。平成17年度（2005）〜令和6年度（2024）。"""
import pathlib, urllib.request, hashlib, datetime, re, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.env.go.jp/recycle/waste_tech/ippan/"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}


def code(fy):
    return f"h{fy - 1988}" if fy <= 2018 else ("r1" if fy == 2019 else f"r{fy - 2018}")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for fy in range(2005, 2025):
        c = code(fy)
        with urllib.request.urlopen(urllib.request.Request(BASE + c + "/index.html", headers=UA), timeout=60) as r:
            html = r.read().decode("utf-8", "replace")
        href = re.search(r'href="(data/seibi/facility/01\.xlsx?)"', html).group(1)
        url = BASE + c + "/" + href
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            b = r.read()
        name = f"incinerator_fy{fy}.{href.rsplit('.', 1)[1]}"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {fy}年度 焼却施設（施設ごと） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "出典：環境省「一般廃棄物処理実態調査結果」（https://www.env.go.jp/recycle/waste_tech/ippan/stats.html）の各年度の「施設整備状況」→「焼却施設」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
