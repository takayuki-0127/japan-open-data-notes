"""W1：子どもの体力はいつから落ちたか（1964〜2025年度の推移、変化点、2019年度以降の合計点）"""
from common import *

d = load()
y = d[d.group == "青少年"].copy()
# 1964年度から定義が続いている種目（年齢×男女）。時間の種目は小さいほど良いので向きをそろえる
LONG = {"50m走": ["11", "13", "16", "19"], "ソフトボール投げ": ["11"], "ハンドボール投げ": ["13", "16", "19"],
        "握力": ["11", "13", "16", "19"], "持久走": ["13", "16", "19"]}
TIME = {"50m走", "持久走"}

ser = []
for it, ages in LONG.items():
    for a in ages:
        for s in ("男", "女"):
            x = y[(y["item"] == it) & (y.age == a) & (y.sex == s)].set_index("year")["value"].sort_index()
            if 1985 not in x.index:
                continue
            # 1985年度＝100 とした指数（良くなると大きくなる向き）
            idx = (x.loc[1985] / x * 100) if it in TIME else (x / x.loc[1985] * 100)
            ser.append(pd.DataFrame({"item": it, "age": a, "sex": s, "year": idx.index, "value": x.values, "index": idx.values}))
ser = pd.concat(ser, ignore_index=True)
ser["key"] = ser["item"] + "_" + ser["age"] + "歳_" + ser["sex"]
ser.to_csv(RES / "w1_index_1985.csv", index=False, encoding="utf-8-sig")


def hinge(x, k):
    X = np.column_stack([np.ones(len(x)), x - k, np.maximum(0, x - k)])
    return X


def best_break(t, v, ks):
    """1つの折れ目をもつ折れ線（つながった2本の直線）で、残差平方和が最小の折れ目の年"""
    best = None
    for k in ks:
        X = hinge(t, k)
        b, *_ = np.linalg.lstsq(X, v, rcond=None)
        sse = ((v - X @ b) ** 2).sum()
        if best is None or sse < best[1]:
            best = (k, sse, b)
    k, sse, b = best
    X0 = np.column_stack([np.ones(len(t)), t])
    b0, *_ = np.linalg.lstsq(X0, v, rcond=None)
    sse0 = ((v - X0 @ b0) ** 2).sum()
    return k, b[1] * 10, (b[1] + b[2]) * 10, 1 - sse / sse0


# 1) 系列ごとの最高の年と、1965〜2019年度での折れ目
rows = []
for key, g in ser.groupby("key"):
    g = g.sort_values("year")
    pk = int(g.loc[g["index"].idxmax(), "year"])
    h = g[g.year <= 2019]
    k, pre, post, r2gain = best_break(h.year.values.astype(float), h["index"].values, range(1975, 2011))
    last = g[g.year == 2025]["index"].iloc[0]
    rows.append({"series": key, "item": g["item"].iloc[0], "peak_year": pk, "peak_index": g["index"].max(),
                 "break_year": k, "slope_before_per10y": pre, "slope_after_per10y": post,
                 "sse_reduction_vs_line": r2gain, "index_2025": last})
pk = pd.DataFrame(rows).sort_values(["item", "series"])
pk.to_csv(RES / "w1_peak_break.csv", index=False, encoding="utf-8-sig")
print(pk.round(2).to_string())
print("最高の年の分布:", pk.peak_year.value_counts().sort_index().to_dict())
print("折れ目の年の中央値:", pk.break_year.median(), " 1980〜1990年に最高:", ((pk.peak_year >= 1980) & (pk.peak_year <= 1989)).sum(), "/", len(pk))

# 種目ごとの平均指数（年齢・男女を平均）
avg = ser.groupby(["item", "year"])["index"].mean().unstack(0)
avg.to_csv(RES / "w1_index_by_item.csv", encoding="utf-8-sig")
print(avg.round(1).to_string())
allavg = ser.groupby("year")["index"].median()
print("全系列の中央値:", allavg.round(1).to_dict())

# 2) 新体力テストの合計点（1998〜2025年度、毎年）
t = y[y["item"] == "合計点"].pivot_table(index="year", columns=["age", "sex"], values="value")
t = t[[c for c in [(a, s) for a in ["7", "9", "11", "13", "16", "19"] for s in ("男", "女")]]]
t.to_csv(RES / "w1_total_score.csv", encoding="utf-8-sig")
out = []
for c in t.columns:
    v = t[c]
    out.append({"age": c[0], "sex": c[1], "1998": v[1998], "max_year": int(v.idxmax()), "max": v.max(),
                "2019": v[2019], "2025": v[2025], "chg_1998_2019": v[2019] - v[1998], "chg_2019_2025": v[2025] - v[2019],
                "pct_2019_2025": (v[2025] / v[2019] - 1) * 100, "min_2020_25_year": int(v.loc[2020:].idxmin()), "min_2020_25": v.loc[2020:].min()})
ts = pd.DataFrame(out)
ts.to_csv(RES / "w1_total_change.csv", index=False, encoding="utf-8-sig")
print(ts.round(2).to_string())
# 合計点の折れ目（1998〜2025年度、各系列を1998年度＝100にして平均）
z = (t / t.loc[1998] * 100).mean(axis=1)
k, pre, post, g = best_break(z.index.values.astype(float), z.values, range(2003, 2023))
print(f"合計点（1998=100の平均）の折れ目 {k}年度、前 {pre:+.2f}/10年、後 {post:+.2f}/10年、直線に対する残差の減少 {g:.2f}")
pd.DataFrame({"year": z.index, "mean_index_1998": z.values}).to_csv(RES / "w1_total_index.csv", index=False, encoding="utf-8-sig")

# ---- 図1：種目ごとの指数（1985年度＝100）
fig, ax = plt.subplots(figsize=(8.4, 4.6))
cols = {"50m走": BLUE, "握力": GREEN, "ソフトボール投げ": ORANGE, "ハンドボール投げ": PURPLE, "持久走": INK}
for it, c in cols.items():
    s = avg[it].dropna()
    ax.plot(s.index, s.values, "-o", ms=3, color=c, label=it)
ax.axhline(100, color=GRAY, lw=0.8, ls=":")
ax.axvspan(1993.5, 1997.5, color="#eeeeee", lw=0)
ax.text(1995.5, 103, "1994〜97年度は\n表に値なし", ha="center", fontsize=8, color=GRAY)
ax.set_ylabel("1985年度＝100（大きいほど良い）")
ax.set_title("子どもの体力の推移（年齢・男女の平均、1965〜2025年度）")
ax.legend(frameon=False, ncol=3, fontsize=9, loc="lower left")
note(fig, "時間の種目は逆数で指数化。1998年度から新体力テスト")
fig.savefig(FIG / "w1_long.png"); plt.close(fig)

# ---- 図2：最高だった年度
fig, ax = plt.subplots(figsize=(8.4, 4.4))
pk2 = pk.sort_values(["peak_year", "series"])
yy = np.arange(len(pk2))
ax.scatter(pk2.peak_year, yy, color=BLUE, s=22, label="最高だった年度", zorder=3)
ax.set_yticks(yy); ax.set_yticklabels(pk2.series.str.replace("_", " "), fontsize=7)
ax.axvspan(1980, 1985, color=LIGHT, alpha=0.4, lw=0)
ax.set_title("いつが最高だったか（30系列：種目×年齢×男女）")
ax.set_xlabel("各系列で最も良かった年度（1965・70・75・80・85・89・93年度、1998年度以降は毎年）")
note(fig)
fig.savefig(FIG / "w1_peak.png"); plt.close(fig)

# ---- 図3：合計点
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=False)
for ax, s in zip(axes, ("男", "女")):
    for a, c in zip(["7", "9", "11", "13", "16", "19"], [LIGHT, BLUE, "#1c4f8f", ORANGE, GREEN, PURPLE]):
        v = t[(a, s)]
        ax.plot(v.index, v.values, color=c, lw=1.6, label=f"{a}歳")
    ax.axvline(2019, color=GRAY, ls=":", lw=1)
    ax.set_title(f"{s}子")
    ax.set_xlim(1997, 2026)
axes[0].set_ylabel("新体力テストの合計点")
axes[1].legend(frameon=False, fontsize=8, ncol=2)
fig.suptitle("新体力テストの合計点（1998〜2025年度）", y=1.02)
note(fig, "年齢区分ごとに得点表が違うので、年齢の間では比べられない")
fig.savefig(FIG / "w1_total.png"); plt.close(fig)
