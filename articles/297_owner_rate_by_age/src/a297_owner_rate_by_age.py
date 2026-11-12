"""297 持ち家の割合は、年齢でどう違うのか（住宅・土地統計調査 時系列 第21-1表）

家計を主に支える者の年齢別に、主世帯のうち持ち家に住む割合（持ち家率）を 1978〜2023年で並べる。
- 年齢別の持ち家率の推移、50%を超える年齢（線形補間）
- 生まれ年（5年刻み）ごとに、年齢とともに持ち家率がどう上がったか
- 全体の持ち家率の変化を「年齢構成の変化」と「同じ年齢の中の変化」に分ける（シフト・シェア）
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, rows, num, year_from_label, save_json, savefig, setup_font, DATA

setup_font()
D = load()
R = rows(D["t054__021_1"])

# --- 整形：年 × 年齢 × (総数, 持ち家, 印刷された持ち家率) ---
recs, year = [], None
for r in R:
    lab = r[1]
    y = year_from_label(lab)
    if y and (len(r) > 2 and r[2].isdigit()):
        year = int(r[2]); continue
    if year is None or lab == "":
        continue
    if lab.startswith("1)"):
        break
    tot, own, rent, pct = num(r[4]), num(r[5]), num(r[6]), num(r[12])
    if tot is None:
        continue
    recs.append(dict(year=year, age=lab.replace("　", "").strip(), total=tot, owned=own, rented=rent, pct_printed=pct))
df = pd.DataFrame(recs)
df.to_csv(os.path.join(DATA, "owner_by_age_long.csv"), index=False)

# 5歳刻みにそろえる（1978年以降）。65歳以上はまとめる
def band(a):
    if a == "総数": return "総数"
    if a.startswith("25歳未満"): return "25歳未満"
    if a.startswith("65") or a.startswith("70") or a.startswith("75") or a.startswith("80") or a.startswith("85"):
        return "65歳以上"
    return a
d5 = df[df.year >= 1978].copy()
d5["band"] = d5.age.map(band)
g = d5.groupby(["year", "band"], sort=False)[["total", "owned", "rented"]].sum().reset_index()
g["rate"] = g.owned / g.total * 100
g["rate_known"] = g.owned / (g.owned + g.rented) * 100   # 頑健性：所有の関係「不詳」を分母から除く
BANDS = ["25歳未満", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50～54歳",
         "55～59歳", "60～64歳", "65歳以上"]
piv = g.pivot(index="year", columns="band", values="rate")[["総数"] + BANDS]
piv.round(2).to_csv(os.path.join(DATA, "owner_rate_by_band.csv"))

# 点検：計算した率と印刷された率（小数1桁）の差
chk = df.dropna(subset=["pct_printed"]).copy()
chk["calc"] = chk.owned / chk.total * 100
max_diff = float((chk.calc - chk.pct_printed).abs().max())

# 50%を超える年齢（各帯の中央の年齢で線形補間）
MID = {"25歳未満": 22, "25～29歳": 27, "30～34歳": 32, "35～39歳": 37, "40～44歳": 42, "45～49歳": 47,
       "50～54歳": 52, "55～59歳": 57, "60～64歳": 62, "65歳以上": 70}
def cross50(row):
    xs = [MID[b] for b in BANDS[:-1]]; ys = [row[b] for b in BANDS[:-1]]
    for i in range(len(xs) - 1):
        if ys[i] < 50 <= ys[i + 1]:
            return xs[i] + (50 - ys[i]) / (ys[i + 1] - ys[i]) * (xs[i + 1] - xs[i])
    return None
age50 = {int(y): round(cross50(piv.loc[y]), 1) for y in piv.index}

# 生まれ年（5年刻み）ごとの曲線：調査年 y、年齢帯 [a, a+4] → 生まれ年 y-a-4 〜 y-a
coh = []
for y in piv.index:
    for b in BANDS[1:-1]:
        a = int(b[:2]); coh.append(dict(cohort=f"{y-a-4}〜{y-a}年生まれ", born=y - a - 2, year=int(y), age=MID[b], rate=piv.loc[y, b]))
coh = pd.DataFrame(coh)
coh.round(3).to_csv(os.path.join(DATA, "owner_rate_by_cohort.csv"), index=False)
# 40～44歳の時点での持ち家率（生まれ年別）
at40 = coh[coh.age == 42].sort_values("born")[["cohort", "year", "rate"]]

# シフト・シェア：1983 → 2023 の全体の率の変化
def shiftshare(y0, y1, col="rate"):
    a = g[g.year == y0].set_index("band"); b = g[g.year == y1].set_index("band")
    w0 = a.loc[BANDS, "total"] / a.loc[BANDS, "total"].sum(); w1 = b.loc[BANDS, "total"] / b.loc[BANDS, "total"].sum()
    r0 = a.loc[BANDS, col]; r1 = b.loc[BANDS, col]
    act0 = float((w0 * r0).sum()); act1 = float((w1 * r1).sum())
    comp = float(((w1 - w0) * (r0 + r1) / 2).sum())      # 年齢構成の変化の分（中点の率で重み付け）
    within = float(((r1 - r0) * (w0 + w1) / 2).sum())    # 同じ年齢の中の変化の分
    only_comp = float((w1 * r0).sum())                    # 年齢別の率が y0 のまま、構成だけ y1
    return dict(y0=y0, y1=y1, rate0=round(act0, 2), rate1=round(act1, 2), change=round(act1 - act0, 2),
                composition=round(comp, 2), within=round(within, 2), rate_if_only_composition=round(only_comp, 2),
                share65_0=round(float(w0["65歳以上"]) * 100, 1), share65_1=round(float(w1["65歳以上"]) * 100, 1))
ss = {f"{a}-{b}": shiftshare(a, b) for a, b in [(1983, 2023), (1983, 2003), (2003, 2023), (1978, 2023)]}
ss_known = {f"{a}-{b}": shiftshare(a, b, "rate_known") for a, b in [(1983, 2023), (2003, 2023)]}
pk = g.pivot(index="year", columns="band", values="rate_known")
tenure_unknown_share = {int(y): round(float(1 - (g[(g.year == y) & (g.band == "総数")].owned.iloc[0] + g[(g.year == y) & (g.band == "総数")].rented.iloc[0]) / g[(g.year == y) & (g.band == "総数")].total.iloc[0]) * 100, 1) for y in [1983, 2003, 2023]}

out = dict(
    max_abs_diff_calc_vs_printed=round(max_diff, 3),
    rate_by_band={str(int(y)): {k: round(v, 1) for k, v in piv.loc[y].items()} for y in [1983, 1993, 2003, 2013, 2023]},
    age_cross_50=age50,
    at_40_44_by_cohort=[dict(cohort=r.cohort, year=int(r.year), rate=round(r.rate, 1)) for r in at40.itertuples()],
    shift_share=ss,
    shift_share_known_tenure=ss_known,
    tenure_unknown_share_pct=tenure_unknown_share,
    rate_known_2023={k: round(v, 1) for k, v in pk.loc[2023].items()},
    rate_known_1983={k: round(v, 1) for k, v in pk.loc[1983].items()},
    change_1983_2023_by_band={b: round(piv.loc[2023, b] - piv.loc[1983, b], 1) for b in BANDS},
)
save_json("a297_main.json", out)

# --- 図 ---
cols = {"30～34歳": "#1f77b4", "35～39歳": "#2ca02c", "40～44歳": "#ff7f0e", "45～49歳": "#d62728",
        "50～54歳": "#9467bd", "65歳以上": "#7f7f7f", "総数": "black"}
fig, ax = plt.subplots(figsize=(7.5, 4.5))
for b, c in cols.items():
    ax.plot(piv.index, piv[b], marker="o", ms=3.5, color=c, lw=2.4 if b == "総数" else 1.6, label=b)
    dy = {"50～54歳": 3.0, "総数": 0.6, "45～49歳": -2.2}.get(b, 0)
    ax.text(2023.6, piv.loc[2023, b] + dy, f"{b} {piv.loc[2023, b]:.0f}%", va="center", fontsize=8.5, color=c)
ax.set_xlim(1976, 2032); ax.set_ylim(0, 90)
ax.set_ylabel("持ち家に住む主世帯の割合（%）")
ax.set_title("全体の持ち家率は60%前後のまま、30〜50代では下がり続けた", fontsize=11)
ax.text(1977, 3, "家計を主に支える者の年齢別。出典：総務省「住宅・土地統計調査」時系列表 第21-1表", fontsize=7.5, color="gray")
savefig(fig, "a297_rate_by_age.png")

fig, ax = plt.subplots(figsize=(7.5, 4.5))
show = coh[coh.born.isin(sorted(coh.born.unique()))]
sel = [1941, 1951, 1961, 1971, 1981, 1991]
cmap = plt.get_cmap("viridis")
for i, bn in enumerate(sel):
    s = coh[coh.born == bn].sort_values("age")
    if len(s) == 0: continue
    ax.plot(s.age, s.rate, marker="o", ms=3.5, color=cmap(i / (len(sel) - 1)), lw=1.8, label=s.cohort.iloc[0])
ax.axhline(50, color="gray", lw=0.8, ls=":")
ax.set_xlabel("年齢（5歳刻みの帯の中央）"); ax.set_ylabel("持ち家率（%）")
ax.set_title("後に生まれた人ほど、同じ年齢での持ち家率が低い", fontsize=11)
ax.legend(fontsize=8.5, frameon=False, loc="lower right")
savefig(fig, "a297_cohort.png")

s = ss["1983-2023"]
fig, ax = plt.subplots(figsize=(6.8, 4.0))
labs = ["実際の変化", "年齢構成の変化の分", "同じ年齢の中の変化の分"]
vals = [s["change"], s["composition"], s["within"]]
ax.barh(labs[::-1], vals[::-1], color=["#2ca02c", "#7f7f7f", "#555555"][::-1])
for i, v in enumerate(vals[::-1]):
    if v >= 0:
        ax.text(v + 0.3, i, f"{v:+.1f}ポイント", va="center", ha="left", fontsize=10)
    else:
        ax.text(v + 0.3, i, f"{v:+.1f}ポイント", va="center", ha="left", fontsize=10, color="white")
ax.axvline(0, color="black", lw=0.8)
ax.set_xlim(-13, 13)
ax.set_xlabel("1983→2023年の持ち家率の変化（ポイント）")
ax.set_title("高齢の世帯が増えた分が、年齢ごとの低下をほぼ打ち消した", fontsize=11)
savefig(fig, "a297_shiftshare.png")
