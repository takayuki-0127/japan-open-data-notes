"""A211 家賃を除くと、物価の地域差はどこまで縮むか：都道府県の地域差指数（総合・家賃を除く総合）のばらつきと、10大費目別の寄与（全国ウエイトで分解）"""
from common import *

I, W, PREF = load()
P = I.loc[PREF]
wn = W.loc["全国", ITEMS].astype(float); wn = wn / wn.sum()
contrib = (P[ITEMS].astype(float) - 100).mul(wn, axis=1)          # 費目iの寄与（ポイント）
contrib["合計（近似）"] = contrib.sum(axis=1)
contrib["総合−100"] = P["総合"] - 100
contrib["家賃を除く総合−100"] = P["家賃を除く総合"] - 100
contrib.round(3).to_csv(RES / "contribution_by_item.csv")

out = []
def p(s): out.append(s); print(s)
for c in ["総合", "家賃を除く総合"]:
    s = P[c]
    p(f"{c}: 最高 {s.idxmax()} {s.max()} 最低 {s.idxmin()} {s.min()} 差{s.max()-s.min():.1f} 標準偏差{s.std(ddof=0):.2f} 上位5平均-下位5平均{s.nlargest(5).mean()-s.nsmallest(5).mean():.2f}")
r = P["総合"].std(ddof=0); r2 = P["家賃を除く総合"].std(ddof=0)
p(f"標準偏差の縮み {(1-r2/r)*100:.1f}%  レンジの縮み {(1-(P['家賃を除く総合'].max()-P['家賃を除く総合'].min())/(P['総合'].max()-P['総合'].min()))*100:.1f}%")
p(f"近似の誤差（合計−(総合−100)）: 平均絶対{(contrib['合計（近似）']-contrib['総合−100']).abs().mean():.3f} 最大{(contrib['合計（近似）']-contrib['総合−100']).abs().max():.3f}")
var = P["総合"].var(ddof=0)
share = {c: np.cov(contrib[c], P["総合"] - 100, ddof=0)[0, 1] / var * 100 for c in ITEMS}   # ばらつきへの寄与（共分散分解）
p("総合のばらつき（分散）への寄与%: " + " ".join(f"{k}{v:.1f}" for k, v in sorted(share.items(), key=lambda x: -x[1])))
pd.Series(share).round(2).rename("share_of_variance_pct").to_csv(RES / "variance_share.csv")
p("費目別指数の都道府県の標準偏差: " + " ".join(f"{c}{P[c].std(ddof=0):.2f}" for c in ITEMS))
p(f"全国ウエイト（1万分比）: " + " ".join(f"{c}{wn[c]*1e4:.0f}" for c in ITEMS))
rk = P[["総合", "家賃を除く総合"]].rank(ascending=False, method="min")
mv = (rk["総合"] - rk["家賃を除く総合"])
p("家賃を除くと順位が下がる県（相対的に安くなる）: " + " ".join(f"{k}{int(rk.loc[k,'総合'])}→{int(rk.loc[k,'家賃を除く総合'])}位" for k in mv.sort_values().index[:5]))
p("家賃を除くと順位が上がる県（相対的に高くなる）: " + " ".join(f"{k}{int(rk.loc[k,'総合'])}→{int(rk.loc[k,'家賃を除く総合'])}位" for k in mv.sort_values().index[-5:]))
for k in list(P["総合"].nlargest(4).index) + list(P["総合"].nsmallest(3).index) + ["沖縄県", "北海道"]:
    c = contrib.loc[k, ITEMS].sort_values()
    p(f"{k} 総合{P.loc[k,'総合']} 家賃除く{P.loc[k,'家賃を除く総合']} 住居{P.loc[k,'住居']} 寄与: 住居{c['住居']:+.2f} 食料{c['食料']:+.2f} 光熱{c['光熱・水道']:+.2f} 教養{c['教養娯楽']:+.2f} 交通{c['交通・通信']:+.2f} | 最大+{c.idxmax()}{c.max():+.2f} 最大−{c.idxmin()}{c.min():+.2f}")
p(f"総合と家賃を除く総合の相関 {P['総合'].corr(P['家賃を除く総合']):.3f}")
p(f"住居指数 最高{P['住居'].idxmax()}{P['住居'].max()} 最低{P['住居'].idxmin()}{P['住居'].min()}")
p(f"光熱・水道 最高{P['光熱・水道'].idxmax()}{P['光熱・水道'].max()} 最低{P['光熱・水道'].idxmin()}{P['光熱・水道'].min()}")
p(f"総合が100以上の県 {int((P['総合']>=100).sum())} / 家賃を除く {int((P['家賃を除く総合']>=100).sum())}")
(RES / "summary.txt").write_text("\n".join(out), encoding="utf-8")

# 図1 総合と家賃を除く総合（並べた点）
o = P["総合"].sort_values().index
fig, ax = plt.subplots(figsize=(8.5, 9.5))
yy = np.arange(len(o))
ax.hlines(yy, P.loc[o, "総合"], P.loc[o, "家賃を除く総合"], color=LIGHT, lw=2)
ax.scatter(P.loc[o, "総合"], yy, color=BLUE, s=22, label="総合", zorder=3)
ax.scatter(P.loc[o, "家賃を除く総合"], yy, color=ORANGE, s=22, label="家賃を除く総合", zorder=3)
ax.axvline(100, color=GRAY, lw=1)
ax.set_yticks(yy); ax.set_yticklabels(o, fontsize=8); ax.set_xlabel("消費者物価地域差指数（全国=100）")
ax.legend(frameon=False, loc="lower right")
ax.set_title(f"家賃を除くと、差は{P['総合'].max()-P['総合'].min():.1f}ポイントから{P['家賃を除く総合'].max()-P['家賃を除く総合'].min():.1f}ポイントに")
save(fig, "a211_index.png")

# 図2 ばらつきへの寄与
sh = pd.Series(share).sort_values()
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.barh(sh.index, sh.values, color=[ORANGE if k == "住居" else BLUE for k in sh.index])
for i, v in enumerate(sh.values): ax.text(v + (1 if v >= 0 else -1), i, f"{v:.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.axvline(0, color=GRAY, lw=1); ax.set_xlabel("都道府県の総合指数のばらつき（分散）への寄与（%）")
ax.set_title(f"都道府県の物価差のばらつきの{share['食料']:.0f}%は食料、{share['住居']:.0f}%は住居から")
save(fig, "a211_share.png")

# 図3 上位・下位の県の費目別寄与（積み上げ）
sel = list(P["総合"].nlargest(5).index) + list(P["総合"].nsmallest(5).index)
C = contrib.loc[sel, ITEMS]
colors = {"住居": ORANGE, "食料": BLUE, "光熱・水道": GREEN, "教養娯楽": PURPLE, "交通・通信": LIGHT}
fig, ax = plt.subplots(figsize=(8.5, 5.2))
pos = np.zeros(len(sel)); neg = np.zeros(len(sel))
for c in ITEMS:
    v = C[c].values; col = colors.get(c, "#d0cfca")
    ax.bar(sel, np.where(v > 0, v, 0), bottom=pos, color=col, label=c if c in colors else None); pos += np.where(v > 0, v, 0)
    ax.bar(sel, np.where(v < 0, v, 0), bottom=neg, color=col); neg += np.where(v < 0, v, 0)
ax.bar(sel, [0] * len(sel), color="#d0cfca", label="その他の費目")
ax.scatter(sel, P.loc[sel, "総合"] - 100, color=INK, zorder=5, s=25, label="総合−100")
ax.axhline(0, color=GRAY, lw=1); ax.set_ylabel("全国との差への寄与（ポイント）"); ax.set_ylim(top=6)
ax.tick_params(axis="x", labelrotation=45); ax.legend(frameon=False, fontsize=8.5, ncol=3)
ax.set_title("総合が高い県・低い県の差は、どの費目から来ているか")
save(fig, "a211_contrib.png")
