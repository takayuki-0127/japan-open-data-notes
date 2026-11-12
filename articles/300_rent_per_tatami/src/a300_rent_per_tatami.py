"""300 家賃は、広さあたりでどれだけ違うのか（住宅・土地統計調査 時系列 第34-1表・第36表）

- 1か月当たり家賃と1畳当たり家賃の推移（全国、所有の関係別、1973〜2023年）
- 1か月の家賃の伸びを「1畳当たり家賃」と「広さ（畳数）」に分ける（畳数 = 家賃 ÷ 1畳当たり家賃、で求める近似）
- 1畳当たり家賃の分布（全国の借家・専用住宅、1993・2023年）：階級データから中央値などを線形補間で求める
- 3大都市圏とそれ以外（全国から3大都市圏を引いたもの）の分布の違い（都道府県の順位づけはしない）
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, rows, num, year_from_label, save_json, savefig, setup_font, DATA

setup_font()
D = load()

# --- 第34-1表 ---
R = rows(D["t072__034_1"])
COLS = ["総数", "専用住宅", "公営の借家", "UR・公社の借家", "民営借家（木造・設備専用）", "民営借家（木造・設備共用）",
        "民営借家（非木造）", "給与住宅", "店舗その他の併用住宅", "農林漁業併用住宅"]
recs, sect = [], None
for r in R:
    if "(その１" in r[1]: sect = "rent_month"
    elif "(その２" in r[1]: sect = "rent_tatami"
    elif r[1].strip().startswith("増減"): sect = None
    if sect and year_from_label(r[1]) and r[2].isdigit() and len(r[2]) == 4:
        recs.append(dict(sect=sect, year=int(r[2]), **dict(zip(COLS, [num(x) for x in r[3:13]]))))
t = pd.DataFrame(recs).drop_duplicates(["sect", "year"])
t.to_csv(os.path.join(DATA, "rent_by_tenure_long.csv"), index=False)
M = t[t.sect == "rent_month"].set_index("year"); T = t[t.sect == "rent_tatami"].set_index("year")
assert len(M) == 11 and len(T) == 11, (len(M), len(T))

tat = (M["専用住宅"] / T["専用住宅"])          # 1住宅当たりの畳数（近似、専用住宅の借家）
def dec(a, b, col="専用住宅"):
    m = np.log(M.loc[b, col] / M.loc[a, col]); p = np.log(T.loc[b, col] / T.loc[a, col])
    return dict(period=f"{a}-{b}", month_ratio=round(M.loc[b, col] / M.loc[a, col], 3), tatami_rent_ratio=round(T.loc[b, col] / T.loc[a, col], 3),
                share_from_price=round(p / m * 100, 1), share_from_size=round((m - p) / m * 100, 1),
                implied_tatami=(round(M.loc[a, col] / T.loc[a, col], 2), round(M.loc[b, col] / T.loc[b, col], 2)))
decs = [dec(1993, 2023), dec(1973, 1993), dec(2018, 2023), dec(1998, 2018)]

# --- 第36表（1畳当たり家賃の分布） ---
EDGES = [500, 750, 1000, 1250, 1500, 1750, 2000, 2250, 2500, 2750, 3000, 3500, 4000, 5000, 6000, 8000]
def area_rows(sheet):
    R = rows(D[sheet]); out = {}
    for r in R:
        key = None
        if "Japan" in r[:5]: key = "全国"
        eng = (r[2] + " " + r[3]).lower()
        if eng.startswith("keihin") or "kanto" in eng: key = "関東大都市圏"     # 古い調査では「京浜葉大都市圏」
        elif "chukyo" in eng: key = "中京大都市圏"
        elif "keihanshin" in eng or "kinki" in eng: key = "近畿大都市圏"         # 古い調査では「京阪神大都市圏」
        if key and key not in out:
            i = next(i for i, c in enumerate(r) if num(c) is not None and i >= 3 and not (c.isdigit() and len(c) == 2))
            vals = [num(x) for x in r[i:i + 21]]
            out[key] = vals
    return out
def to_classes(v):
    # v: 総数, [0円 or 50円未満], [1〜500 or 50〜500], 500〜750, …, 8000以上, 不詳
    tot = v[0]; low = (v[1] or 0) + (v[2] or 0); mid = v[3:19]; top = v[18]; nr = v[19]
    counts = [low] + v[3:18] + [top]
    return tot, counts, nr
def quantile(counts, q):
    bounds = [0] + EDGES + [10000]   # 8000円以上は 8,000〜10,000 として扱う（中央値には影響しない）
    n = sum(counts); target = q * n; cum = 0
    for i, c in enumerate(counts):
        if cum + c >= target:
            return bounds[i] + (target - cum) / c * (bounds[i + 1] - bounds[i])
        cum += c
dist = {}
for sheet in sorted(k for k in D if k.startswith("t075__")):
    y = year_from_label(sheet.split("__")[1])
    ar = area_rows(sheet)
    res = {}
    for nm, v in ar.items():
        tot, cnt, nr = to_classes(v)
        assert abs(sum(cnt) + (nr or 0) - tot) <= 300, (sheet, nm, sum(cnt), nr, tot)
        res[nm] = dict(total=tot, counts=cnt)
    # 3大都市圏以外 = 全国 − 3大都市圏
    if all(k in res for k in ("全国", "関東大都市圏", "中京大都市圏", "近畿大都市圏")):
        res["3大都市圏"] = dict(total=sum(res[k]["total"] for k in ("関東大都市圏", "中京大都市圏", "近畿大都市圏")),
                           counts=list(np.sum([res[k]["counts"] for k in ("関東大都市圏", "中京大都市圏", "近畿大都市圏")], axis=0)))
        res["3大都市圏以外"] = dict(total=res["全国"]["total"] - res["3大都市圏"]["total"],
                             counts=list(np.array(res["全国"]["counts"]) - np.array(res["3大都市圏"]["counts"])))
    dist[y] = res
qtab = []
for y, res in sorted(dist.items()):
    for nm, d in res.items():
        c = d["counts"]; n = sum(c)
        qtab.append(dict(year=y, area=nm, n=n, p10=round(quantile(c, .1)), p25=round(quantile(c, .25)), p50=round(quantile(c, .5)), p75=round(quantile(c, .75)), p90=round(quantile(c, .9)),
                         share_ge8000=round(c[16] / n * 100, 1),
                         share_ge5000=round(sum(c[14:]) / n * 100, 1), share_lt1000=round(sum(c[:3]) / n * 100, 1)))
qtab = pd.DataFrame(qtab); qtab.to_csv(os.path.join(DATA, "rent_per_tatami_quantiles.csv"), index=False)
def q(y, a): return qtab[(qtab.year == y) & (qtab.area == a)].iloc[0].to_dict()

out = dict(
    month={int(y): dict(総数=M.loc[y, "総数"], 公営=M.loc[y, "公営の借家"], UR=M.loc[y, "UR・公社の借家"], 民営非木造=M.loc[y, "民営借家（非木造）"], 給与=M.loc[y, "給与住宅"]) for y in [1993, 2003, 2013, 2018, 2023]},
    tatami={int(y): dict(総数=T.loc[y, "総数"], 公営=T.loc[y, "公営の借家"], UR=T.loc[y, "UR・公社の借家"], 民営木造専用=T.loc[y, "民営借家（木造・設備専用）"], 民営非木造=T.loc[y, "民営借家（非木造）"], 給与=T.loc[y, "給与住宅"]) for y in [1993, 2003, 2013, 2018, 2023]},
    ratio_private_nonwood_to_public={int(y): round(T.loc[y, "民営借家（非木造）"] / T.loc[y, "公営の借家"], 2) for y in [1993, 2003, 2013, 2023]},
    decomposition=decs,
    metro_median_ratio={int(y): round(q(y, "3大都市圏")["p50"] / q(y, "3大都市圏以外")["p50"], 2) for y in sorted(dist)},
    implied_tatami={int(y): round(v, 2) for y, v in tat.items()},
    quantiles={f"{int(r.year)}_{r.area}": dict(p10=r.p10, p25=r.p25, p50=r.p50, p75=r.p75, p90=r.p90, share_ge8000=r.share_ge8000, share_ge5000=r.share_ge5000, share_lt1000=r.share_lt1000, n=r.n) for r in qtab.itertuples() if r.year in (1993, 2003, 2013, 2023)},
)
save_json("a300_main.json", out)

# --- 図 ---
fig, ax = plt.subplots(figsize=(7.5, 4.4))
for col, lab, c in [("民営借家（非木造）", "民営借家（非木造）", "#9467bd"), ("UR・公社の借家", "UR・公社の借家", "#17becf"), ("総数", "借家全体", "black"),
                    ("民営借家（木造・設備専用）", "民営借家（木造）", "#a6761d"), ("給与住宅", "給与住宅", "#7f7f7f"), ("公営の借家", "公営の借家", "#8c564b")]:
    s = T[col].dropna()
    ax.plot(s.index, s, marker="o", ms=3.2, lw=2.3 if col == "総数" else 1.6, color=c)
    dy = {"総数": 90, "民営借家（木造・設備専用）": -90}.get(col, 0)
    ax.text(2024, s.loc[2023] + dy, f"{lab} {s.loc[2023]:,.0f}円", fontsize=8.3, color=c, va="center")
ax.set_xlim(1971, 2037); ax.set_ylabel("1畳当たりの家賃（円／月）")
ax.set_title("1畳当たりの家賃は1990年代に伸びが止まり、2018→23年に10%上がった", fontsize=10.5)
ax.text(1972, 120, "出典：総務省「住宅・土地統計調査」時系列表 第34-1表（全国）。民営借家（非木造）は1988年から", fontsize=7.5, color="gray")
ax.set_ylim(0, 4500)
savefig(fig, "a300_rent_per_tatami.png")

fig, ax = plt.subplots(figsize=(7.6, 4.3))
bounds = np.array([0] + EDGES, float)                 # 8,000円以上は幅が決まらないので図では別に書く
for y, c in [(1993, "#9ecae1"), (2023, "#08519c")]:
    cnt = np.array(dist[y]["全国"]["counts"], float); share = cnt / cnt.sum() * 100
    dens = share[:-1] / (np.diff(bounds) / 250)     # 250円の幅あたりの割合にそろえる
    ax.stairs(dens, bounds, color=c, lw=2, label=f"{y}年（中央値 {q(y, '全国')['p50']:,}円、8,000円以上 {share[-1]:.1f}%）")
ax.set_xlim(0, 8000); ax.set_xlabel("1畳当たりの家賃（円／月）")
ax.set_ylabel("250円の幅あたりの割合（%）")
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
ax.set_title("1畳当たりの家賃の分布は、30年で全体に高い方へ動いた", fontsize=10.5)
savefig(fig, "a300_distribution.png")

fig, ax = plt.subplots(figsize=(7.2, 4.2))
yrs = sorted(dist)
for nm, c in [("3大都市圏", "#d62728"), ("3大都市圏以外", "#1f77b4"), ("全国", "black")]:
    p50 = [q(y, nm)["p50"] for y in yrs]; p10 = [q(y, nm)["p25"] for y in yrs]; p90 = [q(y, nm)["p75"] for y in yrs]
    ax.plot(yrs, p50, marker="o", color=c, lw=2, label=f"{nm}（中央値）")
    if nm != "全国":
        ax.fill_between(yrs, p10, p90, color=c, alpha=0.12)
ax.set_ylabel("1畳当たりの家賃（円／月）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("3大都市圏の中央値は、それ以外の1.5〜1.7倍で推移（帯は25〜75%の範囲）", fontsize=10)
ax.text(1993, 700, "3大都市圏の範囲は調査年ごとの定義による（古い調査では京浜葉・京阪神大都市圏）", fontsize=7.3, color="gray")
savefig(fig, "a300_metro.png")
