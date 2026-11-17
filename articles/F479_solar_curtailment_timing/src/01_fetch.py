"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
九州電力送配電「エリア需給実績データ」（2016年度〜2025年度）と、内閣府「国民の祝日」CSV。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.kyuden.co.jp/td_area_jukyu/"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}

FILES = {}
# 2016〜2023年度：四半期ごとの1時間値（ファイル名の年は年度。H28=2016年度）
for fy in range(2016, 2024):
    tag = {2016: "H28", 2017: "H29", 2018: "H30"}.get(fy, str(fy))
    for q in range(1, 5):
        n = f"area_jyukyu_jisseki_{tag}_{q}Q.csv"
        FILES[n] = (BASE + "csv_area_jyukyu_jisseki/" + n, f"{fy}年度 第{q}四半期 1時間値")
# 2024年度〜2025年度：月ごとの30分値
for y, m in [(y, m) for y in (2024, 2025, 2026) for m in range(1, 13)]:
    if (y, m) < (2024, 4) or (y, m) > (2026, 3):
        continue
    n = f"eria_jukyu_{y}{m:02d}_09.csv"
    FILES[n] = (BASE + "csv/" + n, f"{y}年{m}月 30分値")
FILES["syukujitsu.csv"] = ("https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv", "内閣府 国民の祝日・休日")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "出典：九州電力送配電「エリア需給実績データ」（でんき予報のページ https://www.kyuden.co.jp/td_area_jukyu/jukyu.html）、内閣府「国民の祝日について」。CSV は Shift_JIS（cp932）。",
              "2016〜2023年度は1時間値（MWh）、2024年度以降は30分値（MW平均）。当月分は速報を含むため、完結した2025年度（2026年3月）までを取った。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
