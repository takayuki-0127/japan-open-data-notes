"""S8：どの街で、どのお酒にお金を使っているか。コレスポンデンス分析（対応分析）で「お酒の地図」を作る（家計調査、県庁所在市・政令市）"""
from common import *
d, lab = read("SSDSE-C-2026")
d = d.rename(columns={d.columns[0]: "code", d.columns[1]: "pref", d.columns[2]: "city"})
K = {"LB110001": "清酒", "LB110002": "焼酎", "LB110003": "ビール", "LB110004": "ウイスキー", "LB110005": "ワイン", "LB110006": "発泡酒", "LB110007": "チューハイ・カクテル", "LB110008": "その他の酒"}
assert all(lab[k].replace("他の酒", "その他の酒") == v for k, v in K.items())
nat = d[d.code == "R00000"].iloc[0]
X = d[d.code != "R00000"].set_index("city")[list(K)].astype(float).rename(columns=K)
tot = d[d.code != "R00000"].set_index("city")["LB11"].astype(float)

# コレスポンデンス分析：行（都市）と列（お酒）の「割合のかたより」を、少ない次元にまとめる
P = X.values / X.values.sum(); r = P.sum(1); c = P.sum(0)
S = (P - np.outer(r, c)) / np.sqrt(np.outer(r, c))
U, sv, Vt = np.linalg.svd(S, full_matrices=False)
inertia = sv ** 2; share = inertia / inertia.sum()
F = (U * sv) / np.sqrt(r)[:, None]          # 都市の座標（主座標）
G = (Vt.T * sv) / np.sqrt(c)[:, None]       # お酒の座標（主座標）
# 向きをそろえる：第1軸は焼酎がプラス側
if G[list(K.values()).index("焼酎"), 0] < 0: F[:, 0] *= -1; G[:, 0] *= -1
if G[list(K.values()).index("ワイン"), 1] < 0: F[:, 1] *= -1; G[:, 1] *= -1
cityc = pd.DataFrame(F[:, :2], index=X.index, columns=["dim1", "dim2"]); drinkc = pd.DataFrame(G[:, :2], index=X.columns, columns=["dim1", "dim2"])
share_tbl = X.div(X.sum(1), axis=0) * 100; nat_share = (nat[list(K)].astype(float) / nat[list(K)].astype(float).sum() * 100).rename(index=K)
print(share[:4].round(3)); print(drinkc.round(3)); print(cityc.sort_values("dim1").round(3).iloc[[0, 1, 2, 3, -4, -3, -2, -1]]); print(cityc.sort_values("dim2").round(3).iloc[[0, 1, 2, -3, -2, -1]])
s = {"inertia_dim1": share[0], "inertia_dim2": share[1], "inertia_dim12": share[:2].sum(), "n_city": len(X),
     "total_nat": float(nat.LB11), "total_max_city": tot.idxmax(), "total_max": tot.max(), "total_min_city": tot.idxmin(), "total_min": tot.min(),
     "shochu_share_nat": nat_share["焼酎"], "shochu_share_max_city": share_tbl["焼酎"].idxmax(), "shochu_share_max": share_tbl["焼酎"].max(),
     "sake_share_nat": nat_share["清酒"], "sake_share_max_city": share_tbl["清酒"].idxmax(), "sake_share_max": share_tbl["清酒"].max(),
     "wine_share_nat": nat_share["ワイン"], "wine_share_max_city": share_tbl["ワイン"].idxmax(), "wine_share_max": share_tbl["ワイン"].max(),
     "beer_share_nat": nat_share["ビール"], "happo_share_nat": nat_share["発泡酒"], "happo_share_max_city": share_tbl["発泡酒"].idxmax(), "happo_share_max": share_tbl["発泡酒"].max()}
pd.Series(s).to_csv(RES / "s8_summary.csv", header=["value"]); print(pd.Series(s))
pd.concat([cityc, share_tbl.round(1), tot.rename("酒類合計（円）")], axis=1).round(3).to_csv(RES / "s8_city.csv", encoding="utf-8-sig")
drinkc.round(3).to_csv(RES / "s8_drinks.csv", encoding="utf-8-sig")

SRC = source("SSDSE-家計消費（SSDSE-C-2026）") + "（総務省「家計調査」二人以上の世帯、2023〜2025年平均）"
fig, ax = plt.subplots(figsize=(9, 6.4))
ax.axhline(0, color="#d8d6cf", lw=0.8); ax.axvline(0, color="#d8d6cf", lw=0.8)
ax.scatter(cityc.dim1, cityc.dim2, s=14, color=LIGHT, edgecolor=BLUE, lw=0.5)
lab_c = set(cityc.dim1.nlargest(5).index) | set(cityc.dim1.nsmallest(5).index) | set(cityc.dim2.nlargest(4).index) | set(cityc.dim2.nsmallest(4).index) | {"東京都区部", "大阪市", "札幌市"}
for ci in lab_c:
    if ci in cityc.index: ax.annotate(ci, (cityc.loc[ci, "dim1"], cityc.loc[ci, "dim2"]), xytext=(3, 2), textcoords="offset points", fontsize=7.8, color="#52514e")
ax.scatter(drinkc.dim1, drinkc.dim2, s=60, marker="s", color=ORANGE, zorder=3)
for k_, r_ in drinkc.iterrows(): ax.annotate(k_, (r_.dim1, r_.dim2), xytext=(5, -4), textcoords="offset points", fontsize=10.5, color=ORANGE, weight="bold")
ax.set_xlabel(f"第1軸（{share[0] * 100:.0f}%）：右ほど焼酎寄り"); ax.set_ylabel(f"第2軸（{share[1] * 100:.0f}%）")
ax.set_title("お酒の地図：右は焼酎・発泡酒の西日本、左は清酒・ワイン・ウイスキーの東日本と大都市", loc="left")
fig.text(0.01, -0.03, SRC + "\n（コレスポンデンス分析。都市と品目が近いほど、その都市はその品目にかける割合が全国より高い）", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "s8_map.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4))
top = share_tbl.loc[cityc.dim1.sort_values().index]
sel = list(top.index[:6]) + list(top.index[-6:])
bottom = np.zeros(len(sel)); cols = ["#2a78d6", "#eb6834", "#e8b22e", "#7a5bd6", "#c2406b", "#a9c9ef", "#3aa07a", "#a3a29c"]
for k_, col in zip(K.values(), cols):
    v = top.loc[sel, k_].values; ax.barh(range(len(sel)), v, left=bottom, color=col, label=k_); bottom += v
ax.set_yticks(range(len(sel)), sel); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("酒類への支出のうちの割合（%）")
ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.18))
ax.set_title("第1軸の両端の6都市：何にお金を使っているか", loc="left")
fig.text(0.01, -0.22, SRC, fontsize=7, color="#8a8984"); fig.savefig(FIG / "s8_share.png"); plt.close(fig)
