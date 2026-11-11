"""255 野菜の作付けは、どの品目で減ったのか

農林水産省「作物統計調査（野菜生産出荷統計）」の品目別作付面積・収穫量の累年統計（全国、1973〜2024年）で、
  1. 1973年からずっと全国の値がある27品目：1973→2024年の作付面積の変化と、減った面積への寄与
  2. 2005年から全国の値がある39品目：2005→2024年の変化（増えた品目・減った品目）
  3. 面積と収穫量の比べ（10a当たり収量が上がった分）
data/ の CSV は e-Stat の Excel を、そのまま CSV にしたもの（季節区分の行は使わず、品目の計だけを使う）。
"""
import csv
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font

setup_font()
MAIN = {
    "veg1_root": ["だいこん", "かぶ", "にんじん", "ごぼう", "れんこん", "ばれいしょ", "さといも", "やまのいも"],
    "veg2_leaf": ["はくさい", "こまつな", "キャベツ", "ちんげんさい", "ほうれんそう", "ふき", "みつば", "しゅんぎく", "みずな",
                  "セルリー", "アスパラガス", "カリフラワー", "ブロッコリー", "レタス", "ねぎ", "にら", "たまねぎ", "にんにく"],
    "veg3_fruitveg": ["きゅうり", "かぼちゃ", "なす", "トマト", "ピーマン", "未成熟トウモロコシ（スイートコーン）", "さやいんげん",
                      "さやえんどう", "グリーンピース", "そらまめ", "えだまめ"],
    "veg4_spice": ["しょうが"],
    "veg5_fruitlike": ["いちご", "メロン", "すいか"],
}
GROUP = {"veg1_root": "根菜類", "veg2_leaf": "葉茎菜類", "veg3_fruitveg": "果菜類", "veg4_spice": "香辛野菜", "veg5_fruitlike": "果実的野菜"}
SHORT = {"未成熟トウモロコシ（スイートコーン）": "スイートコーン"}


def num(v):
    v = v.replace(",", "").strip()
    try:
        return float(v)
    except ValueError:
        return np.nan


rows = []
for k, items in MAIN.items():
    R = list(csv.reader(open(DATA / f"{k}.csv", encoding="utf-8")))
    cols = {x: j for j, x in enumerate(R[4]) if x}
    for r in R[7:]:
        m = re.search(r"\((\d{4})\)", r[0] or "")
        if not m:
            continue
        for it in items:
            j = cols[it]
            rows.append({"分類": GROUP[k], "品目": SHORT.get(it, it), "年": int(m.group(1)),
                         "作付面積_ha": num(r[j]), "収穫量_t": num(r[j + 1]), "出荷量_t": num(r[j + 2])})
D = pd.DataFrame(rows)
D.to_csv(RES / "a255_long.csv", index=False)
A = D.pivot(index="年", columns="品目", values="作付面積_ha")
H = D.pivot(index="年", columns="品目", values="収穫量_t")
grp = D.drop_duplicates("品目").set_index("品目")["分類"]

full = [c for c in A if A[c].notna().all()]
c1 = pd.DataFrame({"分類": grp[full], "1973年_ha": A.loc[1973, full], "2024年_ha": A.loc[2024, full]})
c1["倍率"] = (c1["2024年_ha"] / c1["1973年_ha"]).round(3)
c1["増減_ha"] = c1["2024年_ha"] - c1["1973年_ha"]
tot0, tot1 = c1["1973年_ha"].sum(), c1["2024年_ha"].sum()
c1["減った面積に占める割合_%"] = (c1["増減_ha"] / (tot1 - tot0) * 100).round(1)
c1["収穫量の倍率"] = (H.loc[2024, full] / H.loc[1973, full]).round(3)
c1 = c1.sort_values("増減_ha")
c1.to_csv(RES / "a255_1973_2024.csv")

c2i = [c for c in A if pd.notna(A.loc[2005, c]) and pd.notna(A.loc[2024, c])]
c2 = pd.DataFrame({"分類": grp[c2i], "2005年_ha": A.loc[2005, c2i], "2024年_ha": A.loc[2024, c2i]})
c2["倍率"] = (c2["2024年_ha"] / c2["2005年_ha"]).round(3)
c2["収穫量の倍率"] = (H.loc[2024, c2i] / H.loc[2005, c2i]).round(3)
c2 = c2.sort_values("倍率")
c2.to_csv(RES / "a255_2005_2024.csv")

# 頑健性：端の1年でなく3年平均（1973〜75年 → 2022〜24年）
a0 = A.loc[1973:1975, full].mean(); a1 = A.loc[2022:2024, full].mean()
rk = (a1 / a0).sort_values()
# 分類ごと
g = c1.groupby("分類")[["1973年_ha", "2024年_ha"]].sum()
g["倍率"] = (g["2024年_ha"] / g["1973年_ha"]).round(3)
# 面積が減った品目の数・増えた品目
res = {
    "27品目_1973年_ha": float(tot0), "27品目_2024年_ha": float(tot1), "27品目_倍率": round(tot1 / tot0, 3),
    "27品目の収穫量_倍率": round(float(H.loc[2024, full].sum() / H.loc[1973, full].sum()), 3),
    "1973→2024_増えた品目": c1[c1["増減_ha"] > 0].index.tolist(),
    "1973→2024_減りの大きい順（ha）": {k: int(v) for k, v in c1["増減_ha"].head(6).items()},
    "上位4品目の寄与_%": round(float(c1["減った面積に占める割合_%"].head(4).sum()), 1),
    "倍率の小さい順_5品目": {k: float(v) for k, v in c1.sort_values("倍率")["倍率"].head(5).items()},
    "分類別": g.reset_index().to_dict("records"),
    "39品目_2005年_ha": float(c2["2005年_ha"].sum()), "39品目_2024年_ha": float(c2["2024年_ha"].sum()),
    "39品目_倍率": round(float(c2["2024年_ha"].sum() / c2["2005年_ha"].sum()), 3),
    "2005→2024_増えた品目": {k: float(v) for k, v in c2[c2["倍率"] > 1]["倍率"].items()},
    "ブロッコリー_1989年_ha": float(A.loc[1989, "ブロッコリー"]), "ブロッコリー_2024年_ha": float(A.loc[2024, "ブロッコリー"]),
    "頑健性_3年平均_増えた品目": rk[rk > 1].round(3).to_dict(),
    "頑健性_3年平均_小さい順5": rk.head(5).round(3).to_dict(),
    "頑健性_3年平均_27品目倍率": round(float(a1.sum() / a0.sum()), 3),
}
json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

# 図1：27品目の倍率（1973→2024）
s = c1.sort_values("倍率")
fig, ax = plt.subplots(figsize=(7.6, 7.2))
colors = ["#2b6cb0" if v >= 1 else "#a0aec0" for v in s["倍率"]]
ax.barh(range(len(s)), s["倍率"], color=colors)
for i, (k, v) in enumerate(s["倍率"].items()):
    ax.text(v + 0.02, i, f"{v:.2f}倍（{int(s.loc[k, '1973年_ha']):,}→{int(s.loc[k, '2024年_ha']):,}ha）", va="center", fontsize=7.5)
ax.axvline(1, color="#555", lw=0.8)
ax.set_yticks(range(len(s))); ax.set_yticklabels(s.index, fontsize=8.5)
ax.set_xlim(0, 2.3)
ax.set_xlabel("2024年の作付面積 ÷ 1973年")
ax.set_title("野菜の作付面積（全国、1973→2024年）：27品目中25品目で減った", fontsize=11)
fig.text(0.01, 0.006, "1973年から毎年全国の値がある27品目。出典：農林水産省「作物統計調査（野菜生産出荷統計）」", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.025, 1, 1)); fig.savefig(FIG / "a255_ratio_1973.png", dpi=150); plt.close(fig)

# 図2：減った面積の内訳（ha）
s = c1.sort_values("増減_ha").head(10)
fig, ax = plt.subplots(figsize=(7.6, 4.4))
ax.barh(range(len(s))[::-1], -s["増減_ha"] / 1000, color="#c05621")
for i, (k, v) in zip(range(len(s))[::-1], s["増減_ha"].items()):
    ax.text(-v / 1000 + 0.8, i, f"{-v/1000:.1f}千ha（{-s.loc[k, '減った面積に占める割合_%']:.0f}%）" if False else f"{-v/1000:.1f}千ha（減った分の{s.loc[k, '減った面積に占める割合_%']:.0f}%）", va="center", fontsize=8)
ax.set_yticks(range(len(s))[::-1]); ax.set_yticklabels(s.index, fontsize=9)
ax.set_xlim(0, 105)
ax.set_xlabel("1973→2024年に減った作付面積（千ha）")
ax.set_title(f"27品目で減った{(tot0-tot1)/1000:.0f}千haのうち、上位4品目で半分強", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a255_decline_share.png", dpi=150); plt.close(fig)

# 図3：2005→2024（39品目）面積と収穫量の倍率
s = c2.sort_values("倍率")
fig, ax = plt.subplots(figsize=(7.6, 7.6))
y = np.arange(len(s))
ax.scatter(s["倍率"], y, color="#2b6cb0", s=22, label="作付面積", zorder=3)
ax.scatter(s["収穫量の倍率"], y, color="#ed8936", s=22, marker="D", label="収穫量", zorder=3)
for i, k in enumerate(s.index):
    ax.plot([s.loc[k, "倍率"], s.loc[k, "収穫量の倍率"]], [i, i], color="#cbd5e0", lw=1, zorder=1)
ax.axvline(1, color="#555", lw=0.8)
ax.set_yticks(y); ax.set_yticklabels(s.index, fontsize=8)
ax.set_xlabel("2024年 ÷ 2005年")
ax.set_title("2005→2024年：面積が増えたのはブロッコリー・こまつな・にんにく・たまねぎ", fontsize=10.5)
ax.legend(frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "a255_2005_2024.png", dpi=150); plt.close(fig)
print(json.dumps(res, ensure_ascii=False, indent=1))
print(c1.to_string())
