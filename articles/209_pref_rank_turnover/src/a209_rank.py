"""A209 都道府県ランキングの1位はどれくらい入れ替わるのか：同じ指標コードの約10年前と最新値を、Kendallのτと1位・上位5位の入れ替わりで比べる"""
from common import *
from scipy.stats import kendalltau

d, names = load()
old = d[d.edition == 2015].sort_values("year").groupby("code").tail(1).set_index("code")   # 2015年版の最新年
new = d[d.edition == 2026].drop_duplicates("code").set_index("code")
codes = sorted(set(old.index) & set(new.index))
rows = []
for c in codes:
    a, b = old.loc[c, P].astype(float), new.loc[c, P].astype(float)
    m = a.notna() & b.notna()
    if m.sum() < 45 or a[m].nunique() < 10 or b[m].nunique() < 10:
        continue
    tau = kendalltau(a[m], b[m]).statistic
    ra, rb = a.rank(ascending=False, method="min"), b.rank(ascending=False, method="min")
    t1a, t1b = PREF[int(np.argmax(a.fillna(-np.inf)))], PREF[int(np.argmax(b.fillna(-np.inf)))]
    l1a, l1b = PREF[int(np.argmin(a.fillna(np.inf)))], PREF[int(np.argmin(b.fillna(np.inf)))]
    top5 = len(set(a.nlargest(5).index) & set(b.nlargest(5).index))
    rows.append({"code": c, "field": FIELD.get(c[0], c[0]), "name": names.set_index("code").name.get(c, ""),
                 "year_old": int(old.loc[c, "year"]), "year_new": int(new.loc[c, "year"]), "n": int(m.sum()), "tau": tau,
                 "top1_old": t1a, "top1_new": t1b, "top1_same": t1a == t1b, "last_old": l1a, "last_new": l1b, "last_same": l1a == l1b,
                 "top5_overlap": top5, "mean_abs_rank_change": float((ra - rb).abs()[m].mean())})
r = pd.DataFrame(rows)
r = r[(r.year_new - r.year_old) >= 5].reset_index(drop=True)
r.round(4).to_csv(RES / "rank_stability_by_indicator.csv", index=False)

out = []
def p(s): out.append(s); print(s)
p(f"指標数 {len(r)}  年の差 中央値{(r.year_new-r.year_old).median():.0f}年 (範囲{(r.year_new-r.year_old).min()}〜{(r.year_new-r.year_old).max()})")
p(f"旧の年 中央値{r.year_old.median():.0f} 新の年 中央値{r.year_new.median():.0f}")
p(f"τ 中央値{r.tau.median():.3f} 平均{r.tau.mean():.3f} 0.8以上{(r.tau>=.8).mean()*100:.1f}% 0.6未満{(r.tau<.6).mean()*100:.1f}% 0.4未満{(r.tau<.4).mean()*100:.1f}%")
p(f"1位が同じ {r.top1_same.sum()}/{len(r)} ({r.top1_same.mean()*100:.1f}%)  最下位が同じ {r.last_same.sum()} ({r.last_same.mean()*100:.1f}%)")
p(f"上位5県の重なり 平均{r.top5_overlap.mean():.2f} 5県とも同じ{(r.top5_overlap==5).mean()*100:.1f}% 0〜2県{(r.top5_overlap<=2).mean()*100:.1f}%")
p(f"順位の平均変化 中央値{r.mean_abs_rank_change.median():.2f}位")
g = r.groupby("field").agg(n=("tau", "size"), tau=("tau", "median"), top1=("top1_same", "mean")).sort_values("tau", ascending=False)
for f, x in g.iterrows(): p(f"  {f}: n{x.n} τ中央値{x.tau:.3f} 1位同じ{x.top1*100:.0f}%")
g.round(3).to_csv(RES / "by_field.csv")
for lab, s in [("τ上位", r.nlargest(6, "tau")), ("τ下位", r.nsmallest(8, "tau"))]:
    p(lab + ": " + " / ".join(f"{x['name']}({x.year_old}→{x.year_new}) τ{x.tau:.2f} 1位{x.top1_old}→{x.top1_new}" for _, x in s.iterrows()))
cnt = r[r.top1_same].top1_new.value_counts().head(6)
p("1位を保った県の内訳: " + " ".join(f"{k}{v}" for k, v in cnt.items()))
cnt2 = r.top1_new.value_counts().head(6)
p("新しい年の1位の県: " + " ".join(f"{k}{v}" for k, v in cnt2.items()))
ch = r[~r.top1_same]
p("1位が入れ替わった例: " + " / ".join(f"{x['name']} {x.top1_old}→{x.top1_new}(τ{x.tau:.2f})" for _, x in ch.sort_values("tau", ascending=False).head(10).iterrows()))
# τと1位の維持
for lo, hi in [(-1, .6), (.6, .8), (.8, .9), (.9, 1.01)]:
    s = r[(r.tau >= lo) & (r.tau < hi)]
    p(f"τ{lo}〜{hi}: {len(s)}指標 1位同じ{s.top1_same.mean()*100:.0f}%")
(RES / "summary.txt").write_text("\n".join(out), encoding="utf-8")

fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.hist(r.tau, bins=np.arange(0, 1.01, 0.05), color=BLUE, edgecolor="white")
ax.axvline(r.tau.median(), color=ORANGE, lw=2)
ax.text(r.tau.median() - 0.02, ax.get_ylim()[1] * .92, f"中央値 {r.tau.median():.2f}", color=ORANGE, ha="right")
ax.set_xlabel("Kendallのτ（約10年前と最新の順位の一致度、1で完全に同じ）"); ax.set_ylabel("指標の数")
ax.set_title(f"{len(r)}指標の多くは、10年たっても順位があまり変わらない")
save(fig, "a209_tau_hist.png")

fig, ax = plt.subplots(figsize=(8.5, 4.8))
gg = g.sort_values("tau")
ax.barh(gg.index, gg.tau, color=BLUE)
for i, (f, x) in enumerate(gg.iterrows()):
    ax.text(x.tau + .01, i, f"{x.tau:.2f}（{int(x.n)}指標、1位同じ{x.top1*100:.0f}%）", va="center", fontsize=9)
ax.set_xlim(0, 1.25); ax.set_xlabel("τの中央値")
ax.set_title("分野別：自然環境・人口はほぼ動かず、家計・安全・行政基盤は入れ替わりやすい")
save(fig, "a209_field.png")

fig, ax = plt.subplots(figsize=(8.5, 4.8))
bins = [(-1, .6, "0.6未満"), (.6, .8, "0.6〜0.8"), (.8, .9, "0.8〜0.9"), (.9, 1.01, "0.9以上")]
vals = [r[(r.tau >= lo) & (r.tau < hi)].top1_same.mean() * 100 for lo, hi, _ in bins]
ns = [len(r[(r.tau >= lo) & (r.tau < hi)]) for lo, hi, _ in bins]
ax.bar([b[2] for b in bins], vals, color=[LIGHT, LIGHT, BLUE, BLUE])
for i, (v, n) in enumerate(zip(vals, ns)): ax.text(i, v + 1.5, f"{v:.0f}%\n（{n}指標）", ha="center", fontsize=10)
ax.set_ylim(0, 110); ax.set_ylabel("1位の県が同じだった割合（%）"); ax.set_xlabel("τ（順位全体の一致度）")
ax.set_title(f"1位が同じだったのは{r.top1_same.mean()*100:.0f}%。全体が安定していても1位は入れ替わる")
save(fig, "a209_top1.png")
