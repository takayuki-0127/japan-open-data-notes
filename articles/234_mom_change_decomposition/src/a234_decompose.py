"""234：前月比の増減を「店舗数×日数×1店1日あたり客数×客単価」に分ける。
順番に置き換える方法（24通り）・対数平均の方法（LMDI）・全順番の平均（シャープレイ値）を比べる。
データはコンビニ正会員チェーンの全店の月次（日本フランチャイズチェーン協会）"""
import itertools, calendar
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

d = pd.read_csv(DATA / "jfa_cvs_monthly.csv")
d["days"] = [calendar.monthrange(y, m)[1] for y, m in zip(d.year, d.month)]
d["cps"] = d.cust_all * 1000 / d.stores / d.days           # 1店1日あたり客数（人）
d["sales_calc"] = d.stores * d.days * d.cps * d.price_all / 1e6   # 百万円
F = ["stores", "days", "cps", "price_all"]
LAB = {"stores": "店舗数", "days": "日数", "cps": "1店1日あたり客数", "price_all": "客単価"}
ident = float((d.sales_calc / d.sales_all - 1).abs().max())

def seq(a, b, order):
    """順番に置き換える：order の順に、前月の値を今月の値に置き換えたときの増え方"""
    cur = {f: a[f] for f in F}; out = {}
    prod = lambda c: np.prod([c[f] for f in F]) / 1e6
    for f in order:
        before = prod(cur); cur[f] = b[f]; out[f] = prod(cur) - before
    return out

def lmdi(a, b):
    """対数平均（LMDI-I）：寄与 = L(今月, 前月) × log(今月の要因 / 前月の要因)。合計は増減にぴったり一致"""
    sa, sb = np.prod([a[f] for f in F]) / 1e6, np.prod([b[f] for f in F]) / 1e6
    L = (sb - sa) / np.log(sb / sa)
    return {f: L * np.log(b[f] / a[f]) for f in F}

rows = []
for i in range(1, len(d)):
    a, b = d.iloc[i - 1], d.iloc[i]
    allp = [seq(a, b, o) for o in itertools.permutations(F)]
    sh = {f: np.mean([p[f] for p in allp]) for f in F}
    lm = lmdi(a, b); s1 = seq(a, b, F)
    for f in F:
        v = [p[f] for p in allp]
        rows.append({"ym": b.ym, "factor": f, "lmdi": lm[f], "shapley": sh[f], "seq_default": s1[f], "seq_min": min(v), "seq_max": max(v),
                     "change": b.sales_calc - a.sales_calc})
r = pd.DataFrame(rows); r.to_csv(RES / "mom_decomposition.csv", index=False)

# 前年同月比も同じように分ける（日数の違いはほぼ消える）
yrows = []
for i in range(12, len(d)):
    a, b = d.iloc[i - 12], d.iloc[i]; lm = lmdi(a, b)
    for f in F: yrows.append({"ym": b.ym, "factor": f, "lmdi": lm[f], "change": b.sales_calc - a.sales_calc})
y = pd.DataFrame(yrows); y.to_csv(RES / "yoy_decomposition.csv", index=False)

# まとめの数字
w = r.pivot(index="ym", columns="factor", values="lmdi")
share_abs = w.abs().div(w.abs().sum(axis=1), axis=0)
wy = y.pivot(index="ym", columns="factor", values="lmdi"); share_abs_y = wy.abs().div(wy.abs().sum(axis=1), axis=0)
r["spread"] = r.seq_max - r.seq_min
spread_rel = r.groupby("ym").apply(lambda g: g.spread.max() / abs(g.change.iloc[0]) if g.change.iloc[0] != 0 else np.nan)
tgt = "2025-12"
m = r[r.ym == tgt].set_index("factor")
summ = {"identity_max_rel_err": ident, "n_months": int(r.ym.nunique()),
        "mom_days_share_mean": float(share_abs["days"].mean()), "yoy_days_share_mean": float(share_abs_y["days"].mean()),
        "mom_days_largest_months": int((share_abs.idxmax(axis=1) == "days").sum()),
        "yoy_days_largest_months": int((share_abs_y.idxmax(axis=1) == "days").sum()),
        "lmdi_vs_shapley_max_abs": float((r.lmdi - r.shapley).abs().max()),
        "lmdi_vs_shapley_max_rel_change": float(((r.lmdi - r.shapley).abs() / r.change.abs()).replace(np.inf, np.nan).max()),
        "seq_spread_over_change_median": float(spread_rel.median()), "seq_spread_over_change_p90": float(spread_rel.quantile(0.9)),
        tgt: {f: {k: round(float(m.loc[f, k]), 1) for k in ["lmdi", "shapley", "seq_default", "seq_min", "seq_max"]} for f in F},
        tgt + "_change": round(float(m.change.iloc[0]), 1)}
pd.Series(summ).to_json(RES / "summary.json", force_ascii=False, indent=1)
print(pd.Series(summ).to_string())

# 図1：2025年12月の前月比の分解（LMDI）
fig, ax = plt.subplots(figsize=(8, 4.2))
a, b = d[d.ym == "2025-11"].iloc[0], d[d.ym == "2025-12"].iloc[0]
vals = [m.loc[f, "lmdi"] for f in F]; base = a.sales_calc
ax.bar(0, base / 1e4, color=GRAY); cum = base
for i, (f, v) in enumerate(zip(F, vals), 1):
    ax.bar(i, v / 1e4, bottom=(cum if v >= 0 else cum + v) / 1e4, color=BLUE if v >= 0 else ORANGE)
    ax.text(i, (cum + max(v, 0)) / 1e4 + 0.08, f"{v / 100:+,.0f}億円", ha="center", fontsize=9.5); cum += v
ax.bar(5, b.sales_calc / 1e4, color=GREEN)
ax.set_xticks(range(6)); ax.set_xticklabels(["11月", "店舗数", "日数\n（30→31日）", "1店1日\nあたり客数", "客単価", "12月"])
ax.set_ylim(base / 1e4 * 0.93, b.sales_calc / 1e4 * 1.02); ax.set_ylabel("売上（兆円）")
ax.set_title(f"2025年12月の売上は前月より{(b.sales_calc - base) / 100:,.0f}億円増。いちばん効いたのは客単価")
save(fig, "a234_waterfall.png")

# 図2：同じ月でも、置き換える順番で寄与が変わる（24通りの幅）
fig, ax = plt.subplots(figsize=(8, 3.8))
for i, f in enumerate(F):
    ax.plot([m.loc[f, "seq_min"] / 100, m.loc[f, "seq_max"] / 100], [i, i], color=GRAY, lw=6, solid_capstyle="round", alpha=.5)
    ax.plot(m.loc[f, "seq_default"] / 100, i, "o", color=ORANGE, ms=8, label="店舗→日数→客数→単価の順" if i == 0 else None)
    ax.plot(m.loc[f, "lmdi"] / 100, i, "D", color=BLUE, ms=7, label="対数平均（LMDI）" if i == 0 else None)
    ax.plot(m.loc[f, "shapley"] / 100, i, "|", color=INK, ms=16, mew=2, label="24通りの平均（シャープレイ値）" if i == 0 else None)
ax.set_yticks(range(4)); ax.set_yticklabels([LAB[f] for f in F]); ax.invert_yaxis()
ax.axvline(0, color=GRAY, lw=0.8); ax.set_xlabel("前月からの増減への寄与（億円）")
ax.set_title("2025年12月：置き換える順番（24通り）で、寄与は灰色の幅だけ動く")
ax.legend(frameon=False, fontsize=8.5, loc="center")
save(fig, "a234_order.png")

# 図3：2025年の各月、前月比と前年同月比の分解（LMDI）
cols = {"stores": GRAY, "days": ORANGE, "cps": BLUE, "price_all": GREEN}
fig, axs = plt.subplots(1, 2, figsize=(9, 3.9), sharey=True)
for ax, tab, ttl in [(axs[0], w, "前月比の分解"), (axs[1], wy, "前年同月比の分解")]:
    t = tab.loc["2025-01":"2025-12"] / 100; x = np.arange(len(t))
    pos = np.zeros(len(t)); neg = np.zeros(len(t))
    for f in F:
        v = t[f].values
        ax.bar(x, np.where(v > 0, v, 0), bottom=pos, color=cols[f], label=LAB[f]); pos += np.where(v > 0, v, 0)
        ax.bar(x, np.where(v < 0, v, 0), bottom=neg, color=cols[f]); neg += np.where(v < 0, v, 0)
    ax.plot(x, t.sum(axis=1), "k.", ms=6)
    ax.axhline(0, color=GRAY, lw=.8); ax.set_xticks(x); ax.set_xticklabels([f"{i}月" for i in range(1, 13)], fontsize=8)
    ax.set_title(ttl, fontsize=11)
axs[0].set_ylabel("寄与（億円）、黒い点は増減の合計"); axs[1].legend(frameon=False, fontsize=8.5, loc="lower left")
fig.suptitle("2025年：前月比は日数（オレンジ）に振り回される。前年同月比ではほぼ消える", fontsize=12, y=1.03)
save(fig, "a234_monthly.png", y=-0.01)
