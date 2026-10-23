"""国籍・地域別に、訪日客は何にお金を使っているか（費目の構成比と、買物の中身の対応分析）"""
from common import *

long, shop = load()
w = long.pivot_table(index=["year", "nat"], columns="item", values="yen")
share = w[ITEMS].div(w["全体"], axis=0)
NATS = [c for c in pd.read_csv(DATA / "spending_by_item.csv").columns[2:] if c not in ("全国籍・地域", "その他")]
L = []
y25 = w.loc[2025]
for n in ["全国籍・地域"] + NATS:
    L.append(f"2025 {n}: 総額 {y25.loc[n,'全体']:,.0f}円 " + " ".join(f"{i}{share.loc[(2025,n),i]:.1%}" for i in ITEMS))
for n in ["全国籍・地域", "中国", "韓国", "台湾", "香港", "米国", "英国", "オーストラリア"]:
    L.append(f"{n}: 2019 総額 {w.loc[(2019,n),'全体']:,.0f} 買物 {w.loc[(2019,n),'買物代']:,.0f}（{share.loc[(2019,n),'買物代']:.1%}） 宿泊 {share.loc[(2019,n),'宿泊費']:.1%}"
             f" → 2025 総額 {w.loc[(2025,n),'全体']:,.0f} 買物 {w.loc[(2025,n),'買物代']:,.0f}（{share.loc[(2025,n),'買物代']:.1%}） 宿泊 {share.loc[(2025,n),'宿泊費']:.1%}")
ch = (share.loc[2025, "買物代"] - share.loc[2019, "買物代"]).loc[NATS]
L.append(f"買物の割合が2019→2025で下がった国籍・地域 {(ch<0).sum()}/{len(ch)}、最大の低下 {ch.idxmin()} {ch.min()*100:.1f}pt")
asia = ["韓国", "台湾", "香港", "中国", "タイ", "シンガポール", "マレーシア", "インドネシア", "フィリピン", "ベトナム"]
west = ["英国", "ドイツ", "フランス", "イタリア", "スペイン", "米国", "カナダ", "オーストラリア"]
for nm, g in [("東・東南アジア10", asia), ("欧米豪8", west)]:
    L.append(f"2025 {nm}（単純平均）: 総額 {y25.loc[g,'全体'].mean():,.0f} 宿泊 {share.loc[2025].loc[g,'宿泊費'].mean():.1%} 買物 {share.loc[2025].loc[g,'買物代'].mean():.1%}")
share.round(4).to_csv(RES / "a145_share.csv")
w.round(0).to_csv(RES / "a145_spending.csv")

# 対応分析（2025年、買物の16品目 × 20の国籍・地域）
X = shop[NATS].T.astype(float)  # 行=国籍、列=品目
P = X / X.values.sum(); r = P.sum(1).values; c = P.sum(0).values
S = (P.values - np.outer(r, c)) / np.sqrt(np.outer(r, c))
U, sv, Vt = np.linalg.svd(S, full_matrices=False)
inertia = sv**2 / (sv**2).sum()
F = (U * sv) / np.sqrt(r)[:, None]          # 行（国籍）の主座標
G = (Vt.T * sv) / np.sqrt(c)[:, None]       # 列（品目）の主座標
if F[NATS.index("中国"), 0] < 0: F[:, 0] *= -1; G[:, 0] *= -1
if F[NATS.index("英国"), 1] < 0: F[:, 1] *= -1; G[:, 1] *= -1
L.append(f"対応分析 寄与率 第1軸 {inertia[0]:.1%} 第2軸 {inertia[1]:.1%}")
pd.DataFrame(F[:, :2], index=NATS, columns=["dim1", "dim2"]).round(3).to_csv(RES / "a145_ca_nations.csv")
pd.DataFrame(G[:, :2], index=X.columns, columns=["dim1", "dim2"]).round(3).to_csv(RES / "a145_ca_items.csv")
L.append("品目の座標（第1軸の順）:\n" + pd.DataFrame(G[:, :2], index=X.columns, columns=["d1", "d2"]).sort_values("d1").round(2).to_string())
L.append("国籍の座標（第1軸の順）:\n" + pd.DataFrame(F[:, :2], index=NATS, columns=["d1", "d2"]).sort_values("d1").round(2).to_string())
ps = shop[NATS + ["全国籍・地域"]].div(shop[NATS + ["全国籍・地域"]].sum(), axis=1)
for it in ["化粧品・香水", "医薬品", "菓子類", "民芸品・伝統工芸品", "酒類", "時計・フィルムカメラ", "宝石・貴金属"]:
    top = ps.loc[it, NATS].sort_values(ascending=False).head(3)
    L.append(f"買物に占める{it}: 全体 {ps.loc[it,'全国籍・地域']:.1%}／上位 " + "、".join(f"{k}{v:.1%}" for k, v in top.items()))
ps.round(4).to_csv(RES / "a145_shopping_share_2025.csv")
(RES / "a145_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

COL = {"宿泊費": BLUE, "飲食費": ORANGE, "交通費": GREEN, "娯楽等サービス費": PURPLE, "買物代": "#d6457a"}
# 図1：2025年 国籍・地域別の1人当たり支出と内訳
order = y25.loc[NATS + ["全国籍・地域"], "全体"].sort_values().index
fig, ax = plt.subplots(figsize=(9.5, 7.2))
left = np.zeros(len(order)); ys = np.arange(len(order))
for it in ITEMS:
    v = y25.loc[order, it].values / 1e4
    ax.barh(ys, v, left=left, color=COL[it], height=0.7, label=it.replace("娯楽等サービス費", "娯楽サービス"))
    left += v
for yy, n in zip(ys, order):
    ax.text(y25.loc[n, "全体"] / 1e4 + 0.5, yy, f"{y25.loc[n,'全体']/1e4:.1f}万円", va="center", fontsize=8.5)
ax.set_yticks(ys); ax.set_yticklabels([("■" if n == "全国籍・地域" else "") + n for n in order], fontsize=9.5)
ax.set_xlabel("1人1回当たり旅行支出（万円、2025年）"); ax.set_xlim(0, 46)
ax.legend(loc="lower right", fontsize=9, frameon=False)
ax.set_title("国籍・地域別の1人当たり旅行支出と内訳（2025年）")
save(fig, "a145_composition.png")

# 図2：2019年→2025年 買物と宿泊の割合の変化（主な国籍・地域）
KEY = ["全国籍・地域", "中国", "台湾", "香港", "韓国", "タイ", "ベトナム", "米国", "英国", "オーストラリア", "フランス"]
fig, ax = plt.subplots(figsize=(9.5, 6))
for n in KEY:
    x0, y0 = share.loc[(2019, n), "買物代"] * 100, share.loc[(2019, n), "宿泊費"] * 100
    x1, y1 = share.loc[(2025, n), "買物代"] * 100, share.loc[(2025, n), "宿泊費"] * 100
    col = INK if n == "全国籍・地域" else (ORANGE if n in asia else BLUE)
    ax.scatter([x0], [y0], facecolors="white", edgecolors=col, s=22, zorder=3)
    ax.scatter([x1], [y1], color=col, s=26, zorder=3)
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", color=col, lw=1.8 if n == "全国籍・地域" else 1.1, shrinkA=3, shrinkB=3))
    dx, dy = {"フランス": (-4.5, 0.8), "香港": (-3.2, 0.6), "タイ": (0.8, 0.6)}.get(n, (0.6, 0.4))
    ax.text(x1 + dx, y1 + dy, n.replace("全国籍・地域", "全体"), fontsize=9, color=col)
ax.set_xlim(5, 55); ax.set_ylim(18, 52)
ax.set_xlabel("買物代の割合（%）"); ax.set_ylabel("宿泊費の割合（%）")
ax.set_title("支出に占める買物と宿泊の割合（○2019年 → ●2025年）")
ax.text(0.99, 0.02, "オレンジ：東・東南アジア　青：欧米豪　黒：全体", transform=ax.transAxes, ha="right", fontsize=9, color=GRAY)
save(fig, "a145_shift.png")

# 図3：対応分析
fig, ax = plt.subplots(figsize=(10, 7.5))
ax.axhline(0, color=LIGHT, lw=0.8); ax.axvline(0, color=LIGHT, lw=0.8)
for i, n in enumerate(NATS):
    col = ORANGE if n in asia else (BLUE if n in west else GRAY)
    ax.scatter(F[i, 0], F[i, 1], color=col, s=22); ax.text(F[i, 0] + 0.015, F[i, 1] + 0.01, n, fontsize=8.5, color=col)
for j, it in enumerate(X.columns):
    ax.scatter(G[j, 0], G[j, 1], marker="^", color=INK, s=18)
    ax.text(G[j, 0] + 0.015, G[j, 1] - 0.03, it.replace("・飲料・たばこ", "").replace("などソフトウェア", "").replace("・ガイドブックなど", ""), fontsize=8, color=INK)
ax.set_xlabel(f"第1軸（{inertia[0]:.0%}）"); ax.set_ylabel(f"第2軸（{inertia[1]:.0%}）")
ax.set_title("買物の中身の対応分析（2025年、●国籍・地域　▲品目）")
save(fig, "a145_ca.png")
