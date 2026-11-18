"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 関西電力送配電「エリア需給実績」：2016〜2023年度の年度ファイル（1時間値）、2024〜2026年の7〜9月の月ファイル（30分値）
  （計画では東京電力パワーグリッドを使う予定だったが、同社のサイトはこのスクリプトの User-Agent からの取得を拒否した（HTTP 403）ため、関西に替えた）
- 九州電力送配電「エリア需給実績データ」：2016〜2023年度の第2四半期ファイル（1時間値、7〜9月）、2024〜2026年の7〜9月の月ファイル（30分値）
- 内閣府「国民の祝日」CSV"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
KA = "https://www.kansai-td.co.jp/denkiyoho/area-performance/csv/"
KM = "https://www.kansai-td.co.jp/interchange/denkiyoho/area-performance/"
K = "https://www.kyuden.co.jp/td_area_jukyu/"
FILES = {}
for fy in range(2016, 2024):
    FILES[f"kansai_area_jyukyu_jisseki_{fy}.csv"] = (KA + f"area_jyukyu_jisseki_{fy}.csv", f"関西 {fy}年度 1時間値（MWh）")
    tag = {2016: "H28", 2017: "H29", 2018: "H30"}.get(fy, str(fy))
    FILES[f"kyushu_area_jyukyu_jisseki_{tag}_2Q.csv"] = (K + f"csv_area_jyukyu_jisseki/area_jyukyu_jisseki_{tag}_2Q.csv", f"九州 {fy}年度 第2四半期（7〜9月） 1時間値（MWh）")
for y in (2024, 2025, 2026):
    for m in (7, 8, 9):
        FILES[f"kansai_eria_jukyu_{y}{m:02d}_06.csv"] = (KM + f"eria_jukyu_{y}{m:02d}_06.csv", f"関西 {y}年{m}月 30分値（MW平均）")
        FILES[f"kyushu_eria_jukyu_{y}{m:02d}_09.csv"] = (K + f"csv/eria_jukyu_{y}{m:02d}_09.csv", f"九州 {y}年{m}月 30分値（MW平均）")
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
        time.sleep(0.4)
    lines += ["", "- 関西電力送配電「エリア需給実績」：https://www.kansai-td.co.jp/denkiyoho/area-performance/past.html （2024年度以降の月ファイルは https://www.kansai-td.co.jp/denkiyoho/area-performance/index.html ）",
              "- 九州電力送配電「エリア需給実績」：https://www.kyuden.co.jp/td_area_jukyu/jukyu.html",
              "- 時刻：1時間値はその1時間の始まり。30分値は、関西は30分の始まり、九州は30分の終わり（02_build.py で1時間の始まりにそろえる）。",
              "", "出典：関西電力送配電・九州電力送配電「エリア需給実績」、内閣府「国民の祝日」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
