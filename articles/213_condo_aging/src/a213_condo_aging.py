"""A213 古いマンションの住人の高齢化：完成年次別の役員の年代（平成30年度と令和5年度で同じ築年の区分を比べる）、将来の不安、永住意識"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import sections, era_rows, ERAS, ERA_END, FIG, RES, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

S = sections()
AGES = ["合計", "20歳未満", "20歳代", "30歳代", "40歳代", "50歳代", "60歳代", "70歳代", "80歳以上"]
def officers(key):
    r = era_rows(S[key], ncol=9)
    d = pd.DataFrame(r, index=AGES).T
    d["share70"] = (d["70歳代"] + d["80歳以上"]) / d["合計"] * 100
    d["share60"] = (d["60歳代"] + d["70歳代"] + d["80歳以上"]) / d["合計"] * 100
    d["share_u50"] = d[["20歳未満", "20歳代", "30歳代", "40歳代"]].sum(axis=1) / d["合計"] * 100
    return d
o23 = officers("10-④(1)"); o18 = officers("１１-②（１）-1")
coh = pd.DataFrame({"y2018_share70": o18.loc[ERAS, "share70"], "y2023_share70": o23.loc[ERAS, "share70"],
                    "y2018_share60": o18.loc[ERAS, "share60"], "y2023_share60": o23.loc[ERAS, "share60"],
                    "y2018_total": o18.loc[ERAS, "合計"], "y2023_total": o23.loc[ERAS, "合計"]})
coh["diff70"] = coh.y2023_share70 - coh.y2018_share70
o23.round(2).to_csv(RES / "officers_age_by_era_2023.csv"); o18.round(2).to_csv(RES / "officers_age_by_era_2018.csv"); coh.round(2).to_csv(RES / "officers_cohort_2018_2023.csv")

COLS = ["合計", "区分所有者の高齢化", "居住者の高齢化", "賃貸住戸の増加", "所有者不明住戸の増加", "居住目的外利用住戸の増加", "管理費等の未払いの増加", "修繕積立金の不足", "理事の選任が困難"]
anx = pd.DataFrame(era_rows(S["46-1"], value_line="pct", ncol=8), index=COLS[1:]).T
anx.to_csv(RES / "anxiety_by_era_2023.csv")
body = S["5②-(1)"]; body = body[body.index("完成年次別"):]
perm = pd.DataFrame(era_rows(body, value_line="pct", ncol=4), index=["永住するつもり", "いずれは住み替える", "特に考えていない", "不明"]).T
perm.to_csv(RES / "permanent_by_era_2023.csv")

L = []
L.append("役員のうち70歳以上の割合（令和5年度、完成年次別）: " + ", ".join(f"{k} {v:.1f}%" for k, v in o23.share70.items() if k != "不明"))
L.append("同じ築年の区分で平成30年度→令和5年度（70歳以上の割合）: " + ", ".join(f"{k} {r.y2018_share70:.1f}→{r.y2023_share70:.1f}（{r.diff70:+.1f}）" for k, r in coh.iterrows()))
L.append(f"8区分のうち上がった区分 {(coh.diff70>0).sum()}、平均の変化 {coh.diff70.mean():+.1f}ポイント")
def overall(key):
    for l in S[key].split("\n"):
        c = [x for x in l.split(",") if x != ""]
        if c and c[0].replace("　", "") == "全体":
            v = [float(x) for x in c[1:10]]; return (v[7] + v[8]) / v[0] * 100
L.append(f"全体の役員 70歳以上 平成30年度 {overall('１１-②（１）-1'):.1f}% → 令和5年度 {overall('10-④(1)'):.1f}%（全体行の平均人数から）")
L.append("将来の不安「区分所有者の高齢化」: " + ", ".join(f"{k} {v:.1f}%" for k, v in anx["区分所有者の高齢化"].items()))
L.append("将来の不安「理事の選任が困難」: " + ", ".join(f"{k} {v:.1f}%" for k, v in anx["理事の選任が困難"].items()))
L.append("永住するつもり（完成年次別）: " + ", ".join(f"{k} {v:.1f}%" for k, v in perm["永住するつもり"].items()))
open(RES / "summary.txt", "w").write("\n".join(L) + "\n"); print("\n".join(L))

lab = lambda k: k.replace("～", "〜").replace("６", "6").replace("２", "2")
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(ERAS))
for i, (k, r) in enumerate(coh.iterrows()):
    ax.plot([i, i], [r.y2018_share70, r.y2023_share70], color=GRAY, lw=1.2, zorder=1)
ax.scatter(x, coh.y2018_share70, color=LIGHT, s=60, label="平成30年度（2018）", zorder=2, edgecolor=BLUE)
ax.scatter(x, coh.y2023_share70, color=ORANGE, s=60, label="令和5年度（2023）", zorder=3)
for i, (k, r) in enumerate(coh.iterrows()):
    ax.text(i + 0.12, r.y2023_share70, f"{r.y2023_share70:.0f}%", fontsize=9, color=ORANGE, va="center")
ax.set_xticks(x); ax.set_xticklabels([lab(k) for k in ERAS], rotation=30, ha="right")
ax.set_xlabel("マンションの完成年次"); ax.set_ylabel("役員のうち70歳以上の割合（%）")
ax.legend(frameon=False); ax.set_title("同じ築年のマンションを5年後に見ると、役員の70歳以上が増えている")
fig.text(0.01, -0.12, SOURCE + "（管理組合向け調査、役員の年代別平均人数から計算）", fontsize=8, color=GRAY); fig.savefig(FIG / "a213_cohort.png"); plt.close()

eras23 = [k for k in anx.index]
fig, ax = plt.subplots(figsize=(9, 5))
xx = np.arange(len(eras23))
for col, c in [("区分所有者の高齢化", ORANGE), ("居住者の高齢化", "#c4471d"), ("理事の選任が困難", BLUE), ("修繕積立金の不足", GRAY)]:
    ax.plot(xx, anx[col], marker="o", color=c, lw=2.2 if "高齢" in col else 1.6, label=col)
ax.set_xticks(xx); ax.set_xticklabels([lab(k) for k in eras23], rotation=30, ha="right")
ax.set_ylabel("将来の不安として挙げた管理組合の割合（%）"); ax.set_xlabel("マンションの完成年次")
ax.legend(frameon=False); ax.set_title("管理組合運営の将来の不安（令和5年度、重複回答）")
fig.text(0.01, -0.14, SOURCE, fontsize=8, color=GRAY); fig.savefig(FIG / "a213_anxiety.png"); plt.close()

fig, ax = plt.subplots(figsize=(9, 5))
pe = perm.drop(index=[k for k in perm.index if k not in ERA_END])
xx = np.arange(len(pe)); b = np.zeros(len(pe))
for col, c in [("永住するつもり", ORANGE), ("いずれは住み替える", BLUE), ("特に考えていない", LIGHT), ("不明", "#dddddd")]:
    ax.bar(xx, pe[col], bottom=b, color=c, label=col, width=0.7); b += pe[col].values
for i, v in enumerate(pe["永住するつもり"]):
    ax.text(i, v / 2, f"{v:.0f}", ha="center", va="center", fontsize=9, color="white")
ax.set_xticks(xx); ax.set_xticklabels([lab(k) for k in pe.index], rotation=30, ha="right"); ax.set_ylim(0, 112); ax.set_yticks(range(0, 101, 20))
ax.set_ylabel("区分所有者の割合（%）"); ax.set_xlabel("マンションの完成年次")
ax.legend(frameon=False, ncol=4, loc="upper center", fontsize=9)
ax.set_title("今のマンションに永住するつもりの人（令和5年度、区分所有者向け調査）")
fig.text(0.01, -0.14, SOURCE, fontsize=8, color=GRAY); fig.savefig(FIG / "a213_permanent.png"); plt.close()
