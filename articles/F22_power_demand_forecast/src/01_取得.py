"""01 取得：電力需要（東京・関西）と気象庁の日別値を取ってくる

2026-10-27 にブラウザの中で取得したファイルを data/raw/ に置いています。
ふつうのネット環境なら、このスクリプトで同じものが取れます（サイト側の形式が変わったら直してください）。

- 東京電力パワーグリッド「エリア需給実績データ」
  - 2016〜2023年度：https://www.tepco.co.jp/forecast/html/images/area-YYYY.csv（1時間ごと、単位 万kWh、数字にカンマあり）
  - 2024年2月以降：https://www.tepco.co.jp/forecast/html/images/eria_jukyu_YYYYMM_03.csv（30分ごと、単位 MW 平均）
- 関西電力送配電「エリア需給実績」
  - 2024年4月以降：https://www.kansai-td.co.jp/interchange/denkiyoho/area-performance/eria_jukyu_YYYYMM_06.csv
- 気象庁「過去の気象データ検索」日ごとの値（東京 prec_no=44 block_no=47662、大阪 prec_no=62 block_no=47772）
  - https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php?prec_no=..&block_no=..&year=..&month=..&day=&view=
"""
import time
import io
import requests
import pandas as pd
from common import RAW

S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (research script)"


def sjis(url):
    r = S.get(url, timeout=60)
    r.raise_for_status()
    return r.content.decode("shift_jis", errors="replace")


def tepco():
    old = []
    for y in range(2016, 2024):
        t = sjis(f"https://www.tepco.co.jp/forecast/html/images/area-{y}.csv")
        old += [l for l in t.splitlines() if l[:4].isdigit()]
    (RAW / "tepco_area_2016_2023.csv").write_text("\n".join(old) + "\n", encoding="utf-8")
    rows = []
    for ym in pd.period_range("2024-02", pd.Timestamp.today().strftime("%Y-%m"), freq="M"):
        try:
            t = sjis(f"https://www.tepco.co.jp/forecast/html/images/eria_jukyu_{ym.strftime('%Y%m')}_03.csv")
        except requests.HTTPError:
            continue
        for l in t.splitlines():
            c = l.split(",")
            if c[0][:4].isdigit():
                rows.append((c[0], int(c[1].split(":")[0]), float(c[2])))
        time.sleep(1)
    df = pd.DataFrame(rows, columns=["date", "hour", "mw"]).groupby(["date", "hour"], sort=False)["mw"].mean().round()
    df.rename("demand_mw").reset_index().to_csv(RAW / "tepco_monthly_2024on_hourly.csv", index=False)


def kansai():
    out = []
    for ym in pd.period_range("2024-04", pd.Timestamp.today().strftime("%Y-%m"), freq="M"):
        try:
            t = sjis(f"https://www.kansai-td.co.jp/interchange/denkiyoho/area-performance/eria_jukyu_{ym.strftime('%Y%m')}_06.csv")
        except requests.HTTPError:
            continue
        out += [l for l in t.splitlines() if l[:4].isdigit()]
        time.sleep(1)
    (RAW / "kansai_area_2024on.csv").write_text("\n".join(out) + "\n", encoding="utf-8")


def jma():
    lines = ["station,date,temp_mean,temp_max,temp_min,humid_mean,sunshine_h,precip_mm"]
    for name, p, b in [("tokyo", 44, 47662), ("osaka", 62, 47772)]:
        for ym in pd.period_range("2016-04", "2026-09", freq="M"):
            url = (f"https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php?prec_no={p}&block_no={b}"
                   f"&year={ym.year}&month={ym.month}&day=&view=")
            tab = pd.read_html(io.StringIO(S.get(url, timeout=60).text), attrs={"id": "tablefix1"})[0]
            for _, r in tab.iterrows():
                d = str(r.iloc[0])
                if not d.isdigit():
                    continue
                v = [str(r.iloc[i]).replace(")", "").replace("]", "").strip() for i in (6, 7, 8, 9, 16, 3)]
                lines.append(f"{name},{ym.year}-{ym.month:02d}-{int(d):02d}," + ",".join(v))
            time.sleep(1)
    (RAW / "jma_daily_tokyo_osaka.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    tepco(); kansai(); jma()
