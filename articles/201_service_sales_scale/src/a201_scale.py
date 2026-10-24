"""A201 サービス業の売上は、事業所の規模とどう比例するか（両対数回帰）"""
from common import *

tot, s = load()
s["lx"], s["ly"] = np.log10(s.w_per), np.log10(s.sales_per)

# industry-by-industry slope
rows = []
for (c, nm), g in s.groupby(["code", "name"]):
    if len(g) < 4: continue
    b, a = np.polyfit(g.lx, g.ly, 1)
    r2 = np.corrcoef(g.lx, g.ly)[0, 1] ** 2
    sm, lg = g.iloc[0], g.iloc[-1]
    rows.append(dict(code=c, name=nm, n_cls=len(g), slope=b, r2=r2,
                     small_cls=sm.cls2, small_spw=sm.sales_per_w, large_cls=lg.cls2, large_spw=lg.sales_per_w,
                     ratio_large_small=lg.sales_per_w / sm.sales_per_w))
r = pd.DataFrame(rows).sort_values("slope", ascending=False)
r.round(3).to_csv(RES / "slopes_by_industry.csv", index=False)

# pooled with industry fixed effects (within transformation)
w = s.copy()
w["lxd"] = w.lx - w.groupby("code").lx.transform("mean")
w["lyd"] = w.ly - w.groupby("code").ly.transform("mean")
bp = (w.lxd * w.lyd).sum() / (w.lxd ** 2).sum()
res = w.lyd - bp * w.lxd
se = np.sqrt((res ** 2).sum() / (len(w) - w.code.nunique() - 1) / (w.lxd ** 2).sum())
# simple pooled (no FE)
b0, a0 = np.polyfit(w.lx, w.ly, 1)

tt = tot.copy(); tt["spw"] = tt.sales_mn / tt.workers * 100
tt[["code", "name", "estab", "workers", "sales_mn", "spw"]].round(1).to_csv(RES / "industry_totals.csv", index=False)
s[["code", "name", "cls2", "estab", "workers", "sales_mn", "w_per", "sales_per", "sales_per_w"]].round(3).to_csv(RES / "size_class_long.csv", index=False)
with open(RES / "summary.txt", "w") as f:
    f.write(f"industries {r.shape[0]} points {len(s)}\n")
    f.write(f"pooled FE slope {bp:.3f} se {se:.3f}; pooled no-FE slope {b0:.3f}\n")
    f.write(f"median slope {r.slope.median():.3f}; >1: {(r.slope>1).sum()} ; <1: {(r.slope<1).sum()}\n")
    f.write(f"median ratio large/small sales per worker {r.ratio_large_small.median():.2f}\n")
    f.write(r.round(3).to_string() + "\n")
    f.write(tt[["name", "estab", "workers", "sales_mn", "spw"]].round(1).to_string() + "\n")
print(open(RES / "summary.txt").read())

# fig1 pooled scatter
fig, ax = plt.subplots(figsize=(8, 5.6))
HL = {"ソフトウェア業": ORANGE, "広告業": PURPLE, "学習塾": GREEN, "葬儀業": INK}
for c, g in s.groupby("name"):
    col = HL.get(c, LIGHT)
    ax.plot(g.w_per, g.sales_per, "-o", color=col, ms=4 if c in HL else 3, lw=1.6 if c in HL else 0.8, label=c if c in HL else None, zorder=3 if c in HL else 1)
xx = np.array([1.5, 2000]); gm = 10 ** (w.ly.mean() - w.lx.mean())
ax.plot(xx, gm * xx, "--", color=GRAY, lw=1, label="傾き1（人数に比例）")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("1事業所あたりの事業従事者数（人、対数目盛）"); ax.set_ylabel("1事業所あたりの年間売上高（百万円、対数目盛）")
ax.set_title(f"規模の区分ごとの売上（27業種、2020年調査）　業種内の傾き {bp:.2f}")
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a201_loglog.png")

# fig2 slopes
fig, ax = plt.subplots(figsize=(7.5, 8.5))
q = r.sort_values("slope")
ax.barh(q.name, q.slope, color=[ORANGE if v > 1.1 else (GRAY if v < 0.9 else BLUE) for v in q.slope])
ax.axvline(1, color=INK, lw=1, ls="--")
for i, v in enumerate(q.slope): ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8)
ax.set_xlabel("両対数の傾き（1より大きい＝大きい事業所ほど1人あたり売上が多い）"); ax.tick_params(axis="y", labelsize=9)
ax.set_title("業種ごとの傾き（2020年調査）")
save(fig, "a201_slopes.png")

# fig3 sales per worker by class for 4 industries
fig, ax = plt.subplots(figsize=(8, 4.8))
for nm, col in HL.items():
    g = s[s.name == nm]
    ax.plot(range(len(g)), g.sales_per_w, "-o", color=col, label=nm)
    ax.text(len(g) - 1 + 0.1, g.sales_per_w.iloc[-1], f"{g.sales_per_w.iloc[-1]:,.0f}", fontsize=8, color=col, va="center")
labs = s[s.name == "ソフトウェア業"].cls2.tolist()
ax.set_xticks(range(len(labs))); ax.set_xticklabels([l.replace("～", "〜\n") for l in labs], fontsize=8.5)
ax.set_yscale("log"); ax.set_ylabel("事業従事者1人あたり年間売上高（万円、対数目盛）")
ax.set_title("1人あたり売上高を規模の区分で比べる\n（目盛はソフトウェア業の区分。広告・学習塾・葬儀業は6つ目が「100人以上」）", fontsize=11.5); ax.legend(frameon=False, fontsize=9)
save(fig, "a201_per_worker.png")
