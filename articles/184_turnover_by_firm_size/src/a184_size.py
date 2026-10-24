"""事業所の規模が小さいほど、新卒の離職率は高いのか（新規学卒就職者の事業所規模別離職状況）"""
from common import *

d = load("turnover_3y_by_size.csv")
SZ = ["5人未満", "5～29人", "30～99人", "100～499人", "500～999人", "1,000人以上"]
MID = dict(zip(SZ, [2.5, np.sqrt(5 * 29), np.sqrt(30 * 99), np.sqrt(100 * 499), np.sqrt(500 * 999), 2000]))  # 代表値（幾何平均、端は仮定）
s = d[d["size"].isin(SZ)].copy()
s["hires_est"] = s.separated_within3y / s.rate_within3y_pct * 100  # 規模別の就職者数（離職者数÷離職率から逆算）
tot = d[d["size"] == "規模計"].set_index(["education", "graduated_march"])
s["hire_share_pct"] = s.hires_est / s.groupby(["education", "graduated_march"]).hires_est.transform("sum") * 100
s.round(2).to_csv(RES / "a184_by_size.csv", index=False, encoding="utf-8")
L = []
chk = s.groupby(["education", "graduated_march"]).hires_est.sum() / tot.hires_total
L.append(f"逆算した就職者数の合計÷就職者数：{chk.min():.3f}〜{chk.max():.3f}")
reg = []
for (e, y), g in s.groupby(["education", "graduated_march"]):
    x = np.log10(g["size"].map(MID)); b, a = np.polyfit(x, g.rate_within3y_pct, 1)
    r = np.corrcoef(x, g.rate_within3y_pct)[0, 1]
    reg.append((e, y, round(b, 2), round(a, 2), round(r, 3)))
reg = pd.DataFrame(reg, columns=["education", "graduated_march", "slope_per_10x", "intercept", "r"])
reg.to_csv(RES / "a184_regression.csv", index=False, encoding="utf-8")
for e in ["大学", "高校"]:
    g = s[(s.education == e) & (s.graduated_march == 2023)].set_index("size")
    L.append(f"{e} 2023年3月卒 3年以内：規模計 {tot.loc[(e,2023),'rate_within3y_pct']}、" + "、".join(f"{k} {g.loc[k,'rate_within3y_pct']}" for k in SZ)
             + f"；5人未満÷1000人以上 {g.loc['5人未満','rate_within3y_pct']/g.loc['1,000人以上','rate_within3y_pct']:.2f}倍、差 {g.loc['5人未満','rate_within3y_pct']-g.loc['1,000人以上','rate_within3y_pct']:.1f}pt")
    L.append(f"   就職者の規模別割合(2023)：" + "、".join(f"{k} {g.loc[k,'hire_share_pct']:.1f}%" for k in SZ) + f"；100人未満計 {g.loc[SZ[:3],'hire_share_pct'].sum():.1f}%")
    rr = reg[(reg.education == e) & (reg.graduated_march == 2023)].iloc[0]
    L.append(f"   回帰(2023)：規模10倍で {rr.slope_per_10x}pt、r={rr.r}；全コホートの傾き {reg[reg.education==e].slope_per_10x.min()}〜{reg[reg.education==e].slope_per_10x.max()}、r最小 {reg[reg.education==e].r.max():.3f}（絶対値最小）")
    w = s[s.education == e].pivot(index="graduated_march", columns="size", values="rate_within3y_pct")
    gap = w["5人未満"] - w["1,000人以上"]
    L.append(f"   5人未満−1000人以上の差：2003 {gap.loc[2003]:.1f}、最小 {gap.idxmin()} {gap.min():.1f}、最大 {gap.idxmax()} {gap.max():.1f}、2023 {gap.loc[2023]:.1f}")
    L.append(f"   2003→2023：5人未満 {w.loc[2003,'5人未満']}→{w.loc[2023,'5人未満']}、1000人以上 {w.loc[2003,'1,000人以上']}→{w.loc[2023,'1,000人以上']}、規模計 {tot.loc[(e,2003),'rate_within3y_pct']}→{tot.loc[(e,2023),'rate_within3y_pct']}")
    hs = s[s.education == e].pivot(index="graduated_march", columns="size", values="hire_share_pct")
    L.append(f"   1000人以上の就職者割合：2003 {hs.loc[2003,'1,000人以上']:.1f}% → 2023 {hs.loc[2023,'1,000人以上']:.1f}%")
    # 規模構成が2003年のままなら
    w03 = (w.loc[2023, SZ] * hs.loc[2003, SZ]).sum() / 100
    L.append(f"   2023の規模別離職率×2003の規模構成 = {w03:.1f}（実際 {tot.loc[(e,2023),'rate_within3y_pct']}）")
(RES / "a184_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

lab = ["5人未満", "5〜29人", "30〜99人", "100〜499人", "500〜999人", "1,000人以上"]
# 図1 2023 棒
fig, ax = plt.subplots(figsize=(9, 4.8))
xx = np.arange(6); w_ = .38
for k, (e, c) in enumerate([("高校", ORANGE), ("大学", BLUE)]):
    g = s[(s.education == e) & (s.graduated_march == 2023)].set_index("size").loc[SZ]
    ax.bar(xx + (k - .5) * w_, g.rate_within3y_pct, w_, color=c, label=f"{e}卒（規模計 {tot.loc[(e,2023),'rate_within3y_pct']}%）")
    for i, v in enumerate(g.rate_within3y_pct):
        ax.text(i + (k - .5) * w_, v + .8, f"{v:.1f}", ha="center", fontsize=9)
ax.set_xticks(xx, lab); ax.set_ylim(0, 72); ax.set_ylabel("就職後3年以内の離職率（%）")
ax.set_xlabel("就職した事業所の規模（従業員数）"); ax.legend(frameon=False)
ax.set_title("事業所の規模別、新卒の3年以内離職率（2023年3月卒）")
save(fig, "a184_size_2023.png")
# 図2 推移（大学）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
cols = ["#0b3d91", BLUE, LIGHT, "#d6a62a", ORANGE, "#b5321a"][::-1]
for ax, e in zip(axs, ["大学", "高校"]):
    w = s[s.education == e].pivot(index="graduated_march", columns="size", values="rate_within3y_pct")
    for k, c, l in zip(SZ, cols, lab):
        ax.plot(w.index, w[k], color=c, lw=2, label=l)
    ax.plot(w.index, tot.loc[e].rate_within3y_pct, color=INK, lw=1.2, ls="--", label="規模計")
    ax.set_title(f"{e}卒"); ax.set_xlabel("卒業年（3月卒）"); ax.set_ylim(15, 72)
axs[0].set_ylabel("就職後3年以内の離職率（%）"); h, l_ = axs[0].get_legend_handles_labels(); fig.legend(h, l_, fontsize=9, frameon=False, loc="upper center", ncol=7, bbox_to_anchor=(0.5, 0.995)); fig.subplots_adjust(top=0.82)
fig.suptitle("規模別の3年以内離職率の推移（2003〜2023年3月卒）", y=1.06)
save(fig, "a184_trend.png")
# 図3 回帰
fig, ax = plt.subplots(figsize=(8.5, 4.8))
for e, c in [("高校", ORANGE), ("大学", BLUE)]:
    g = s[(s.education == e) & (s.graduated_march == 2023)]
    x = np.log10(g["size"].map(MID)); y = g.rate_within3y_pct
    rr = reg[(reg.education == e) & (reg.graduated_march == 2023)].iloc[0]
    ax.scatter(x, y, color=c, s=50, zorder=3)
    xs = np.linspace(x.min(), x.max(), 10); ax.plot(xs, rr.intercept + rr.slope_per_10x * xs, color=c, lw=1.5,
                                                    label=f"{e}卒：規模が10倍で {rr.slope_per_10x:+.1f}pt（相関 {rr.r:.2f}）")
ax.set_xticks([np.log10(MID[k]) for k in SZ], lab, fontsize=9)
ax.set_xlabel("事業所の規模（対数目盛、各区分の代表値）"); ax.set_ylabel("3年以内の離職率（%）")
ax.set_title("規模と離職率の単回帰（2023年3月卒）"); ax.legend(frameon=False)
save(fig, "a184_regression.png")
