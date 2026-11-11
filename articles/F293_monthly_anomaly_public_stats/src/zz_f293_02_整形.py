"""F293 02 整形：3つの統計を「系列 × 月」の長い表にそろえる。

出力 data/series_long.csv：src（S1/S2/S3）, sid（系列の名前）, ym（YYYYMM）, x（値）
"""
import pathlib
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
out = []

# S1 商業動態統計 6業態（百万円）
s1 = pd.read_csv(RAW / "s1_shogyo_6types.csv")
s1["ym"] = s1["ym"].str.replace("-", "").astype(int)
for g, d in s1.groupby("業態"):
    out.append(pd.DataFrame({"src": "S1", "sid": g, "ym": d["ym"], "x": d["販売額_百万円"]}))

# S2 消費者物価 品目（4桁の符号が1000以上＝品目。類・中分類などのまとめは除く）
cpi = pd.read_csv(RAW / "s2_cpi_items_monthly.csv.gz")
cols = [c for c in cpi.columns if "|" in c and int(c.split("|")[1]) >= 1000 and cpi[c].notna().all()]
for c in cols:
    out.append(pd.DataFrame({"src": "S2", "sid": c, "ym": cpi["ym"].astype(int), "x": cpi[c].astype(float)}))

# S3 家計調査 品目別支出（円、二人以上の世帯）
NAMES = ["消費支出", "食料", "酒類", "清酒", "焼酎", "ビール", "ウイスキー", "ワイン",
         "発泡酒・ビール風アルコール飲料", "チューハイ・カクテル", "たばこ"]
recs = []
for blk in RAW.joinpath("kakei_items_monthly_2015_2026.csv").read_text(encoding="utf-8").split("#"):
    lines = [l for l in blk.splitlines() if l.strip()]
    if len(lines) < 3:
        continue
    years, cur = [], None
    for c in lines[1].split(",")[8:]:
        if c.strip():
            cur = int(c.strip().replace("年", ""))
        years.append(cur)
    for l in lines[3:]:
        c = l.split(",")
        name = c[7].strip()
        if name not in NAMES:
            continue
        cnt = {}
        for y, v in zip(years, c[8:]):
            if y is None or v.strip() in ("", "-", "…"):
                continue
            cnt[y] = cnt.get(y, 0) + 1
            recs.append((name, y * 100 + cnt[y], float(v)))
l = RAW.joinpath("kakei_3X7_2025_2026.csv").read_text(encoding="utf-8").splitlines()[1]
for i, v in enumerate([float(v) for v in l.split(",")[8:] if v.strip()]):
    recs.append(("発泡酒・ビール風アルコール飲料", (2025 + i // 12) * 100 + i % 12 + 1, v))
k = pd.DataFrame(recs, columns=["sid", "ym", "x"]).drop_duplicates(["sid", "ym"])
k["src"] = "S3"
out.append(k[["src", "sid", "ym", "x"]])

df = pd.concat(out).sort_values(["src", "sid", "ym"]).reset_index(drop=True)
# 月が途切れていないか
def full(d):
    p = pd.PeriodIndex([f"{v//100}-{v%100:02d}" for v in d.ym], freq="M")
    return len(p) == (p.max() - p.min()).n + 1
chk = df.groupby(["src", "sid"]).apply(full)
df = df[df.set_index(["src", "sid"]).index.isin(chk[chk].index)]
df.to_csv(BASE / "data" / "series_long.csv", index=False, float_format="%.6g")
print(df.groupby("src").agg(series=("sid", "nunique"), first=("ym", "min"), last=("ym", "max"), rows=("x", "size")))
print("途切れて外した系列", (~chk).sum())
