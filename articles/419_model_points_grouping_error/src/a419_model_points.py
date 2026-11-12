"""419 契約を代表の契約にまとめて計算すると、結果はどれだけずれるか（架空の定期保険10万件）
1件ごとの計算：死亡保険金の将来の支払いの現在価値＝保険金額 × Σ v^(k+1)・(k年生きる割合)・(その年の死亡率)
まとめ方：年齢の幅×残りの期間の幅のマスに入る契約を、1つの代表の契約（年齢・期間）と保険金額の合計に置きかえる。"""
import json
import numpy as np, pandas as pd
from common import *

SEED, NPOL, NPORT = 419, 100_000, 20
LT = pd.read_csv(DATA / "life_table_2024_qx.csv"); QX = LT[LT.sex == "男"].set_index("age").qx.reindex(range(0, 106)).values
AGES = np.arange(25, 71); NMAX = 30

def a_grid(i, shock=1.0):
    """A[x-25, n]：年齢 x・残り n 年（0〜30）の、保険金額1あたりの現在価値"""
    v = 1 / (1 + i); q = np.minimum(QX * shock, 1.0); G = np.zeros((len(AGES), NMAX + 1))
    for a, x in enumerate(AGES):
        surv, acc = 1.0, 0.0
        for k in range(NMAX):
            acc += v ** (k + 1) * surv * q[x + k]; surv *= 1 - q[x + k]; G[a, k + 1] = acc
    return G

def interp(G, x, n):
    """年齢・期間が整数でないとき、まわりの4点から線形に補う"""
    xa = np.clip(x - 25, 0, len(AGES) - 1); n = np.clip(n, 0, NMAX)
    x0 = np.minimum(np.floor(xa).astype(int), len(AGES) - 2); n0 = np.minimum(np.floor(n).astype(int), NMAX - 1)
    fx, fn = xa - x0, n - n0
    return (G[x0, n0] * (1 - fx) * (1 - fn) + G[x0 + 1, n0] * fx * (1 - fn) + G[x0, n0 + 1] * (1 - fx) * fn + G[x0 + 1, n0 + 1] * fx * fn)

def portfolio(rng):
    x = np.clip(np.round(rng.normal(45, 10, NPOL)), 25, 70).astype(int)
    nmax = np.minimum(NMAX, 80 - x)
    n = np.minimum(1 + rng.binomial(29, np.clip(0.75 - 0.012 * (x - 25), 0.1, 0.9)), nmax)        # 若い人ほど長い契約
    sa = rng.lognormal(np.log(1000) + 0.012 * (45 - x), 0.8, NPOL)                               # 保険金額（万円）。若い人ほどやや大きい
    return pd.DataFrame(dict(age=x, term=n, sa=sa))

# マスの切り方：(年齢の幅, 期間の区切り)
def term_band(n, kind):
    if kind == "粗い": return np.digitize(n, [6, 11, 21])                   # 1-5, 6-10, 11-20, 21-30
    if kind == "中くらい": return (n - 1) // 3                              # 3年ごと
    return (n - 1) // 2                                                      # 2年ごと
def age_band(x, kind): return (x - 25) // {"粗い": 10, "中くらい": 5, "細かい": 2}[kind]
KINDS = ["粗い", "中くらい", "細かい"]                                      # 年齢10歳×期間4区分／5歳×3年／2歳×2年
METHODS = ["マスの真ん中", "件数で平均", "金額で重みをつけた平均", "金額で重みをつけた平均（整数に丸める）"]
SCEN = {"金利1%": (0.01, 1.0), "金利0%": (0.00, 1.0), "金利3%": (0.03, 1.0), "死亡率+10%": (0.01, 1.1)}
GR = {k: a_grid(*v) for k, v in SCEN.items()}

def model_points(P, kind, method):
    P = P.assign(ab=age_band(P.age.values, kind), tb=term_band(P.term.values, kind))
    g = P.groupby(["ab", "tb"])
    if method == "マスの真ん中":
        r = g.agg(x=("age", lambda s: (s.min() + s.max()) / 2), n=("term", lambda s: (s.min() + s.max()) / 2), sa=("sa", "sum"))
        lo = P.groupby("ab").age.agg(["min", "max"]); lt = P.groupby("tb").term.agg(["min", "max"])          # マスの端はポートフォリオ全体の区切りから
        r = r.reset_index(); r["x"] = r.ab.map((lo["min"] + lo["max"]) / 2); r["n"] = r.tb.map((lt["min"] + lt["max"]) / 2)
    elif method == "件数で平均":
        r = g.agg(x=("age", "mean"), n=("term", "mean"), sa=("sa", "sum")).reset_index()
    else:
        P = P.assign(wx=P.age * P.sa, wn=P.term * P.sa)
        r = P.groupby(["ab", "tb"]).agg(wx=("wx", "sum"), wn=("wn", "sum"), sa=("sa", "sum")).reset_index(); r["x"] = r.wx / r.sa; r["n"] = r.wn / r.sa
        if "丸める" in method: r["x"] = np.round(r.x); r["n"] = np.round(r.n)
    return r

rows = []
for pi in range(NPORT):
    P = portfolio(np.random.default_rng([SEED, pi]))
    if pi == 0: P.head(2000).round(1).to_csv(DATA / "example_policies_2000.csv", index=False)
    full = {k: float((P.sa.values * G[P.age.values - 25, P.term.values]).sum()) for k, G in GR.items()}
    old = P.age.values >= 60; full_old = float((P.sa.values * GR["金利1%"][P.age.values - 25, P.term.values])[old].sum())
    for kind in KINDS:
        for m in METHODS:
            r = model_points(P, kind, m)
            mp = {k: float((r.sa.values * interp(G, r.x.values, r.n.values)).sum()) for k, G in GR.items()}
            rows.append(dict(ポートフォリオ=pi, マス=kind, 代表の数=len(r), まとめ方=m, 全件=full["金利1%"], 代表=mp["金利1%"], ずれ_パーセント=100 * (mp["金利1%"] / full["金利1%"] - 1),
                             **{f"ずれ_{k}": 100 * (mp[k] / full[k] - 1) for k in SCEN if k != "金利1%"},
                             **{f"変化分のずれ_{k}": 100 * ((mp[k] - mp["金利1%"]) / (full[k] - full["金利1%"]) - 1) for k in SCEN if k != "金利1%"},
                             全件の変化_金利3=100 * (full["金利3%"] / full["金利1%"] - 1)))
T = pd.DataFrame(rows); T.to_csv(RES / "errors_by_portfolio.csv", index=False)
num = [c for c in T.columns if c.startswith("ずれ") or c.startswith("変化分")]
S = T.groupby(["マス", "まとめ方"])[["代表の数"] + num].agg(["mean", "min", "max"])
S.columns = [f"{a}_{b}" for a, b in S.columns]; S = S.reindex(pd.MultiIndex.from_product([KINDS, METHODS])).reset_index().rename(columns={"level_0": "マス", "level_1": "まとめ方"})
S.to_csv(RES / "error_summary.csv", index=False)

# 1件あたりの現在価値は、年齢と期間でどう曲がっているか（例の表）
G = GR["金利1%"]; curve = pd.DataFrame({f"残り{n}年": G[:, n] * 1000 for n in (5, 10, 20, 30)}, index=AGES).rename_axis("年齢")
curve.round(2).to_csv(RES / "pv_per_1000_by_age_term.csv")

# マスを細かくしたときのずれ（年齢の幅だけを変える。期間は1年ごと）
rows = []
P = portfolio(np.random.default_rng([SEED, 0])); fullv = float((P.sa.values * G[P.age.values - 25, P.term.values]).sum())
for w in [1, 2, 3, 5, 10, 15, 23, 46]:
    Q = P.assign(ab=(P.age - 25) // w)
    for lab, f in [("件数で平均", lambda d: d.age.mean()), ("金額で重みをつけた平均", lambda d: (d.age * d.sa).sum() / d.sa.sum())]:
        r = Q.groupby(["ab", "term"]).apply(lambda d: pd.Series(dict(x=f(d), sa=d.sa.sum()))).reset_index()
        rows.append(dict(年齢の幅=w, まとめ方=lab, 代表の数=len(r), ずれ_パーセント=100 * ((r.sa.values * interp(G, r.x.values, r.term.values.astype(float))).sum() / fullv - 1)))
W = pd.DataFrame(rows); W.to_csv(RES / "error_by_age_band_width.csv", index=False)

s = lambda k, m, c: float(S[(S.マス == k) & (S.まとめ方 == m)][c].iloc[0])
main = dict(条件=dict(契約数=NPOL, ポートフォリオの数=NPORT, 乱数の種=SEED, 生命表="令和6年簡易生命表（男）"),
            ずれ_金利1={k: {m: dict(平均=s(k, m, "ずれ_パーセント_mean"), 最小=s(k, m, "ずれ_パーセント_min"), 最大=s(k, m, "ずれ_パーセント_max"), 代表の数=s(k, m, "代表の数_mean")) for m in METHODS} for k in KINDS},
            変化分のずれ_金利3={k: {m: s(k, m, "変化分のずれ_金利3%_mean") for m in METHODS} for k in KINDS},
            変化分のずれ_金利0={k: {m: s(k, m, "変化分のずれ_金利0%_mean") for m in METHODS} for k in KINDS},
            変化分のずれ_死亡率={k: {m: s(k, m, "変化分のずれ_死亡率+10%_mean") for m in METHODS} for k in KINDS},
            全件の変化_金利3=float(T.全件の変化_金利3.mean()), 年齢の幅=W.round(3).to_dict("records"))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

MC = {METHODS[0]: GRAY, METHODS[1]: BLUE, METHODS[2]: ORANGE, METHODS[3]: GREEN}
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))
x = np.arange(3); w = 0.2
for j, m in enumerate(METHODS):
    v = [s(k, m, "ずれ_パーセント_mean") for k in KINDS]
    ax[0].bar(x + (j - 1.5) * w, v, w, color=MC[m], label=m)
    for xi, vv in zip(x + (j - 1.5) * w, v): ax[0].text(xi, vv + (0.15 if vv >= 0 else -0.5), f"{vv:+.1f}", ha="center", fontsize=7.5)
ax[0].axhline(0, color=INK, lw=0.8); ax[0].set_xticks(x); ax[0].set_xticklabels([f"{k}\n{d}\n代表 約{s(k, METHODS[1], '代表の数_mean'):.0f}件" for k, d in zip(KINDS, ["10歳×期間4区分", "5歳×3年", "2歳×2年"])], fontsize=8.5); ax[0].set_ylim(-5, 13); ax[0].set_ylabel("全件の計算とのずれ（%）")
ax[0].set_title("現在価値の合計のずれ（金利1%、20回の平均）"); ax[0].legend(fontsize=7.5, frameon=False)
for n, col in zip((5, 10, 20, 30), [LIGHT, BLUE, GREEN, ORANGE]): ax[1].plot(AGES, curve[f"残り{n}年"], color=col, label=f"残り{n}年")
ax[1].set_xlabel("年齢"); ax[1].set_ylabel("保険金額1,000あたりの現在価値"); ax[1].set_title("1件ごとの現在価値は、年齢に対して下に凸の曲線"); ax[1].legend(fontsize=8, frameon=False)
save(fig, "a419_total_error_by_grouping.png", "架空の定期保険10万件。死亡率は厚生労働省「令和6年簡易生命表」（男）。作成者が計算")

fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))
for a, (col, ttl) in zip(ax, [("変化分のずれ_金利3%_mean", "金利を1%→3%にしたときの「変化の大きさ」のずれ"), ("変化分のずれ_死亡率+10%_mean", "死亡率を1.1倍にしたときの「変化の大きさ」のずれ")]):
    for j, m in enumerate(METHODS):
        v = [s(k, m, col) for k in KINDS]
        a.bar(x + (j - 1.5) * w, v, w, color=MC[m], label=m)
        for xi, vv in zip(x + (j - 1.5) * w, v): a.text(xi, vv + (0.3 if vv >= 0 else -1.2), f"{vv:+.1f}", ha="center", fontsize=7.5)
    a.axhline(0, color=INK, lw=0.8); a.set_xticks(x); a.set_xticklabels(KINDS); a.set_ylabel("全件で計算した変化とのずれ（%）"); a.set_title(ttl, fontsize=11); lo, hi = a.get_ylim(); a.set_ylim(lo - 0.12 * (hi - lo), hi + 0.05 * (hi - lo))
ax[0].legend(fontsize=7.5, frameon=False)
save(fig, "a419_sensitivity_error.png", "変化の大きさ＝前提を変えたときの現在価値の増減。作成者が計算")

fig, ax = plt.subplots(figsize=(8.5, 4.3))
for lab, col in [("件数で平均", BLUE), ("金額で重みをつけた平均", ORANGE)]:
    d = W[W.まとめ方 == lab]; ax.plot(d.年齢の幅, d.ずれ_パーセント, "o-", color=col, label=lab)
ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("1つにまとめる年齢の幅（歳）"); ax.set_ylabel("全件の計算とのずれ（%）"); ax.set_title("年齢の幅を広げるほど、ずれは大きくなる（期間は1年ごとのまま）"); ax.legend(fontsize=8.5, frameon=False)
save(fig, "a419_error_by_age_band_width.png", "架空の定期保険10万件（1つのポートフォリオ）。作成者が計算")
print(json.dumps(main, ensure_ascii=False, indent=1))
