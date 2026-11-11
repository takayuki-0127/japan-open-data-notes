"""A283 食料品の輸出は、どの品目で伸びたのか
統計品別表（輸出、9桁）のうち、HS第1〜23類（食料品・飲料・飼料。たばこの第24類は除く）を食料品とした。
品目は HS の4桁（項）にまとめ、2015→2025年の増加額を品目ごとに分ける。
数量の単位がそろう品目は、増加額を「量」「ドルに直した単価」「為替（ドル円）」に分ける（対数平均の重み、A281 と同じ方法）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font, note

setup_font()
F = pd.read_csv(DATA / "food_exports_hs9.csv", dtype={"HS": str})
ALL = pd.read_csv(DATA / "all_exports_total.csv").set_index("year")["all_exports"]
FX = pd.read_csv(DATA / "usdjpy_annual.csv").set_index("year")["usdjpy"]
MAP = pd.read_csv(DATA / "hs9_to_gaikyo_export.csv", dtype=str).fillna("")
H4 = {"0201": "牛肉（生鮮・冷蔵）", "0202": "牛肉（冷凍）", "0301": "生きている魚（錦鯉など）", "0303": "冷凍魚",
      "0304": "魚のフィレ・すり身など", "0307": "軟体動物（ほたて貝など）", "0902": "茶（緑茶など）",
      "1605": "甲殻類・軟体動物の調製品", "1905": "パン・菓子類", "2101": "コーヒー・茶のエキスなど",
      "2103": "ソース・調味料", "2106": "その他の調製食料品", "2202": "清涼飲料水など", "2203": "ビール",
      "2206": "清酒などの発酵酒", "2208": "ウイスキーなどの蒸留酒", "1006": "米", "0808": "りんご・なしなど",
      "1209": "まく用の種", "0508": "さんご・貝殻など", "2306": "油かす", "0602": "生きている植物（苗木など）",
      "2309": "飼料（ペットフードなど）", "1704": "砂糖菓子", "0407": "鳥卵（殻付き）", "1806": "チョコレート菓子",
      "0302": "生鮮・冷蔵の魚", "1901": "麦芽エキス・調製食料品（粉ミルクなど）", "2005": "調製野菜", "2009": "果汁", "1604": "魚の調製品（缶詰など）", "1518": "加工した油脂", "1902": "めん類",
      "0306": "甲殻類（かになど）", "1001": "小麦", "0801": "ナッツ類（ココナッツなど）", "2104": "スープ"}
GROUP = [("01", "05", "畜産物・水産物（生鮮・冷凍）"), ("06", "15", "農産物（野菜・果物・穀物・茶・油脂など）"),
         ("16", "21", "加工食品（調製品・菓子・調味料など）"), ("22", "22", "飲料（酒・清涼飲料水）"), ("23", "23", "飼料など")]


def grp(hs):
    c = hs[:2]
    return next(n for a, b, n in GROUP if a <= c <= b)


F["h4"] = F.HS.str[:4]; F["group"] = F.HS.map(grp)
tot = F.groupby("year").value.sum()
main = {"food_oku": (tot / 1e5).round(1).to_dict(), "food_share_of_all_exports": (tot / ALL).round(5).to_dict(),
        "growth_2015_2025": tot[2025] / tot[2015], "growth_2015_2020": tot[2020] / tot[2015], "growth_2020_2025": tot[2025] / tot[2020]}
h = F.pivot_table(index="h4", columns="year", values="value", aggfunc="sum").fillna(0) / 1e5  # 億円
h["d"] = h[2025] - h[2015]; h["name"] = [H4.get(k, "") for k in h.index]
h = h.sort_values("d", ascending=False); h.round(1).to_csv(RES / "by_hs4_oku.csv")
dsum = tot[2025] / 1e5 - tot[2015] / 1e5
main["n_hs4"] = int((h[[2015, 2025]].sum(axis=1) > 0).sum())
main["top10_share_of_increase"] = float(h.d.head(10).sum() / dsum)
main["top20_share_of_increase"] = float(h.d.head(20).sum() / dsum)
main["n_hs4_decreased"] = int((h.d < 0).sum())
main["top15"] = [(k, r["name"], round(r[2015], 1), round(r[2020], 1), round(r[2025], 1), round(r.d, 1)) for k, r in h.head(15).iterrows()]
main["bottom5"] = [(k, r["name"], round(r[2015], 1), round(r[2025], 1), round(r.d, 1)) for k, r in h.sort_values("d").head(5).iterrows()]
g = F.pivot_table(index="group", columns="year", values="value", aggfunc="sum") / 1e5
g.round(1).to_csv(RES / "by_group_oku.csv"); main["by_group"] = g.round(1).to_dict(orient="index")
# 酒類（2203・2204・2205・2206・2208）
alc = h.loc[[k for k in ["2203", "2204", "2205", "2206", "2208"] if k in h.index]]
main["alcohol"] = {"2015": float(alc[2015].sum()), "2025": float(alc[2025].sum())}


def decompose(y0, y1):
    a = F[F.year == y0]; b = F[F.year == y1]
    m = a.merge(b, on="HS", suffixes=("0", "1"))
    ok = (m.value0 > 0) & (m.value1 > 0) & (m.q20 > 0) & (m.q21 > 0) & (m.unit20 == m.unit21)
    m = m[ok].copy()
    w = np.where(np.isclose(m.value0, m.value1), m.value0, (m.value1 - m.value0) / (np.log(m.value1) - np.log(m.value0)))
    m["d_qty"] = w * np.log(m.q21 / m.q20); m["d_fx"] = w * np.log(FX[y1] / FX[y0])
    m["d_usd"] = w * np.log((m.value1 / m.q21) / (m.value0 / m.q20)) - m.d_fx
    m["dv"] = m.value1 - m.value0; m["h4"] = m.HS.str[:4]
    t0, t1 = tot[y0], tot[y1]
    s = {"matched_share_value1": float(m.value1.sum() / t1), "matched_dv_oku": float(m.dv.sum() / 1e5), "all_dv_oku": float((t1 - t0) / 1e5),
         "qty_oku": float(m.d_qty.sum() / 1e5), "usd_oku": float(m.d_usd.sum() / 1e5), "fx_oku": float(m.d_fx.sum() / 1e5),
         "usdjpy": [float(FX[y0]), float(FX[y1])]}
    return s, m


s1525, m1525 = decompose(2015, 2025); s2025, m2025 = decompose(2020, 2025)
main["decomp_2015_2025"] = s1525; main["decomp_2020_2025"] = s2025
bh = m2025.groupby("h4")[["dv", "d_qty", "d_usd", "d_fx"]].sum() / 1e5
bh["name"] = [H4.get(k, "") for k in bh.index]; bh = bh.sort_values("dv", ascending=False)
bh.round(1).to_csv(RES / "decomp_by_hs4_2020_2025_oku.csv")
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：食料品の輸出額（グループ別）
fig, ax = plt.subplots(figsize=(8.2, 4.8))
cols = ["#1b9e77", "#66a61e", "#e6ab02", "#d95f02", "#7570b3"]
ys = [2015, 2020, 2025]; bottom = np.zeros(3)
for (a, b, n), c in zip(GROUP, cols):
    v = np.array([g.loc[n, y] for y in ys]); ax.bar([str(y) for y in ys], v, bottom=bottom, color=c, label=n, width=0.55); bottom += v
for i, y in enumerate(ys):
    ax.text(i, bottom[i] + 150, f"{bottom[i]:,.0f}億円", ha="center", fontsize=10)
ax.set_ylabel("食料品の輸出額（億円）"); ax.set_ylim(0, bottom.max() * 1.15)
ax.set_title("食料品の輸出（HS第1〜23類）は10年で2.2倍")
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
fig.subplots_adjust(bottom=0.1); note(fig); fig.savefig(FIG / "a283_total.png"); plt.close(fig)

# 図2：増加額の大きい15品目（HS4桁）
t = h.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.4, 5.8))
ax.barh(range(len(t)), t[2025] - t[2020], left=t[2020] - t[2015], color="#d95f02", label="2020→2025年")
ax.barh(range(len(t)), t[2020] - t[2015], color="#7570b3", label="2015→2020年")
for i, (k, r) in enumerate(t.iterrows()):
    ax.text(max(r.d, r[2020] - r[2015]) + 15, i, f"+{r.d:,.0f}億円（{r[2015]:,.0f}→{r[2025]:,.0f}）", va="center", fontsize=8)
ax.set_yticks(range(len(t))); ax.set_yticklabels([f"{r['name']}（{k}）" for k, r in t.iterrows()], fontsize=9)
ax.axvline(0, color="#333", lw=0.8); ax.set_xlabel("2015年からの増加額（億円）")
ax.set_xlim(min(0, (t[2020] - t[2015]).min()) - 50, t.d.max() * 1.6)
ax.set_title("増加額の大きい15品目：茶・酒・牛肉・調味料・ほたて貝")
ax.legend(fontsize=9, frameon=False, loc="lower right")
fig.subplots_adjust(left=0.33, bottom=0.11); note(fig); fig.savefig(FIG / "a283_items.png"); plt.close(fig)

# 図3：量・ドルに直した単価・為替（2020→2025年、数量の単位がそろう品目、上位10品目＋全体）
t = bh.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.4, 5.6))
for i, (k, r) in enumerate(t.iterrows()):
    pos = neg = 0
    for c, nm, col in [("d_qty", "量", "#8c8c8c"), ("d_usd", "ドルに直した単価", "#d95f02"), ("d_fx", "為替（ドル円）", "#1b9e77")]:
        v = r[c]
        if v >= 0:
            ax.barh(i, v, left=pos, color=col, label=nm if i == 0 else None); pos += v
        else:
            ax.barh(i, v, left=neg, color=col, label=nm if i == 0 else None); neg += v
ax.set_yticks(range(len(t))); ax.set_yticklabels([f"{r['name']}（{k}）" for k, r in t.iterrows()], fontsize=9)
ax.axvline(0, color="#333", lw=0.8); ax.set_xlabel("2020→2025年の輸出額の増加（億円）")
s = s2025
ax.set_title(f"2020→2025年：量で伸び、ドルで見た単価は下がった\n（数量の単位がそろう品目の合計：量{s['qty_oku']:+,.0f}億円・ドルに直した単価{s['usd_oku']:+,.0f}億円・為替{s['fx_oku']:+,.0f}億円）", fontsize=10.5)
ax.legend(fontsize=9, frameon=False, loc="lower right")
fig.subplots_adjust(left=0.33, bottom=0.11); note(fig); fig.savefig(FIG / "a283_decomp.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, default=float, indent=0)[:3800])
print(bh.head(12).round(0).to_string())
