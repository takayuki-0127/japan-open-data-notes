"""A281 輸入は、どの品目で円安の影響を受けたのか
統計品別表（輸入、9桁）で、2020→2025年の輸入額の増加を、品目ごとに「量」「ドルに直した単価」「為替（ドル円）」に分ける。
ln(金額) = ln(量) + ln(円の単価)、ln(円の単価) = ln(ドルに直した単価) + ln(ドル円)。
品目ごとの重みは対数平均（LMDI）で、品目の和が増加額にぴったり合う。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font, note

setup_font()
A = pd.read_csv(DATA / "imports_hs9_2019_2020_2025.csv", dtype={"HS": str})
MAP = pd.read_csv(DATA / "hs9_to_gaikyo_import.csv", dtype=str).fillna("")
NAMES = pd.read_csv(DATA / "gaikyo_import_names.csv", dtype=str).set_index("code")["name"]
FX = pd.read_csv(DATA / "usdjpy_annual.csv").set_index("year")["usdjpy"]
TOP = {"0": "食料品", "1": "飲料・たばこ", "2": "原料品", "3": "鉱物性燃料", "4": "動植物性油脂",
       "5": "化学製品", "6": "原料別製品", "7": "機械類・輸送用機器", "8": "雑製品", "9": "特殊取扱品"}


def lmean(a, b):
    return np.where(np.isclose(a, b), a, (b - a) / (np.log(b) - np.log(a)))


def decompose(y0, y1):
    a = A[A.year == y0].drop(columns="year"); b = A[A.year == y1].drop(columns="year")
    m = a.merge(b, on="HS", how="outer", suffixes=("0", "1"))
    for c in ["value0", "value1", "q20", "q21"]:
        m[c] = m[c].fillna(0)
    special = m.HS.str.startswith("00000")  # 少額貨物などの特殊なコード
    ok = (m.value0 > 0) & (m.value1 > 0) & (m.q20 > 0) & (m.q21 > 0) & (m.unit20 == m.unit21) & ~special
    mm = m[ok].copy()
    w = lmean(mm.value0.values, mm.value1.values)
    mm["d_qty"] = w * np.log(mm.q21 / mm.q20)
    mm["d_price"] = w * np.log((mm.value1 / mm.q21) / (mm.value0 / mm.q20))
    mm["d_fx"] = w * np.log(FX[y1] / FX[y0])
    mm["d_usd"] = mm.d_price - mm.d_fx
    mm["dv"] = mm.value1 - mm.value0
    mm["usd_unit_change"] = np.exp(np.log((mm.value1 / mm.q21) / (mm.value0 / mm.q20)) - np.log(FX[y1] / FX[y0])) - 1
    mm = mm.merge(MAP, on="HS", how="left").fillna({"gaikyo": "", "gaikyo_name": ""})
    tot0, tot1 = m.value0.sum(), m.value1.sum()
    s = {"y0": y0, "y1": y1, "total0_cho": tot0 / 1e9, "total1_cho": tot1 / 1e9, "dv_cho": (tot1 - tot0) / 1e9,
         "matched_items": int(ok.sum()), "matched_share_value1": mm.value1.sum() / tot1,
         "matched_dv_cho": mm.dv.sum() / 1e9, "qty_cho": mm.d_qty.sum() / 1e9, "fx_cho": mm.d_fx.sum() / 1e9,
         "usd_price_cho": mm.d_usd.sum() / 1e9, "unmatched_dv_cho": (tot1 - tot0 - mm.dv.sum()) / 1e9,
         "usdjpy0": FX[y0], "usdjpy1": FX[y1]}
    return s, mm


main = {}
s20, mm = decompose(2020, 2025)
s19, mm19 = decompose(2019, 2025)
s24 = None
main["base2020"] = s20; main["base2019"] = s19
for k, s in (("base2020", s20), ("base2019", s19)):
    md = s["matched_dv_cho"]
    s.update({"share_qty": s["qty_cho"] / md, "share_fx": s["fx_cho"] / md, "share_usd": s["usd_price_cho"] / md})

# 大分類（概況品の1桁）別
mm["g1"] = mm.gaikyo.str[:1]
g1 = mm.groupby("g1")[["value0", "value1", "dv", "d_qty", "d_fx", "d_usd"]].sum() / 1e9
g1.index = [TOP.get(i, "対応なし") for i in g1.index]
g1.round(4).to_csv(RES / "by_section_2020_2025.csv")
fuel_usd = g1.loc["鉱物性燃料", "d_usd"]
main["fuel_share_of_usd_price"] = fuel_usd / s20["usd_price_cho"]
main["fuel_dv_cho"] = g1.loc["鉱物性燃料", "dv"]


# 品目（概況品の5桁、ない場合は3桁）別
def key(c):
    return c[:5] if len(c) >= 5 else c[:3]


mm["k"] = mm.gaikyo.map(key)
it = mm.groupby("k")[["value0", "value1", "dv", "d_qty", "d_fx", "d_usd"]].sum() / 1e9
it["name"] = [NAMES.get(k, "") for k in it.index]
it = it.sort_values("dv", ascending=False)
it.round(4).to_csv(RES / "by_item_2020_2025.csv")

# ドルに直した単価が下がった品目の割合（2025年の金額で重み）
w = mm.value1
main["share_value_usd_unit_down"] = float(w[mm.usd_unit_change < 0].sum() / w.sum())
main["share_value_usd_unit_down_yen_up"] = float(w[(mm.usd_unit_change < 0) & (mm.d_price > 0)].sum() / w.sum())
main["share_value_qty_down"] = float(w[mm.d_qty < 0].sum() / w.sum())
yen_unit = (mm.value1 / mm.q21) / (mm.value0 / mm.q20) - 1
main["wmedian_yen_unit_change"] = float(np.interp(0.5, (w[np.argsort(yen_unit)].cumsum() / w.sum()).values, np.sort(yen_unit)))
main["wmedian_usd_unit_change"] = float(np.interp(0.5, (w.values[np.argsort(mm.usd_unit_change.values)].cumsum() / w.sum()),
                                                np.sort(mm.usd_unit_change.values)))
# 頑健性：燃料を除く
nf = mm[mm.g1 != "3"]
main["nonfuel"] = {"dv_cho": nf.dv.sum() / 1e9, "qty_cho": nf.d_qty.sum() / 1e9, "fx_cho": nf.d_fx.sum() / 1e9,
                   "usd_cho": nf.d_usd.sum() / 1e9}
# 頑健性：上位品目の寄与
main["top10_items_share_of_dv"] = float(it.dv.head(10).sum() / it.dv.sum())
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：増えた輸入額の内訳（2020年基準・2019年基準）
fig, ax = plt.subplots(figsize=(8.2, 4.6))
cols = [("qty_cho", "量", "#8c8c8c"), ("usd_price_cho", "ドルに直した単価", "#d95f02"), ("fx_cho", "為替（ドル円）", "#1b9e77"),
        ("unmatched_dv_cho", "分けられない分（品目の新設・廃止など）", "#c7c7c7")]
for i, (lab, s) in enumerate([("2020→2025年", s20), ("2019→2025年", s19)]):
    pos, neg = 0, 0
    for c, nm, col in cols:
        v = s[c]
        if v >= 0:
            ax.barh(i, v, left=pos, color=col, label=nm if i == 0 else None); pos += v
        else:
            ax.barh(i, v, left=neg, color=col, label=nm if i == 0 else None); neg += v
    ax.text(pos + 0.5, i, f"計 +{s['dv_cho']:.1f}兆円", va="center", fontsize=10)
ax.set_yticks([0, 1]); ax.set_yticklabels(["2020→2025年", "2019→2025年"]); ax.invert_yaxis()
ax.axvline(0, color="#333", lw=0.8); ax.set_xlabel("輸入額の増加（兆円）")
ax.set_title("輸入額の増加の内訳：量はほとんど増えず、増えたのは単価")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=2, fontsize=9, frameon=False)
fig.subplots_adjust(bottom=0.3, left=0.15); note(fig); fig.savefig(FIG / "a281_total.png"); plt.close(fig)

# 図2：増加額の大きい12品目の内訳
top = it.head(12).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.6, 6.0))
for i, (k, r) in enumerate(top.iterrows()):
    pos, neg = 0, 0
    for c, nm, col in [("d_qty", "量", "#8c8c8c"), ("d_usd", "ドルに直した単価", "#d95f02"), ("d_fx", "為替（ドル円）", "#1b9e77")]:
        v = r[c]
        if v >= 0:
            ax.barh(i, v, left=pos, color=col, label=nm if i == 0 else None); pos += v
        else:
            ax.barh(i, v, left=neg, color=col, label=nm if i == 0 else None); neg += v
ax.set_yticks(range(len(top))); ax.set_yticklabels(top.name, fontsize=9.5)
ax.axvline(0, color="#333", lw=0.8); ax.set_xlabel("2020→2025年の輸入額の増加（兆円）")
ax.set_title("増加額の大きい12品目：燃料はドル建ての値上がりも大きい")
ax.legend(loc="lower right", fontsize=9, frameon=False)
fig.subplots_adjust(left=0.27, bottom=0.12); note(fig); fig.savefig(FIG / "a281_items.png"); plt.close(fig)

# 図3：品目ごとの単価の変化（円・ドル）の分布、2025年の金額で重み
fig, ax = plt.subplots(figsize=(8.2, 4.6))
bins = np.linspace(-0.8, 2.0, 57)
yen = np.clip(yen_unit.values, -0.79, 1.99); usd = np.clip(mm.usd_unit_change.values, -0.79, 1.99)
ax.hist(yen, bins=bins, weights=w / w.sum() * 100, alpha=0.55, color="#1b9e77", label="円の単価")
ax.hist(usd, bins=bins, weights=w / w.sum() * 100, alpha=0.55, color="#d95f02", label="ドルに直した単価")
ax.axvline(0, color="#333", lw=0.8)
ax.axvline(FX[2025] / FX[2020] - 1, color="#1b9e77", ls="--", lw=1)
ax.text(FX[2025] / FX[2020] - 1 + 0.02, ax.get_ylim()[1] * 0.9, f"ドル円の変化 +{(FX[2025]/FX[2020]-1)*100:.0f}%", color="#1b9e77", fontsize=9)
ax.set_xlabel("2020→2025年の単価の変化（−80%〜+200%で切った）"); ax.set_ylabel("2025年の輸入額に占める割合（%）")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x*100:+.0f}%"))
ax.set_title("品目ごとの単価：ドルで見ると下がった品目が輸入額の2割強")
ax.legend(frameon=False)
fig.subplots_adjust(bottom=0.17); note(fig); fig.savefig(FIG / "a281_dist.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, default=float, indent=1)[:2500])
print(it.head(12).round(2).to_string())
print(g1.round(2).to_string())
