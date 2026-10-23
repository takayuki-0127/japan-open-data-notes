"""W1：賃金カーブ（年齢とともに給与がどれだけ上がるか）は都道府県でどれだけ違うか。違いのうち、企業規模の構成で説明できる分はどれだけか"""
from common import *
a = load_age()
a.to_csv(RES / "w1_age_long.csv", index=False, encoding="utf-8-sig")
MID = dict(zip(AGES, AGE_MID))


def curve(d, sex, size="計"):
    return d[(d["size"] == size) & (d.sex == sex) & (d.ageg != "all")].pivot(index="pref", columns="ageg", values="scheduled")[AGES].reindex(PREFS)


def wavg(d, sex, size="計"):
    """47都道府県を労働者数で重み付けした平均（全国の近似）"""
    x = d[(d["size"] == size) & (d.sex == sex) & (d.ageg != "all")].dropna(subset=["scheduled", "workers"])
    g = x.groupby("ageg").apply(lambda t: np.average(t.scheduled, weights=t.workers))
    return g[AGES]


# 1) 傾き：50〜54歳の所定内給与 ÷ 20〜24歳
r = pd.DataFrame(index=PREFS)
for sex, k in [("男", "m"), ("女", "f")]:
    c = curve(a, sex); r[k] = c["50-54"] / c["20-24"]; r[k + "_2024"] = c["20-24"]; r[k + "_5054"] = c["50-54"]
nat = {s: wavg(a, s) for s in ["男", "女"]}
nat_ratio = {s: nat[s]["50-54"] / nat[s]["20-24"] for s in nat}
gap_age = (nat["女"] / nat["男"] * 100).round(1)
gap_age.to_csv(RES / "w1_gender_ratio_by_age.csv", header=["women_per_men_pct"], encoding="utf-8-sig")

# 2) 大企業（1,000人以上）で働く男性の割合
w = a[(a.sex == "男") & (a.ageg == "all")].pivot(index="pref", columns="size", values="workers")
r["big"] = w["1000+"] / w["計"] * 100
b, c0 = np.polyfit(r.big, r.m, 1); corr = r[["m", "big"]].corr().iloc[0, 1]

# 3) 規模別の傾き（都道府県内で比べる）
bysize = {}
for size in ["1000+", "100-999", "10-99"]:
    c = curve(a, "男", size); bysize[size] = (c["50-54"] / c["20-24"])
bs = pd.DataFrame(bysize); bs.to_csv(RES / "w1_ratio_by_size_men.csv", encoding="utf-8-sig")

# 4) 直接標準化：各年齢で「規模の構成」を全国（47都道府県計）と同じにしたら傾きはどうなるか
x = a[(a.sex == "男") & (a["size"] != "計") & (a.ageg.isin(["20-24", "50-54"]))].copy()
mix = x.groupby(["ageg", "size"]).workers.sum(); mix = mix / mix.groupby(level=0).transform("sum")
x["w_nat"] = [mix[(g, s)] for g, s in zip(x.ageg, x["size"])]
x["missing"] = x.scheduled.isna()
std = x.dropna(subset=["scheduled"]).groupby(["pref", "ageg"]).apply(lambda t: np.sum(t.scheduled * t.w_nat) / t.w_nat.sum()).unstack()
r["m_std"] = (std["50-54"] / std["20-24"]).reindex(PREFS)
miss = x.groupby("pref").missing.sum(); r["n_missing_cells"] = miss.reindex(PREFS)
r.round(3).to_csv(RES / "w1_prefs.csv", encoding="utf-8-sig")

s = {"nat_ratio_men": nat_ratio["男"], "nat_ratio_women": nat_ratio["女"],
     "men_min_pref": r.m.idxmin(), "men_min": r.m.min(), "men_max_pref": r.m.idxmax(), "men_max": r.m.max(),
     "women_min_pref": r.f.idxmin(), "women_min": r.f.min(), "women_max_pref": r.f.idxmax(), "women_max": r.f.max(),
     "sd_men": r.m.std(), "sd_men_std": r.m_std.std(), "range_men": r.m.max() - r.m.min(), "range_men_std": r.m_std.max() - r.m_std.min(),
     "corr_men_big": corr, "slope_per10pt": b * 10, "corr_m_f": r[["m", "f"]].corr().iloc[0, 1],
     "median_ratio_1000": bs["1000+"].median(), "median_ratio_100": bs["100-999"].median(), "median_ratio_10": bs["10-99"].median(),
     "share_pref_big_steeper_than_small": (bs["1000+"] > bs["10-99"]).mean() * 100,
     "tokyo_m": r.loc["東京", "m"], "tokyo_m_std": r.loc["東京", "m_std"], "aomori_m": r.loc["青森", "m"], "aomori_m_std": r.loc["青森", "m_std"],
     "n_missing_cells_total": int(miss.sum()),
     "women_per_men_2024": gap_age["20-24"], "women_per_men_5054": gap_age["50-54"]}
pd.Series(s).to_csv(RES / "w1_summary.csv", header=["value"]); print(pd.Series(s))

note = "（一般労働者。所定内給与額＝残業代や賞与を除く月給。企業規模10人以上）"
# 図1 カーブ
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for ax, sex, col in [(axes[0], "男", BLUE), (axes[1], "女", ORANGE)]:
    c = curve(a, sex); xs = AGE_MID
    for p in PREFS: ax.plot(xs, c.loc[p] / 10, color=GRAY, lw=0.6, alpha=0.5)
    ax.plot(xs, nat[sex] / 10, color=col, lw=2.6, label="47都道府県の平均")
    for p, ls in [("東京", "-"), ("青森", "--")]:
        ax.plot(xs, c.loc[p] / 10, color=INK, lw=1.4, ls=ls, label=p)
    ax.set_title(f"{sex}性"); ax.set_xlabel("年齢"); ax.legend(frameon=False, fontsize=9, loc="upper left")
axes[0].set_ylabel("所定内給与（万円／月）")
fig.suptitle("年齢別の月給：男性は50代まで大きく上がり、女性は上がり方が小さい", y=1.02)
fig.text(0.01, -0.04, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "w1_curves.png"); plt.close(fig)

# 図2 傾きの順位
o = r.sort_values("m")
fig, ax = plt.subplots(figsize=(8, 10))
ax.hlines(range(47), o.f, o.m, color=LIGHT, lw=1)
ax.scatter(o.m, range(47), color=BLUE, s=22, label="男性", zorder=3); ax.scatter(o.f, range(47), color=ORANGE, s=22, label="女性", zorder=3)
ax.set_yticks(range(47)); ax.set_yticklabels(o.index, fontsize=8)
ax.axvline(1, color=GRAY, lw=0.8)
ax.set_xlabel("50〜54歳の月給 ÷ 20〜24歳の月給（倍）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("賃金カーブの傾き：男性1.5〜2.0倍、女性1.1〜1.5倍")
fig.text(0.01, -0.02, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "w1_steep.png"); plt.close(fig)

# 図3 大企業割合
fig, ax = plt.subplots(figsize=(8, 5.2))
ax.scatter(r.big, r.m, color=BLUE, s=24)
xx = np.linspace(r.big.min(), r.big.max(), 10); ax.plot(xx, b * xx + c0, color=INK, lw=1)
for p in ["東京", "神奈川", "愛知", "青森", "島根", "高知", "鳥取", "宮城"]:
    ax.annotate(p, (r.loc[p, "big"], r.loc[p, "m"]), xytext=(4, 2), textcoords="offset points", fontsize=8.5)
ax.set_xlabel("1,000人以上の企業で働く男性の割合（%）"); ax.set_ylabel("男性の賃金カーブの傾き（倍）")
ax.set_title(f"大企業で働く人が多い県ほど、カーブが急（相関 {corr:.2f}）")
fig.text(0.01, -0.04, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "w1_bigfirm.png"); plt.close(fig)

# 図4 標準化の前後
o = r.sort_values("m")
fig, ax = plt.subplots(figsize=(8, 10))
ax.hlines(range(47), o.m_std, o.m, color=LIGHT, lw=1)
ax.scatter(o.m, range(47), color=BLUE, s=22, label="実際", zorder=3)
ax.scatter(o.m_std, range(47), color=GREEN, s=22, marker="D", label="企業規模の構成を全国並みにした場合", zorder=3)
ax.set_yticks(range(47)); ax.set_yticklabels(o.index, fontsize=8)
ax.set_xlabel("男性：50〜54歳の月給 ÷ 20〜24歳の月給（倍）"); ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title(f"規模の構成をそろえると、ばらつき（標準偏差）は {s['sd_men']:.3f} → {s['sd_men_std']:.3f}")
fig.text(0.01, -0.02, SOURCE + "\n（直接標準化：各年齢で1,000人以上・100〜999人・10〜99人の人数比を47都道府県計に置き換えて平均）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "w1_standardize.png"); plt.close(fig)
