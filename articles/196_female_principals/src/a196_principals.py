"""女性の校長の割合は都道府県でどれだけ違うか（公立小・中学校、2015年度と2025年度）"""
from common import *

d = load()
L = []
g = d.groupby(["year", "school"]).sum(numeric_only=True)
for (y, s), r in g.iterrows():
    L.append(f"{y} {s}学校 校長 女{int(r.head_f):,}/{int(r.head_m+r.head_f):,} = {r.head_f/(r.head_m+r.head_f):.1%}  副校長・教頭の女性 {(r.vice_f+r.kyoto_f)/(r.vice_m+r.vice_f+r.kyoto_m+r.kyoto_f):.1%}  教員全体の女性 {r.tot_f/(r.tot_m+r.tot_f):.1%}")
w = d.pivot_table(index="pref", columns=["school", "year"], values=["head_share", "vk_share", "tf_share"])
w.to_csv(RES / "a196_pref_wide.csv", encoding="utf-8")
for s in ["小", "中"]:
    x = w["head_share"][s][2025].sort_values(ascending=False)
    L.append(f"{s}学校 2025 上位: " + "、".join(f"{p} {v:.1%}" for p, v in x.head(5).items()) + " / 下位: " + "、".join(f"{p} {v:.1%}" for p, v in x.tail(5).items()))
    L.append(f"{s}学校 2025 最大/最小 {x.max()/x.min():.1f}倍、標準偏差 {x.std():.3f}（2015 {w['head_share'][s][2015].std():.3f}）、30%以上の県 {(x>=0.3).sum()}（2015 {(w['head_share'][s][2015]>=0.3).sum()}）")
    ch = (w["head_share"][s][2025] - w["head_share"][s][2015]).sort_values(ascending=False)
    L.append(f"{s}学校 2015→2025 変化 上位: " + "、".join(f"{p} {v*100:+.1f}pt" for p, v in ch.head(5).items()) + " 下がった県: " + "、".join(f"{p} {v*100:+.1f}pt" for p, v in ch[ch < 0].items()))
    r1 = np.corrcoef(w["vk_share"][s][2015], w["head_share"][s][2025])[0, 1]
    r2 = np.corrcoef(w["tf_share"][s][2025], w["head_share"][s][2025])[0, 1]
    r3 = np.corrcoef(w["head_share"][s][2015], w["head_share"][s][2025])[0, 1]
    L.append(f"{s}学校 相関: 2015年の副校長・教頭の女性割合と2025年の女性校長割合 r={r1:.2f}、2025年の教員の女性割合と女性校長割合 r={r2:.2f}、2015と2025の女性校長割合 r={r3:.2f}")
xs, xc = w["head_share"]["小"][2025], w["head_share"]["中"][2025]
L.append(f"小と中の女性校長割合の相関（2025）r={np.corrcoef(xs, xc)[0,1]:.2f}")
(RES / "a196_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：小学校の女性校長の割合（2025、県別）と2015年
x = w["head_share"]["小"].sort_values(2025)
fig, ax = plt.subplots(figsize=(9.5, 11))
ys = np.arange(len(x))
ax.barh(ys, x[2025] * 100, color=BLUE, height=0.7, label="2025年度")
ax.scatter(x[2015] * 100, ys, color=ORANGE, s=18, zorder=3, label="2015年度")
nat = g.loc[(2025, "小")]; nv = nat.head_f / (nat.head_m + nat.head_f) * 100
ax.axvline(nv, color=INK, lw=1, ls="--"); ax.text(nv + 0.5, len(x) - 0.5, f"全国 {nv:.1f}%", fontsize=9)
ax.set_yticks(ys); ax.set_yticklabels(x.index, fontsize=9)
ax.set_xlabel("公立小学校の校長に占める女性の割合（%）"); ax.legend(loc="lower right", frameon=False)
ax.set_title("公立小学校の女性校長の割合（都道府県別）")
save(fig, "a196_pref_elem.png")

# 図2：段階別の女性割合（教員全体・副校長と教頭・校長）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, s in zip(axes, ["小", "中"]):
    vals = []
    for y in [2015, 2025]:
        r = g.loc[(y, s)]
        vals.append([r.tot_f / (r.tot_m + r.tot_f), (r.vice_f + r.kyoto_f) / (r.vice_m + r.vice_f + r.kyoto_m + r.kyoto_f), r.head_f / (r.head_m + r.head_f)])
    xx = np.arange(3)
    for k, (y, c) in enumerate(zip([2015, 2025], [LIGHT, BLUE])):
        b = ax.bar(xx + (k - 0.5) * 0.38, np.array(vals[k]) * 100, width=0.38, color=c, label=f"{y}年度")
        for xi, v in zip(xx + (k - 0.5) * 0.38, vals[k]):
            ax.text(xi, v * 100 + 1, f"{v*100:.0f}", ha="center", fontsize=9)
    ax.set_xticks(xx); ax.set_xticklabels(["教員全体", "副校長・教頭", "校長"]); ax.set_title(f"公立{s}学校")
axes[0].set_ylabel("女性の割合（%）"); axes[0].legend(frameon=False); axes[0].set_ylim(0, 75)
fig.suptitle("職が上がるほど女性の割合は下がる（2015年度と2025年度）", y=1.04)
save(fig, "a196_pipeline.png")

# 図3：2015年の副校長・教頭の女性割合と2025年の女性校長割合（小学校）
a, b = w["vk_share"]["小"][2015] * 100, w["head_share"]["小"][2025] * 100
fig, ax = plt.subplots(figsize=(8, 5.5))
ax.scatter(a, b, color=BLUE, s=22)
for p in a.index:
    if b[p] > 40 or b[p] < 17 or a[p] > 40:
        ax.annotate(p, (a[p], b[p]), fontsize=8, xytext=(3, 2), textcoords="offset points")
k = np.polyfit(a, b, 1); xx = np.linspace(a.min(), a.max(), 10); ax.plot(xx, np.polyval(k, xx), color=GRAY, lw=1)
ax.set_xlabel("2015年度 副校長・教頭に占める女性の割合（%）"); ax.set_ylabel("2025年度 校長に占める女性の割合（%）")
ax.set_title(f"10年前に女性の副校長・教頭が多かった県ほど、今の女性校長が多い（小学校、r={np.corrcoef(a,b)[0,1]:.2f}）", fontsize=11)
save(fig, "a196_vice_to_head.png")
