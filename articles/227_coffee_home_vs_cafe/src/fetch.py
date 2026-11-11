"""data/ の CSV を e-Stat から作り直す（記事の作成時は、同じ URL をブラウザのページ内で取得した）。

- 家計調査（二人以上の世帯）長期時系列 品目分類（全品目）
    年：statInfId 000040270655（2015〜2019年）・000040270656（2020〜2024年）
    月：statInfId 000040270649（2015〜2019年）・000040270650（2020〜2024年）・000040270651（2025年1月〜）
  2025年の年の値は、月の表の12か月の合計（2024年で年の表と合計の差は±3円以内）
- 家計調査 年報 詳細結果表（Excel）
    第4-6表 世帯主の年齢階級別：2019 000031909558／2020 000032048838／2021 000032167634／
      2022 000040015264／2023 000040140561／2024 000040247212／2025 000040409549
    第4-1表 都道府県庁所在市別：2015 000031370135／2019 000031909555／2023 000040140558／
      2024 000040247209／2025 000040409546
- 消費者物価指数（2020年基準）品目別：同じリポジトリの articles/F209_prices_household_series_part1/data/cpi_items_annual.csv
  （元は e-Stat statInfId 000032103844）から、使う品目の列を抜き出した

使い方：python fetch.py（ネットにつながる環境で）
"""
import csv
import io
import requests
import pandas as pd
from common import DATA
from kakei_parse import parse

ITEMS = ["コーヒー", "コーヒー飲料", "喫茶代", "飲料", "茶類"]
CPI_ITEMS = ["インスタントコーヒー", "コーヒー豆", "コーヒー飲料Ａ", "コーヒー飲料Ｂ", "コーヒー（外食）Ａ", "コーヒー（外食）Ｂ", "コーヒー・ココア", "総合"]
DETAIL = ["age"]
LONG_Y = {"000040270655": None, "000040270656": None}
LONG_M = ["000040270649", "000040270650", "000040270651"]
AGE = {2019: "000031909558", 2020: "000032048838", 2021: "000032167634", 2022: "000040015264",
       2023: "000040140561", 2024: "000040247212", 2025: "000040409549"}
CITY = {2015: "000031370135", 2019: "000031909555", 2023: "000040140558", 2024: "000040247209", 2025: "000040409546"}
U = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
NAMES = ITEMS + [i.replace("発泡酒・ビール風アルコール飲料", "発泡酒") for i in ITEMS]


def get(sid, kind):
    r = requests.get(U.format(sid, kind), timeout=120)
    r.raise_for_status()
    return r.content


def long_annual(sid):
    rows = list(csv.reader(io.StringIO(get(sid, 1).decode("shift_jis"))))
    yrs = [int(c[:4]) for c in rows[1][8:] if c]
    out = []
    for r in rows[3:]:
        if len(r) > 8 and r[7].strip() in NAMES:
            for j, y in enumerate(yrs):
                out.append((r[7].strip(), y, float(r[8 + j])))
    return out


def long_monthly(sid):
    rows = list(csv.reader(io.StringIO(get(sid, 1).decode("shift_jis"))))
    h = [i for i, r in enumerate(rows) if r and r[0] == "表側連番"][0]
    years, cur = [], None
    for c in rows[h - 2][8:]:
        if "年" in c:
            cur = int(c.strip()[:4])
        years.append(cur)
    months = [int(x.strip().replace("月", "")) for x in rows[h][8:] if x.strip()]
    out = []
    for r in rows[h + 1:]:
        if len(r) > 8 and r[7].strip() in NAMES:
            for j, v in enumerate(r[8:8 + len(months)]):
                if v.strip():
                    out.append((r[7].strip(), years[j], months[j], float(v)))
    return out


if __name__ == "__main__":
    a = sum((long_annual(s) for s in LONG_Y), [])
    m = pd.DataFrame(sum((long_monthly(s) for s in LONG_M), []), columns=["item", "year", "month", "value"])
    y25 = m[m.year == 2025].groupby("item").value.sum().reset_index().assign(year=2025)
    ann = pd.concat([pd.DataFrame(a, columns=["item", "year", "value"]), y25[["item", "year", "value"]]])
    ann.to_csv(DATA / "kakei_annual.csv", index=False)
    m.to_csv(DATA / "kakei_monthly.csv", index=False)
    det = []
    for kind, ids in (("age", AGE), ("city", CITY)):
        if kind not in DETAIL:
            continue
        for y, sid in ids.items():
            p = DATA / f"_tmp_{sid}"
            p.write_bytes(get(sid, 0))
            sheets = [0] if kind == "age" or y == 2015 else ["二人・全国，地方等", "二人・市別"]
            d = pd.concat([parse(p, s) for s in sheets]).assign(year=y, kind=kind)
            det.append(d[d.item.isin(NAMES + ["世帯人員", "世帯数分布(抽出率調整)", "集計世帯数"])
                         & d.metric.isin(["支出金額", "購入数量", "平均価格"])])
            p.unlink()
    if det:
        pd.concat(det).to_csv(DATA / "kakei_detail.csv", index=False)
    c = pd.read_csv("https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
                    "F209_prices_household_series_part1/data/cpi_items_annual.csv")
    c[["year"] + [x for x in c.columns if x.split("|")[0] in CPI_ITEMS]].to_csv(DATA / "cpi_annual.csv", index=False)
    print("done")
