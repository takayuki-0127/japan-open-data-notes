"""W1：職業別の有効求人倍率。人手不足はどの職業で深いか（2013〜2026年、パートを含む常用）

職業分類は2023年4月分から変わった（旧＝平成23年改定 厚生労働省編職業分類、新＝平成21年改定 日本標準職業分類）。
新しい分類は2022年4月分まで遡って集計されているので、2022年度（2022年4月〜2023年3月）は両方の分類の値がある。
この重なりで、分類の切り替えでどれだけ値が動くかを確かめる。
"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load_occ, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, foot

d, names = load_occ()
d["年"] = d["年月"].str[:4].astype(int)
d["月"] = d["年月"].str[5:].astype(int)
nm = names[names["分類"] == "新"].set_index("行")["職業"].str.replace("（注２）", "", regex=False).to_dict()
MAJOR = [0, 1, 2, 15, 23, 27, 36, 37, 38, 50, 56, 62, 67, 68]  # 職業計・大分類・分類不能・介護関係職種（合計）
SHORT = {0: "職業計", 6: "情報処理・通信技術者", 9: "看護師など", 16: "一般事務", 29: "介護サービス", 32: "飲食物調理",
         36: "保安（警備員など）", 52: "自動車運転", 57: "建設躯体工事", 60: "土木作業", 63: "運搬", 68: "介護関係職種"}


def annual(sub, by):
    g = sub.groupby(by)[["有効求人", "有効求職", "新規求人", "新規求職", "就職件数"]].mean()
    g["倍率"] = g["有効求人"] / g["有効求職"]
    return g


# 1) 年平均（月の平均どうしの比）。旧分類は2013〜2022年、新分類は2023〜2025年。2026年は1〜8月
old = annual(d[(d["分類"] == "旧") & d["年"].between(2013, 2022)], ["行", "年"]).reset_index().assign(分類="旧")
new = annual(d[(d["分類"] == "新") & d["年"].between(2023, 2025)], ["行", "年"]).reset_index().assign(分類="新")
n26 = annual(d[(d["分類"] == "新") & (d["年"] == 2026)], ["行", "年"]).reset_index().assign(分類="新（1〜8月）")
n25p = annual(d[(d["分類"] == "新") & (d["年"] == 2025) & (d["月"] <= 8)], ["行", "年"]).reset_index().assign(分類="新（1〜8月）")
ann = pd.concat([old, new, n25p, n26], ignore_index=True)
ann["職業"] = ann["行"].map(nm)
ann.round(3).to_csv(RES / "w1_annual_by_occupation.csv", index=False)

# 2) 分類の切り替えの影響：2022年度を旧・新の両方で
fy = d[((d["年"] == 2022) & (d["月"] >= 4)) | ((d["年"] == 2023) & (d["月"] <= 3))]
br = pd.concat({k: annual(fy[fy["分類"] == k], ["行"]) for k in ("旧", "新")}, axis=1)
brk = pd.DataFrame({"職業": [nm[i] for i in br.index],
                    "倍率_旧分類": br[("旧", "倍率")], "倍率_新分類": br[("新", "倍率")],
                    "有効求人_新÷旧": br[("新", "有効求人")] / br[("旧", "有効求人")],
                    "有効求職_新÷旧": br[("新", "有効求職")] / br[("旧", "有効求職")]})
brk["倍率の差"] = brk["倍率_新分類"] - brk["倍率_旧分類"]
brk.round(3).to_csv(RES / "w1_break_fy2022.csv", index_label="行")

# 3) 2025年の中分類のランキング（有効求職者が月平均1,000人以上）
a25 = new[(new["年"] == 2025) & (~new["行"].isin(MAJOR))].copy()
a25["職業"] = a25["行"].map(nm)
a25 = a25[a25["有効求職"] >= 1000].sort_values("倍率", ascending=False)
a25.round(3).to_csv(RES / "w1_ranking_2025.csv", index=False)

# 4) 2013→2019年（同じ旧分類、オンライン登録の前）：倍率の変化を求人の変化と求職の変化に分ける
o = old.set_index(["行", "年"])
dec = pd.DataFrame({"職業": [nm[i] for i in o.xs(2013, level=1).index],
                    "倍率2013": o.xs(2013, level=1)["倍率"], "倍率2019": o.xs(2019, level=1)["倍率"],
                    "有効求人の変化(対数)": np.log(o.xs(2019, level=1)["有効求人"] / o.xs(2013, level=1)["有効求人"]),
                    "有効求職の変化(対数)": np.log(o.xs(2019, level=1)["有効求職"] / o.xs(2013, level=1)["有効求職"])})
dec["倍率の変化(対数)"] = dec["有効求人の変化(対数)"] - dec["有効求職の変化(対数)"]
dec.round(3).to_csv(RES / "w1_decomp_2013_2019.csv", index_label="行")

# --- 図1：主な職業の推移
sel = [57, 36, 52, 29, 6, 16, 0]
col = {57: ORANGE, 36: PURPLE, 52: GREEN, 29: BLUE, 6: "#c9a227", 16: GRAY, 0: INK}
fig, ax = plt.subplots(figsize=(8.6, 5))
for i in sel:
    a = old[old["行"] == i]; b = new[new["行"] == i]; c = n26[n26["行"] == i]
    lw = 2.4 if i == 0 else 1.8
    ax.plot(a["年"], a["倍率"], color=col[i], lw=lw)
    ax.plot(b["年"], b["倍率"], color=col[i], lw=lw)
    ax.plot([2022, 2023], [a["倍率"].iloc[-1], b["倍率"].iloc[0]], color=col[i], lw=lw * 0.7, ls=":")
    ax.plot(c["年"], c["倍率"], "o", color=col[i], ms=4, mfc="white")
    ax.text(2026.25, c["倍率"].iloc[0], SHORT[i] + f" {c['倍率'].iloc[0]:.2f}", color=col[i], va="center", fontsize=9)
ax.axvline(2022.5, color=GRAY, ls=":", lw=1)
ax.text(2022.55, 0.22, "職業分類の切り替え", color=GRAY, fontsize=8, va="bottom")
ax.set_yscale("log"); ax.set_yticks([0.3, 0.5, 1, 2, 3, 5, 8]); ax.set_yticklabels(["0.3", "0.5", "1", "2", "3", "5", "8"])
ax.set_xlim(2012.6, 2028.6); ax.set_xticks(range(2013, 2027, 2))
ax.set_ylabel("有効求人倍率（年平均、倍、対数目盛）")
ax.set_title("職業別の有効求人倍率（パートを含む常用）")
foot(fig, "2013〜2022年は旧分類、2023年以降は新分類（点線でつないだ）。白丸は2026年1〜8月の平均")
fig.savefig(FIG / "w1_trend.png"); plt.close(fig)

# --- 図2：2025年のランキング
top = pd.concat([a25.head(12), a25.tail(6)])
fig, ax = plt.subplots(figsize=(8, 6.4))
y = np.arange(len(top))[::-1]
ax.barh(y, top["倍率"], color=[ORANGE if v >= 1 else LIGHT for v in top["倍率"]])
for yy, v in zip(y, top["倍率"]):
    ax.text(v + 0.08, yy, f"{v:.2f}", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(top["職業"], fontsize=9)
tot = new[(new["行"] == 0) & (new["年"] == 2025)]["倍率"].iloc[0]
ax.axvline(tot, color=INK, lw=1, ls="--"); ax.text(tot + 0.05, y[-1] - 0.9, f"職業計 {tot:.2f}", fontsize=9)
ax.set_xlabel("有効求人倍率（2025年平均、倍）")
ax.set_title("2025年に倍率が高い職業・低い職業（上位12・下位6）")
foot(fig, "日本標準職業分類の中分類。有効求職者が月平均1,000人以上の職業")
fig.savefig(FIG / "w1_ranking.png"); plt.close(fig)

# --- 図3：2013→2019年の分解
ids = [36, 57, 52, 29, 60, 32, 6, 9, 16, 0]
dd = dec.loc[ids]
fig, ax = plt.subplots(figsize=(8, 5.2))
y = np.arange(len(ids))[::-1]
ax.barh(y + 0.18, 100 * (np.exp(dd["有効求人の変化(対数)"]) - 1), 0.36, color=ORANGE, label="有効求人の変化")
ax.barh(y - 0.18, 100 * (np.exp(dd["有効求職の変化(対数)"]) - 1), 0.36, color=BLUE, label="有効求職者の変化")
ax.set_yticks(y); ax.set_yticklabels([SHORT[i] + f"（{dd.loc[i, '倍率2013']:.2f}→{dd.loc[i, '倍率2019']:.2f}倍）" for i in ids], fontsize=9)
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("2013年→2019年の変化（%）")
ax.legend(frameon=False, loc="lower left")
ax.set_title("倍率が上がったのは求人が増えたからか、求職者が減ったからか")
foot(fig, "旧分類（平成23年改定 厚生労働省編職業分類）で比較。かっこ内は有効求人倍率の2013年→2019年")
fig.savefig(FIG / "w1_decomp.png"); plt.close(fig)

# --- 画面に要点
pd.set_option("display.width", 200)
print("職業計", ann[ann["行"] == 0][["分類", "年", "倍率", "有効求人", "有効求職"]].round(2).to_string(index=False))
for i in sel + [9, 32, 60, 68]:
    s = ann[ann["行"] == i]
    print(SHORT.get(i, nm[i]), " ".join(f"{r.年}{'*' if '1〜8' in r.分類 else ''}:{r.倍率:.2f}" for r in s.itertuples()))
print("\n2022年度の分類切り替え\n", brk.loc[[0, 6, 9, 16, 29, 32, 36, 52, 57, 60, 63, 68, 8, 3, 4, 7]].round(2).to_string())
print("\n2025ランキング\n", a25[["職業", "倍率", "有効求人", "有効求職"]].round(2).to_string(index=False))
print("\n分解\n", dec.loc[ids].round(3).to_string())
