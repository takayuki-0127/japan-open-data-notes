"""230 酒類の支出は、ビールから何に移ったのか

家計調査（二人以上の世帯）の「酒類」とその8品目の1世帯当たり年間支出（2015〜2025年）から、
  1. 酒類に占める品目の割合の移り変わり
  2. 年報（第4-6表の平均）の購入数量で見た、2019→2025年の量の変化（ビール・発泡酒系・チューハイなど）
  3. 世帯主の年齢別の品目の割合（2025年）と、その2019年からの変化
  4. 2026年1〜9月の前年同期比（2026年10月の酒税の一本化の前）
を出す。2025年改定で「発泡酒・ビール風アルコール飲料」は「発泡酒」に名前が変わった（同じ系列として扱う：推測）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, AGES, setup_font, annual, monthly, detail, cpi

setup_font()
P = annual()
C = cpi()
YRS = list(range(2015, 2026))
ITEMS = ["ビール", "発泡酒・ビール風アルコール飲料", "チューハイ・カクテル", "焼酎", "清酒", "ワイン", "ウイスキー", "他の酒"]
SHORT = {"ビール": "ビール", "発泡酒・ビール風アルコール飲料": "発泡酒・ビール風", "チューハイ・カクテル": "チューハイ・カクテル",
         "焼酎": "焼酎", "清酒": "清酒", "ワイン": "ワイン", "ウイスキー": "ウイスキー", "他の酒": "他の酒"}
COL = dict(zip(ITEMS, ["#d4a017", "#f2d06b", "#5b9bd5", "#8c564b", "#c49c94", "#9467bd", "#7f3c0a", "#bbbbbb"]))

sp = P.loc[YRS, ITEMS]
share = sp.div(P.loc[YRS, "酒類"], axis=0) * 100
share_chk = (sp.sum(axis=1) / P.loc[YRS, "酒類"] * 100)

# 購入数量（年報 第4-6表）。単位：ビール・発泡酒系はL、ほかはmL（L に直す）
D = detail().replace({"item": {"発泡酒": "発泡酒・ビール風アルコール飲料"}})
x = D[D.kind == "age"]
avg = x[x.group == "平均"]
Q = avg[avg.metric == "購入数量"].pivot_table(index="year", columns="item", values="value")
QI = ["ビール", "発泡酒・ビール風アルコール飲料", "チューハイ・カクテル", "焼酎", "清酒", "ワイン", "ウイスキー"]
QL = Q[QI].copy()
for c in QL:
    if QL[c].max() > 500:
        QL[c] = QL[c] / 1000
QL["ビール系の合計"] = QL["ビール"] + QL["発泡酒・ビール風アルコール飲料"]
qidx = QL / QL.loc[2019] * 100
PR = avg[avg.metric == "平均価格"].pivot_table(index="year", columns="item", values="value")

# 年齢別の割合（2019・2025年）
sp_age = x[(x.metric == "支出金額") & x.group.isin(AGES + ["平均"])]
def age_share(y):
    t = sp_age[sp_age.year == y].pivot_table(index="group", columns="item", values="value").loc[AGES + ["平均"]]
    return t[ITEMS].div(t["酒類"], axis=0) * 100
as19, as25 = age_share(2019), age_share(2025)
tot_age = sp_age[sp_age.item == "酒類"].pivot_table(index="group", columns="year", values="value").loc[AGES + ["平均"]]

# 2026年1〜9月
m = monthly()
m = m[m.item.isin(ITEMS + ["酒類"]) & (m.month <= 9)]
ytd = m.groupby(["item", "year"]).value.sum().unstack("year")
ytd_chg = (ytd[2026] / ytd[2025] - 1) * 100

# 実質の酒類（CPI 酒類）
real = P.loc[YRS, "酒類"] / C.loc[YRS, "酒類"] * 100

# 保存
sp.to_csv(RES / "spend_items.csv")
share.round(2).to_csv(RES / "share_items.csv")
QL.round(3).to_csv(RES / "quantity_liters.csv")
PR.round(2).to_csv(RES / "avg_price_per_unit.csv")
as25.round(2).to_csv(RES / "share_by_age_2025.csv")
as19.round(2).to_csv(RES / "share_by_age_2019.csv")
out = {
    "total_2015": float(P.loc[2015, "酒類"]), "total_2019": float(P.loc[2019, "酒類"]), "total_2020": float(P.loc[2020, "酒類"]),
    "total_2025": float(P.loc[2025, "酒類"]),
    "real_total_2025_vs_2015": round(float(real[2025] / real[2015] * 100), 1),
    "real_total_2025_vs_2019": round(float(real[2025] / real[2019] * 100), 1),
    "share_2015": share.loc[2015].round(1).rename(SHORT).to_dict(), "share_2019": share.loc[2019].round(1).rename(SHORT).to_dict(),
    "share_2025": share.loc[2025].round(1).rename(SHORT).to_dict(),
    "share_items_sum_check_max_abs_dev": round(float((share_chk - 100).abs().max()), 2),
    "liters_2019": QL.loc[2019].round(2).to_dict(), "liters_2025": QL.loc[2025].round(2).to_dict(),
    "liters_idx_2025": qidx.loc[2025].round(1).to_dict(),
    "beer_price_per_l": PR["ビール"].round(0).to_dict(), "happoshu_price_per_l": PR["発泡酒・ビール風アルコール飲料"].round(0).to_dict(),
    "age_share_2025": as25[["ビール", "発泡酒・ビール風アルコール飲料", "チューハイ・カクテル", "焼酎", "清酒", "ワイン", "ウイスキー"]].round(1).rename(columns=SHORT).to_dict(orient="index"),
    "age_share_change_2019_2025_pt": (as25 - as19)[["ビール", "発泡酒・ビール風アルコール飲料", "チューハイ・カクテル"]].round(1).rename(columns=SHORT).to_dict(orient="index"),
    "age_total_2025": tot_age[2025].to_dict(),
    "ytd_2026_vs_2025_pct": ytd_chg.round(1).rename(SHORT).to_dict(),
}
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# 図1：酒類に占める割合（積み上げ）
fig, ax = plt.subplots(figsize=(8, 4.8))
bottom = np.zeros(len(YRS))
for it in ITEMS:
    ax.bar(YRS, share[it], bottom=bottom, color=COL[it], label=SHORT[it], width=0.75)
    for xi, (b, v) in enumerate(zip(bottom, share[it])):
        if v >= 7 and YRS[xi] in (2015, 2019, 2025):
            ax.text(YRS[xi], b + v / 2, f"{v:.0f}", ha="center", va="center", fontsize=8)
    bottom += share[it].values
ax.set_xticks(YRS)
ax.set_ylim(0, 100)
ax.set_ylabel("酒類の支出に占める割合（%）")
ax.set_title("お酒の支出の中身（二人以上の世帯、2015〜2025年）")
ax.legend(frameon=False, fontsize=8, ncol=1, bbox_to_anchor=(1.01, 1), loc="upper left")
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」をもとに作成者が加工して作成。2025年は月の表の12か月の合計。2025年の「発泡酒」は旧「発泡酒・ビール風アルコール飲料」とつないだ", fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a230_share.png", dpi=150)
plt.close(fig)

# 図2：買った量（L、2019年＝100）
fig, ax = plt.subplots(figsize=(8, 4.8))
for it, c, lab in [("ビール", COL["ビール"], "ビール"), ("発泡酒・ビール風アルコール飲料", "#e07b39", "発泡酒・ビール風"),
                   ("ビール系の合計", "black", "ビール系の合計"), ("チューハイ・カクテル", COL["チューハイ・カクテル"], "チューハイ・カクテル"),
                   ("焼酎", COL["焼酎"], "焼酎"), ("ワイン", COL["ワイン"], "ワイン")]:
    ax.plot(qidx.index, qidx[it], marker="o", lw=2.6 if it == "ビール系の合計" else 1.8, color=c, label=lab,
            ls="--" if it == "ビール系の合計" else "-")
    ax.text(2025.1, qidx.loc[2025, it], f"{qidx.loc[2025, it]:.0f}", va="center", fontsize=8, color=c)
ax.axhline(100, color="gray", lw=.8)
ax.set_xticks(list(qidx.index))
ax.set_xlim(2018.7, 2025.6)
ax.set_title("お酒を買った量（L、2019年＝100）")
ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower left")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-6表（平均）をもとに作成者が加工して作成", fontsize=8, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a230_liters.png", dpi=150)
plt.close(fig)

# 図3：年齢別の中身（2025年）
fig, ax = plt.subplots(figsize=(8, 4.8))
labs = AGES + ["平均"]
left = np.zeros(len(labs))
yy = np.arange(len(labs))[::-1]
for it in ITEMS:
    v = as25.loc[labs, it].values
    ax.barh(yy, v, left=left, color=COL[it], label=SHORT[it])
    for i in range(len(labs)):
        if v[i] >= 8:
            ax.text(left[i] + v[i] / 2, yy[i], f"{v[i]:.0f}", ha="center", va="center", fontsize=8)
    left += v
ax.set_yticks(yy)
ax.set_yticklabels([f"{l}（{tot_age.loc[l, 2025]/1000:.0f}千円）" for l in labs], fontsize=9)
ax.set_xlim(0, 100)
ax.set_xlabel("酒類の支出に占める割合（%）、かっこ内は酒類の年間支出")
ax.set_title("お酒の支出の中身、世帯主の年齢別（2025年）")
ax.legend(frameon=False, fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-6表をもとに作成者が加工して作成。29歳以下は集計世帯が約100と少ない", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a230_age.png", dpi=150)
plt.close(fig)
