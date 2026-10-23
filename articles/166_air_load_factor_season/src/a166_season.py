"""国内定期航空の座席利用率は、季節でどう変わるか（2016〜2025年の月別）"""
from common import *

d = load("domestic_monthly_wide.csv")
M = [f"m{m:02d}" for m in range(1, 13)]
L = d.melt(id_vars=["section", "year", "item"], value_vars=M, var_name="m", value_name="v")
L["month"] = L.m.str[1:].astype(int)
W = L.pivot_table(index=["section", "year", "month"], columns="item", values="v").reset_index()
NORMAL = [2016, 2017, 2018, 2019, 2023, 2024, 2025]  # 2020〜2022年はコロナの影響が大きいので季節の型からは外す
tot = W[W.section == "総合計"].copy()
nrm = tot[tot.year.isin(NORMAL)]
prof = nrm.groupby("month").lf.mean()
dev = nrm.assign(dev=nrm.lf - nrm.groupby("year").lf.transform("mean")).groupby("month").dev.mean()
# 旅客数と座席数の季節指数（各年の月平均=100）
for c in ["passengers", "seats"]:
    nrm[c + "_idx"] = nrm[c] / nrm.groupby("year")[c].transform("mean") * 100
idx = nrm.groupby("month")[["passengers_idx", "seats_idx"]].mean()
ann = tot.groupby("year").lf.mean()
sec = W[W.year.isin(NORMAL)].groupby(["section", "month"]).lf.mean().unstack(0)
L_ = []
L_.append("季節の型（2016〜19・2023〜25年の平均、総合計の座席利用率%）: " + "、".join(f"{m}月 {prof[m]:.1f}" for m in range(1, 13)))
L_.append("年平均からの差（ポイント）: " + "、".join(f"{m}月 {dev[m]:+.1f}" for m in range(1, 13)))
L_.append(f"最高 {dev.idxmax()}月 {dev.max():+.1f}、最低 {dev.idxmin()}月 {dev.min():+.1f}、幅 {dev.max()-dev.min():.1f}ポイント")
L_.append("旅客数の季節指数: " + "、".join(f"{m}月 {idx.passengers_idx[m]:.0f}" for m in range(1, 13)))
L_.append("座席数の季節指数: " + "、".join(f"{m}月 {idx.seats_idx[m]:.0f}" for m in range(1, 13)))
L_.append(f"旅客数指数の幅 {idx.passengers_idx.max()-idx.passengers_idx.min():.0f}、座席数指数の幅 {idx.seats_idx.max()-idx.seats_idx.min():.0f}")
L_.append("年平均の座席利用率（単純平均）: " + "、".join(f"{y} {ann[y]:.1f}" for y in ann.index))
for s in sec.columns:
    v = sec[s]
    L_.append(f"{s}: 平均 {v.mean():.1f}、最高 {v.idxmax()}月 {v.max():.1f}、最低 {v.idxmin()}月 {v.min():.1f}、幅 {v.max()-v.min():.1f}")
for y in [2019, 2025]:
    t = tot[tot.year == y].set_index("month").lf
    L_.append(f"{y}年: 8月 {t[8]:.1f}、1月 {t[1]:.1f}、4月 {t[4]:.1f}、12月 {t[12]:.1f}")
out = W.copy(); out.to_csv(RES / "a166_monthly_long.csv", index=False, encoding="utf-8")
pd.DataFrame({"lf_mean": prof, "lf_dev": dev, "passengers_idx": idx.passengers_idx, "seats_idx": idx.seats_idx}).round(2).to_csv(RES / "a166_season_profile.csv", encoding="utf-8")
sec.round(2).to_csv(RES / "a166_section_profile.csv", encoding="utf-8")
(RES / "a166_summary.txt").write_text("\n".join(L_), encoding="utf-8"); print("\n".join(L_))

mlab = [f"{m}月" for m in range(1, 13)]
# 図1：年ごとの月別座席利用率（ふだんの年）と平均
fig, ax = plt.subplots(figsize=(9.5, 4.6))
for y in NORMAL:
    t = tot[tot.year == y].set_index("month").lf
    ax.plot(range(1, 13), t.values, color=LIGHT if y < 2023 else "#7fb0e6", lw=1.1)
    ax.text(12.15, t[12], str(y), fontsize=8, color=GRAY, va="center")
ax.plot(range(1, 13), prof.values, color=BLUE, lw=3, marker="o", label="平均（2016〜19・2023〜25年）")
ax.set_xticks(range(1, 13)); ax.set_xticklabels(mlab); ax.set_ylabel("座席利用率（%）"); ax.set_ylim(55, 92)
ax.legend(frameon=False, loc="upper left"); ax.set_title("国内線の座席利用率は8月がいちばん高く、4月と1月が低い")
save(fig, "a166_profile.png")

# 図2：年×月のヒートマップ（2016〜2025年）
H = tot.pivot(index="year", columns="month", values="lf")
fig, ax = plt.subplots(figsize=(9.5, 4.8))
im = ax.imshow(H.values, cmap="Blues", vmin=15, vmax=90, aspect="auto")
ax.set_xticks(range(12)); ax.set_xticklabels(mlab); ax.set_yticks(range(len(H))); ax.set_yticklabels(H.index)
for i in range(H.shape[0]):
    for j in range(12):
        v = H.values[i, j]; ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 62 else INK)
cb = fig.colorbar(im, ax=ax, fraction=0.03); cb.set_label("座席利用率（%）")
ax.set_title("月別の座席利用率（2016〜2025年）。2020〜22年はコロナで大きく下がった")
save(fig, "a166_heatmap.png")

# 図3：旅客数と座席数の季節指数
fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.plot(range(1, 13), idx.passengers_idx, color=ORANGE, lw=2.5, marker="o", label="旅客数")
ax.plot(range(1, 13), idx.seats_idx, color=GRAY, lw=2.5, marker="s", label="座席数")
ax.axhline(100, color=INK, lw=0.6)
ax.set_xticks(range(1, 13)); ax.set_xticklabels(mlab); ax.set_ylabel("季節指数（その年の月平均=100）")
ax.legend(frameon=False); ax.set_title("座席数の増減は旅客数の半分ほど。旅客数の波が利用率の波になる")
save(fig, "a166_seats_vs_pax.png")
