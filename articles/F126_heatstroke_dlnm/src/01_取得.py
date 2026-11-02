"""01 取得：熱中症の救急搬送（日・都道府県）と気象庁の日ごとの気温・湿度

2026-11-03 にブラウザの中で取得したものを data/raw/ に置いています（このコンテナからは政府サイトに届かないため）。
ふつうのネット環境なら、このスクリプトで同じものが取れます（サイトの形式が変わったら直してください）。

- 総務省消防庁「熱中症による救急搬送人員に関するデータ」過去のデータ一覧（確定値、日別・都道府県別）
  https://www.fdma.go.jp/disaster/heatstroke/post4.html の heatstroke003_data_{h27_2,h28,...,r7}.xlsx（2015〜2025年、各年5〜9月。2020年は6〜9月）
- 気象庁「過去の気象データ検索」日ごとの値（47の気象台、2015〜2025年の5〜9月）
  https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php?prec_no=..&block_no=..&year=..&month=..&day=&view=
"""
import io, time
import requests
import pandas as pd
from common import RAW, STATIONS

S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (research script)"
FILES = ["items/heatstroke003_data_h27_2", "item/heatstroke003_data_h28", "item/heatstroke003_data_h29", "item/heatstroke003_data_h30"] + \
        [f"items/heatstroke003_data_r{i}" for i in range(1, 8)]
WANT = ["搬送人員（計）", "年齢区分：高齢者", "年齢区分：成人", "年齢区分：少年", "傷病程度：死亡", "傷病程度：重症", "傷病程度：中等症", "傷病程度：軽症", "発生場所：住居"]
COLS = ["total", "elderly", "adult", "youth", "death", "severe", "moderate", "mild", "home"]


def heatstroke():
    out = []
    for f in FILES:
        b = S.get(f"https://www.fdma.go.jp/disaster/heatstroke/{f}.xlsx", timeout=60).content
        for sn, df in pd.read_excel(io.BytesIO(b), sheet_name=None).items():
            df.columns = [str(c).strip() for c in df.columns]
            d = pd.DataFrame({"date": pd.to_datetime(df["日付"]).dt.date, "pref": df["都道府県コード"]})
            for w, c in zip(WANT, COLS):
                d[c] = df[w] if w in df else None
            out.append(d.dropna(subset=["pref"]))
        time.sleep(1)
    pd.concat(out).to_csv(RAW / "heatstroke_daily_2015_2025.csv", index=False)


def jma():
    rows = []
    for p, prec, blk, name in STATIONS:
        for y in range(2015, 2026):
            for m in range(5, 10):
                html = S.get("https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php",
                             params=dict(prec_no=prec, block_no=blk, year=y, month=m, day="", view=""), timeout=60).text
                t = pd.read_html(io.StringIO(html), attrs={"id": "tablefix1"})[0]
                for r in t.itertuples(index=False):
                    if str(r[0]).isdigit():
                        rows.append((p, f"{y}-{m:02d}-{int(r[0]):02d}", r[6], r[7], r[8], r[9]))
                time.sleep(1)
    pd.DataFrame(rows, columns=["pref", "date", "tmean", "tmax", "tmin", "rh"]).to_csv(RAW / "jma_daily_2015_2025.csv", index=False)


if __name__ == "__main__":
    heatstroke(); jma()
