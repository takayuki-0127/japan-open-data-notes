"""A284 港ごとの輸出は、何に偏っているのか
概況品別税関一覧表（輸出）で、税関の事務所（出張所などをまとめた上3桁のコード）ごとに、輸出する品物の偏りを測る。
偏りの物差しは概況品3桁（57分類）の HHI（割合の2乗の和、0〜1）。いちばん多い品物は概況品5桁で示す。
対象は2025年の輸出額が1,000億円以上の事務所（2015年も同じ基準）。事務所の良し悪しの順位ではなく、何が出ていくかの違いを見る。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font, note

setup_font()
A = pd.read_csv(DATA / "exports_customs_gaikyo_2015_2025.csv", dtype={"Custom": str, "Commodity": str})
NAMES = pd.read_csv(DATA / "gaikyo_export_names.csv", dtype=str).set_index("code")["name"]
CUS = pd.read_csv(DATA / "customs_names.csv", dtype=str).set_index("Custom")["custom_name"]
MIN = 1e8  # 千円 → 1,000億円


AIRPORT_WORDS = ("空港", "航空", "羽田", "千歳")  # 羽田税関支署・千歳税関支署は空港の税関


def kind(name):
    return "空港" if any(w in name for w in AIRPORT_WORDS) else "港など"


def table(y):
    a = A[A.year == y]
    tot = a[a.Commodity.str.len() == 1].groupby("Custom").value.sum()
    b = a[a.Commodity.str.len() == 3].copy().reset_index(drop=True)
    b["sh"] = b.value / b.groupby("Custom").value.transform("sum")
    h = b.groupby("Custom").agg(hhi3=("sh", lambda x: (x ** 2).sum()))
    c = a[a.Commodity.str.len() == 5].copy().reset_index(drop=True)
    c = c.merge(tot.rename("tot"), left_on="Custom", right_index=True)
    c["sh"] = c.value / c.tot
    top = c.loc[c.groupby("Custom").sh.idxmax()].set_index("Custom")
    h["total_oku"] = tot / 1e5
    h["top5_code"] = top.Commodity; h["top5_name"] = top.Commodity.map(NAMES); h["top5_share"] = top.sh
    h["name"] = [CUS.get(k, "") for k in h.index]; h["kind"] = h.name.map(kind)
    h["national_share"] = tot / tot.sum()
    return h, tot, b


main = {}
H = {}
for y in (2015, 2025):
    h, tot, b = table(y); H[y] = (h, tot, b)
    big = h[h.total_oku >= MIN / 1e5]
    nat = b.groupby("Commodity").value.sum(); nat = nat / nat.sum()
    main[str(y)] = {"total_cho": tot.sum() / 1e9, "offices_all": int(len(h)), "offices_big": int(len(big)),
                    "big_share_of_exports": float(big.total_oku.sum() / h.total_oku.sum()),
                    "top10_share": float(h.national_share.nlargest(10).sum()),
                    "national_hhi3": float((nat ** 2).sum()), "median_office_hhi3": float(big.hhi3.median()),
                    "wmean_office_hhi3": float((big.hhi3 * big.total_oku).sum() / big.total_oku.sum()),
                    "n_top5_over_half": int((big.top5_share > 0.5).sum()),
                    "exports_share_offices_top5_over_half": float(big.total_oku[big.top5_share > 0.5].sum() / h.total_oku.sum()),
                    "n_hhi_over_025": int((big.hhi3 > 0.25).sum())}
    big.sort_values("total_oku", ascending=False).round(4).to_csv(RES / f"offices_{y}.csv")
h25 = H[2025][0]; big25 = h25[h25.total_oku >= MIN / 1e5]
main["top5_item_counts_over_half"] = big25[big25.top5_share > 0.5].top5_name.value_counts().to_dict()
main["by_kind_2025"] = big25.groupby("kind").agg(n=("hhi3", "size"), median_hhi3=("hhi3", "median"), exports_oku=("total_oku", "sum")).round(3).to_dict(orient="index")
both = H[2015][0][["hhi3", "total_oku"]].join(big25[["hhi3", "total_oku", "name"]], lsuffix="15", rsuffix="25", how="inner")
both = both[both.total_oku15 >= MIN / 1e5]
main["change_2015_2025"] = {"n_offices": int(len(both)), "n_hhi_down": int((both.hhi325 < both.hhi315).sum()),
                            "median_change": float((both.hhi325 - both.hhi315).median())}
both.round(4).to_csv(RES / "hhi3_change_2015_2025.csv")
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：事務所の大きさと偏り（2025年）
fig, ax = plt.subplots(figsize=(8.4, 5.2))
for k, col in (("港など", "#1b9e77"), ("空港", "#d95f02")):
    d = big25[big25.kind == k]
    ax.scatter(d.total_oku, d.hhi3, s=40, color=col, alpha=0.75, label=f"{k}（{len(d)}）", edgecolor="none")
nat = main["2025"]["national_hhi3"]
ax.axhline(nat, color="#555", ls="--", lw=0.9); ax.text(1000, nat + 0.02, f"全国の輸出全体の偏り {nat:.2f}", fontsize=8.5, color="#555")
ax.set_xscale("log"); ax.set_xlabel("2025年の輸出額（億円、対数目盛）"); ax.set_ylabel("輸出する品物の偏り（HHI、概況品3桁）")
ax.set_title(f"輸出額1,000億円以上の{len(big25)}の税関の事務所：品物の偏りは大きく違う")
ax.legend(frameon=False, fontsize=9)
fig.subplots_adjust(bottom=0.14); note(fig); fig.savefig(FIG / "a284_scatter.png"); plt.close(fig)

# 図2：輸出額の大きい12の事務所の品物の構成（税関の符号の順に並べた）
GR = [("705", "輸送用機器"), ("703", "電気機器"), ("701", "一般機械"), ("5", "化学製品"), ("611", "鉄鋼"),
      ("613", "非鉄金属"), ("6", "その他の原料別製品"), ("8", "精密機器・雑製品"), ("9", "特殊取扱品（金など）"), ("", "食料品・原材料・燃料など")]
def gname(c):
    for p, n in GR:
        if p and c.startswith(p):
            return n
    return "食料品・原材料・燃料など"
b25 = H[2025][2].copy(); b25["g"] = b25.Commodity.map(gname)
sel = big25.total_oku.nlargest(12).index.sort_values()
comp = b25[b25.Custom.isin(sel)].pivot_table(index="Custom", columns="g", values="value", aggfunc="sum").fillna(0)
comp = comp.div(comp.sum(axis=1), axis=0)[[n for _, n in GR]].loc[sel]
comp.round(4).to_csv(RES / "composition_top12_2025.csv")
fig, ax = plt.subplots(figsize=(9.0, 5.6))
cols = ["#d95f02", "#7570b3", "#1b9e77", "#e7298a", "#666666", "#a6761d", "#bdbdbd", "#66a61e", "#e6ab02", "#a6cee3"]
left = np.zeros(len(comp))
for n, c in zip(comp.columns, cols):
    ax.barh(range(len(comp)), comp[n] * 100, left=left, color=c, label=n); left += comp[n].values * 100
ax.set_yticks(range(len(comp))); ax.set_yticklabels([f"{h25.loc[k, 'name']}（{h25.loc[k, 'total_oku']/1e4:.1f}兆円）" for k in comp.index], fontsize=8.8)
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("輸出額の構成（%）")
ax.set_title("輸出額の大きい12の事務所の品物の構成（2025年、税関の符号の順）", fontsize=11)
ax.legend(fontsize=7.8, frameon=False, ncol=5, loc="lower center", bbox_to_anchor=(0.42, -0.3))
fig.subplots_adjust(left=0.3, bottom=0.25); note(fig); fig.savefig(FIG / "a284_mix.png"); plt.close(fig)

# 図3：2015年と2025年の偏り
fig, ax = plt.subplots(figsize=(6.6, 5.6))
ax.scatter(both.hhi315, both.hhi325, s=np.sqrt(both.total_oku25) * 1.2, color="#7570b3", alpha=0.6, edgecolor="none")
lim = [0, 1]; ax.plot(lim, lim, color="#888", lw=0.8, ls="--"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_xlabel("2015年の偏り（HHI）"); ax.set_ylabel("2025年の偏り（HHI）")
c = main["change_2015_2025"]
ax.set_title(f"2015年と2025年の偏り：{c['n_offices']}の事務所のうち{c['n_hhi_down']}で下がった", fontsize=10.5)
ax.text(0.03, 0.93, "点の大きさ＝2025年の輸出額\n点線より下＝偏りが小さくなった", fontsize=8.5, transform=ax.transAxes, va="top")
fig.subplots_adjust(bottom=0.14, left=0.14); note(fig); fig.savefig(FIG / "a284_change.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, default=float, indent=0))
print(big25.sort_values("total_oku", ascending=False).head(15)[["name", "total_oku", "hhi3", "top5_name", "top5_share"]].round(3).to_string())
