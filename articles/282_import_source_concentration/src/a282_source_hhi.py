"""A282 輸入元が少数の国に偏っている品目はどれか
概況品別国別表（輸入）で、品目ごとに輸入元の国の集中度（HHI：国ごとの割合の2乗の和、0〜1）を測る。
主な分析は概況品の5桁（172品目）。3桁（57品目）でも同じ計算をして、品目の細かさで結論が変わるかを見る。
HHI 0.25 超を「偏りが強い」とした（米司法省の企業結合ガイドラインの目安 2,500 を 0〜1 に直した値。目安であって基準ではない）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font, note

setup_font()
A = pd.read_csv(DATA / "imports_gaikyo_country_2015_2025.csv", dtype={"Commodity": str, "Country": str})
NAMES = pd.read_csv(DATA / "gaikyo_import_names.csv", dtype=str).set_index("code")["name"]
CN = pd.read_csv(DATA / "country_names.csv", dtype=str).set_index("Country")["country_name"]
TH = 0.25


def hhi_table(y, L):
    a = A[(A.year == y) & (A.Commodity.str.len() == L)].copy().reset_index(drop=True)
    a["sh"] = a.value / a.groupby("Commodity").value.transform("sum")
    h = a.groupby("Commodity").agg(value=("value", "sum"), hhi=("sh", lambda x: (x ** 2).sum()),
                                   top_share=("sh", "max"), n_countries=("Country", "nunique"))
    top = a.loc[a.groupby("Commodity").sh.idxmax()].set_index("Commodity").Country
    h["top_country"] = top.map(CN)
    h["n_for_80"] = a.sort_values("sh", ascending=False).groupby("Commodity").sh.apply(lambda s: int(np.searchsorted(s.cumsum().values, 0.8) + 1))
    h["name"] = [NAMES.get(c, "") for c in h.index]
    return h


def total(y):
    return A[(A.year == y) & (A.Commodity.str.len() == 1)].value.sum()


main = {}
T = {}
for y in (2015, 2025):
    for L in (3, 5):
        h = hhi_table(y, L); T[(y, L)] = h
        main[f"{y}_L{L}"] = {"items": len(h), "coverage": h.value.sum() / total(y),
                              "wmean_hhi": float((h.hhi * h.value).sum() / h.value.sum()),
                              "median_hhi": float(h.hhi.median()),
                              "share_value_hhi_over": float(h.value[h.hhi > TH].sum() / h.value.sum()),
                              "n_items_hhi_over": int((h.hhi > TH).sum()),
                              "share_value_top_over_half": float(h.value[h.top_share > 0.5].sum() / h.value.sum())}
T[(2025, 5)].sort_values("value", ascending=False).round(4).to_csv(RES / "hhi_gaikyo5_2025.csv")
T[(2015, 5)].sort_values("value", ascending=False).round(4).to_csv(RES / "hhi_gaikyo5_2015.csv")
T[(2025, 3)].sort_values("value", ascending=False).round(4).to_csv(RES / "hhi_gaikyo3_2025.csv")

# 2015→2025年：重み（輸入額の構成）とHHIのどちらが効いたか
a, b = T[(2015, 5)], T[(2025, 5)]
m = a[["value", "hhi", "top_country"]].join(b[["value", "hhi", "top_country", "name"]], lsuffix="15", rsuffix="25", how="inner")
f = lambda v, h: float(v[h > TH].sum() / v.sum())
main["decomp_L5"] = {"w15_h15": f(m.value15, m.hhi15), "w15_h25": f(m.value15, m.hhi25),
                     "w25_h15": f(m.value25, m.hhi15), "w25_h25": f(m.value25, m.hhi25), "items_both": len(m)}
cu = m[(m.hhi15 <= TH) & (m.hhi25 > TH)].sort_values("value25", ascending=False)
cd = m[(m.hhi15 > TH) & (m.hhi25 <= TH)].sort_values("value25", ascending=False)
main["crossed_up"] = [(r["name"], round(r.value25 / 1e9, 2), round(r.hhi15, 3), round(r.hhi25, 3)) for _, r in cu.iterrows()]
main["crossed_down"] = [(r["name"], round(r.value25 / 1e9, 2), round(r.hhi15, 3), round(r.hhi25, 3)) for _, r in cd.iterrows()]
main["crossed_up_share_2025"] = float(cu.value25.sum() / m.value25.sum())
main["crossed_down_share_2025"] = float(cd.value25.sum() / m.value25.sum())
m.round(4).to_csv(RES / "hhi_change_2015_2025_L5.csv")
# 1兆円以上の品目
big = b[b.value > 1e9].sort_values("hhi", ascending=False)
main["big_items"] = [(r["name"], round(r.value / 1e9, 2), round(r.hhi, 3), round(r.top_share, 3), r.top_country, int(r.n_for_80)) for _, r in big.iterrows()]
# 原油の国別（説明用）
oil = A[(A.Commodity == "30301")].copy()
oil["sh"] = oil.value / oil.groupby("year").value.transform("sum"); oil["country"] = oil.Country.map(CN)
main["crude_top5"] = {int(y): [(r.country, round(r.sh, 3)) for _, r in g.nlargest(5, "sh").iterrows()] for y, g in oil.groupby("year")}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：品目ごとの輸入額とHHI（2025年、5桁）
fig, ax = plt.subplots(figsize=(8.4, 5.2))
x = b.value / 1e5  # 億円
ax.scatter(x, b.hhi, s=np.sqrt(x) * 1.2 + 4, color=np.where(b.hhi > TH, "#d95f02", "#7570b3"), alpha=0.65, edgecolor="none")
ax.axhline(TH, color="#555", ls="--", lw=0.9); ax.text(x.min(), TH + 0.015, "HHI 0.25（目安）", fontsize=8.5, color="#555")
ax.set_xscale("log"); ax.set_xlabel("2025年の輸入額（億円、対数目盛）"); ax.set_ylabel("輸入元の集中度（HHI）")
OFF = {"00907": (-160, 0), "81309": (-200, 4), "70307": (-215, 35), "30101": (-235, 24), "70105": (-260, 18),
       "30301": (-285, 10), "70311": (-270, -4), "30501": (-190, -20)}
for c, (dx, dy) in OFF.items():
    if c in b.index:
        r = b.loc[c]
        ax.annotate(f"{r['name']}（{r.top_country[:7]} {r.top_share*100:.0f}%）", (r.value / 1e5, r.hhi), fontsize=8,
                    xytext=(dx, dy), textcoords="offset points", arrowprops=dict(arrowstyle="-", color="#888", lw=0.6))
ax.set_title("輸入元の集中度：大きな品目にも偏りの強いものがある（2025年、172品目）")
fig.subplots_adjust(bottom=0.14); note(fig); fig.savefig(FIG / "a282_scatter.png"); plt.close(fig)

# 図2：偏りが強い品目の輸入額の割合（2015・2025年、品目の細かさ別、重みを固定した場合）
fig, ax = plt.subplots(figsize=(8.2, 4.6))
labels = ["5桁 2015年", "5桁 2025年", "5桁 2025年\n（重みは2015年）", "3桁 2015年", "3桁 2025年"]
vals = [main["2015_L5"]["share_value_hhi_over"], main["2025_L5"]["share_value_hhi_over"], main["decomp_L5"]["w15_h25"],
        main["2015_L3"]["share_value_hhi_over"], main["2025_L3"]["share_value_hhi_over"]]
cols = ["#7570b3", "#d95f02", "#fdb863", "#b2abd2", "#e08214"]
ax.bar(range(5), np.array(vals) * 100, color=cols)
for i, v in enumerate(vals):
    ax.text(i, v * 100 + 1, f"{v*100:.0f}%", ha="center", fontsize=10)
ax.set_xticks(range(5)); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("HHI 0.25超の品目の輸入額の割合（%）"); ax.set_ylim(0, 70)
ax.set_title("偏りが強い品目の割合は、品目の細かさで向きまで変わる")
fig.subplots_adjust(bottom=0.2); note(fig); fig.savefig(FIG / "a282_share.png"); plt.close(fig)

# 図3：0.25の線を越えた品目（2025年の輸入額の大きい順）
sel = pd.concat([cu[cu.value25 >= 1.5e8].assign(dir="up"), cd[cd.value25 >= 1.5e8].assign(dir="down")]).sort_values("value25")
fig, ax = plt.subplots(figsize=(8.4, 5.4))
for i, (c, r) in enumerate(sel.iterrows()):
    col = "#d95f02" if r.dir == "up" else "#1b9e77"
    ax.annotate("", xy=(r.hhi25, i), xytext=(r.hhi15, i), arrowprops=dict(arrowstyle="->", color=col, lw=1.6))
    ax.plot(r.hhi15, i, "o", color="#999", ms=4)
ax.set_yticks(range(len(sel))); ax.set_yticklabels([f"{r['name']}（{r.value25/1e9:.1f}兆円）" for _, r in sel.iterrows()], fontsize=9)
ax.axvline(TH, color="#555", ls="--", lw=0.9); ax.set_xlim(0.12, 0.45)
ax.set_xlabel("輸入元の集中度（HHI）　灰色の点＝2015年、矢印の先＝2025年")
ax.set_title("0.25の線を越えた品目（2025年に1,500億円以上）：上がった（橙）・下がった（緑）", fontsize=11)
fig.subplots_adjust(left=0.33, bottom=0.14); note(fig); fig.savefig(FIG / "a282_cross.png"); plt.close(fig)
print(json.dumps({k: v for k, v in main.items() if k not in ("big_items",)}, ensure_ascii=False, default=float, indent=0)[:3500])
for r in main["big_items"]: print(r)
