"""429 共通の費用を部門に配る基準を変えると、何部門の損益の符号が変わるのか
架空の会社（12部門、共通費3種類）。乱数の種は429。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import *

SRC = "出所：架空のデータ（作成者が乱数で作成、seed 429）"
BASES = [("headcount", "人数"), ("sales", "売上"), ("area_m2", "面積"), ("it_hours", "使った時間")]
COSTS = ["本社費", "施設費", "システム費"]
NAT = {"本社費": "headcount", "施設費": "area_m2", "システム費": "it_hours"}


def company(rng, n=12, ratio=0.6, spread=1.0):
    """架空の会社。ratio＝共通費の合計 ÷ 部門の利益（配る前）の合計。spread＝部門ごとの「人・面積・時間の使い方」の違いの大きさ"""
    sales = np.round(rng.lognormal(np.log(400), 0.6, n)) * 1_000_000          # 部門の売上（円）
    margin = np.clip(rng.normal(0.12, 0.05, n), 0.01, 0.30)                   # 配る前の利益率
    direct = np.round(sales * margin)
    # 売上1億円あたりの人数・面積・時間は、部門の仕事の中身で違う
    head = np.maximum(1, np.round(sales / 1e8 * 6 * rng.lognormal(0, 0.5 * spread, n))).astype(int)
    area = np.maximum(10, np.round(sales / 1e8 * 120 * rng.lognormal(0, 0.7 * spread, n))).astype(int)
    hours = np.maximum(10, np.round(sales / 1e8 * 300 * rng.lognormal(0, 0.8 * spread, n))).astype(int)
    total = direct.sum() * ratio
    sh = np.round(total * np.array([0.5, 0.3, 0.2]))
    d = pd.DataFrame({"dept": [f"部門{chr(65 + i)}" for i in range(n)], "sales": sales.astype(np.int64), "direct_profit": direct.astype(np.int64),
                      "headcount": head, "area_m2": area, "it_hours": hours})
    s = pd.DataFrame({"cost_name": COSTS, "amount": sh.astype(np.int64)})
    return d, s


def allocate(d, s):
    """基準ごとの、配ったあとの利益。mix＝費用ごとに基準を変える。half＝売上と人数を半々"""
    tot = s.amount.sum(); out = {}
    for col, lab in BASES:
        out[lab] = d.direct_profit - tot * d[col] / d[col].sum()
    mix = d.direct_profit.astype(float).copy()
    for c, a in zip(s.cost_name, s.amount):
        mix = mix - a * d[NAT[c]] / d[NAT[c]].sum()
    out["費用ごとに基準を変える"] = mix
    out["売上と人数を半々"] = d.direct_profit - tot * (0.5 * d.sales / d.sales.sum() + 0.5 * d.headcount / d.headcount.sum())
    return pd.DataFrame(out).set_index(d.dept)


def flips(P, cols):
    sg = np.sign(P[cols].values)
    return int(((sg.max(axis=1) > 0) & (sg.min(axis=1) < 0)).sum())


rng = np.random.default_rng(429)
d, s = company(rng)
d.to_csv(DATA / "departments.csv", index=False); s.to_csv(DATA / "shared_costs.csv", index=False)
P = allocate(d, s)
four = [l for _, l in BASES]
P.round(0).astype(np.int64).to_csv(RES / "profit_after_by_basis.csv")
red = {c: int((P[c] < 0).sum()) for c in P.columns}
flip4 = flips(P, four); flip_all = flips(P, list(P.columns))
flip_dept = [dd for dd, row in P[four].iterrows() if row.max() > 0 and row.min() < 0]
rank = P.rank(ascending=False).astype(int)
rank.to_csv(RES / "rank_by_basis.csv")
maxshift = int((rank[four].max(axis=1) - rank[four].min(axis=1)).max())
shift3 = int(((rank[four].max(axis=1) - rank[four].min(axis=1)) >= 3).sum())
rho = {f"{a}×{b}": round(float(spearmanr(P[a], P[b])[0]), 3) for i, a in enumerate(four) for b in four[i + 1:]}
top1 = {c: P[c].idxmax() for c in P.columns}; bottom1 = {c: P[c].idxmin() for c in P.columns}
share = {lab: (d[col] / d[col].sum() * 100).round(1).tolist() for col, lab in BASES}

# ---- SQL（DuckDB）で同じ数字が出るか
con = duckdb.connect(); con.register("dept", d); con.register("shared", s)
q1 = """WITH t AS (SELECT SUM(amount) AS total FROM shared)
SELECT d.dept, d.direct_profit - t.total * d.{c} * 1.0 / SUM(d.{c}) OVER () AS profit_after FROM dept d CROSS JOIN t ORDER BY d.dept"""
chk = []
for col, lab in BASES:
    r = con.execute(q1.format(c=col)).df()
    ok = bool(np.allclose(r.profit_after.values, P[lab].values, rtol=1e-12)); assert ok
    chk.append({"基準": lab, "Python と一致": ok})
q2 = """SELECT d.dept, d.direct_profit - SUM(CASE s.cost_name WHEN '本社費' THEN s.amount * d.headcount * 1.0 / x.headcount
 WHEN '施設費' THEN s.amount * d.area_m2 * 1.0 / x.area_m2 WHEN 'システム費' THEN s.amount * d.it_hours * 1.0 / x.it_hours END) AS profit_after
FROM dept d CROSS JOIN shared s CROSS JOIN (SELECT SUM(headcount) AS headcount, SUM(area_m2) AS area_m2, SUM(it_hours) AS it_hours FROM dept) x
GROUP BY d.dept, d.direct_profit ORDER BY d.dept"""
r = con.execute(q2).df(); ok = bool(np.allclose(r.profit_after.values, P["費用ごとに基準を変える"].values, rtol=1e-12)); assert ok
chk.append({"基準": "費用ごとに基準を変える", "Python と一致": ok})
pd.DataFrame(chk).to_csv(RES / "sql_check_duckdb.csv", index=False)

# ---- 架空の会社を2,000社作る
def many(ratio, spread, n_co=2000, seed=4290):
    g = np.random.default_rng(seed)
    fl, rd, ms, rh, t1 = [], [], [], [], []
    for _ in range(n_co):
        dd, ss = company(g, ratio=ratio, spread=spread)
        PP = allocate(dd, ss)
        fl.append(flips(PP, four)); rd.append([(PP[c] < 0).sum() for c in four])
        rk = PP[four].rank(ascending=False)
        ms.append((rk.max(axis=1) - rk.min(axis=1)).max())
        rh.append(np.mean([spearmanr(PP[a], PP[b])[0] for i, a in enumerate(four) for b in four[i + 1:]]))
        t1.append(len({PP[c].idxmin() for c in four}))
    fl = np.array(fl); rd = np.array(rd)
    return {"符号が変わる部門の数（平均）": round(float(fl.mean()), 2), "符号が変わる部門の数（中央値）": float(np.median(fl)), "1部門以上で符号が変わる会社の割合": round(float((fl >= 1).mean() * 100), 1),
            "3部門以上で符号が変わる会社の割合": round(float((fl >= 3).mean() * 100), 1), "赤字の部門の数（基準ごとの平均）": [round(float(x), 2) for x in rd.mean(axis=0)],
            "順位が動く幅の最大（中央値）": float(np.median(ms)), "順位相関（平均）": round(float(np.mean(rh)), 3),
            "いちばん利益の少ない部門が基準で変わる会社の割合": round(float((np.array(t1) > 1).mean() * 100), 1)}, fl


base, fl_base = many(0.6, 1.0)
sweep = []
for ratio in [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]:
    m, _ = many(ratio, 1.0, 1000, seed=4291)
    sweep.append({"共通費÷配る前の利益の合計": ratio, **{k: v for k, v in m.items() if not isinstance(v, list)}})
sweep = pd.DataFrame(sweep); sweep.to_csv(RES / "sweep_shared_cost_ratio.csv", index=False)
sp = []
for spread in [0.0, 0.5, 1.0, 1.5]:
    m, _ = many(0.6, spread, 1000, seed=4292)
    sp.append({"部門ごとの使い方の違いの大きさ": spread, **{k: v for k, v in m.items() if not isinstance(v, list)}})
sp = pd.DataFrame(sp); sp.to_csv(RES / "sweep_spread.csv", index=False)
pd.Series(fl_base).value_counts().sort_index().rename_axis("符号が変わる部門の数").rename("会社の数").to_csv(RES / "flip_count_distribution.csv")

main = {"one_company": {"共通費の合計": int(s.amount.sum()), "配る前の利益の合計": int(d.direct_profit.sum()), "売上の合計": int(d.sales.sum()), "赤字の部門の数": red,
                        "4つの基準で符号が変わる部門の数": flip4, "符号が変わる部門": flip_dept, "混ぜた基準も入れて符号が変わる部門の数": flip_all,
                        "順位が動く幅の最大": maxshift, "順位が3つ以上動く部門の数": shift3, "順位相関": rho, "利益がいちばん多い部門": top1, "利益がいちばん少ない部門": bottom1,
                        "配る前に赤字の部門の数": int((d.direct_profit < 0).sum()), "基準ごとの割合（%）": share},
        "many_base": base, "sweep_ratio": json.loads(sweep.to_json(orient="records", force_ascii=False)), "sweep_spread": json.loads(sp.to_json(orient="records", force_ascii=False)),
        "flip_distribution": {int(k): int(v) for k, v in pd.Series(fl_base).value_counts().sort_index().items()}}
json.dump(main, open(RES / "a429_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図1：1つの会社の、基準ごとの利益
fig, ax = plt.subplots(figsize=(9.4, 4.8))
cols = [BLUE, ORANGE, GREEN, GRAY]; y = np.arange(len(P))
order = P[four].mean(axis=1).sort_values(ascending=False).index
for j, (c, col) in enumerate(zip(four, cols)):
    ax.scatter(P.loc[order, c] / 1e6, y, s=42, color=col, label=c, zorder=3)
for i, dd in enumerate(order):
    lo, hi = P.loc[dd, four].min() / 1e6, P.loc[dd, four].max() / 1e6
    ax.plot([lo, hi], [i, i], color=ORANGE if dd in flip_dept else "#d0d0cc", lw=2.5 if dd in flip_dept else 1.5, zorder=1)
ax.scatter(d.set_index("dept").loc[order, "direct_profit"] / 1e6, y, marker="|", s=120, color=INK, label="配る前の利益", zorder=2)
ax.axvline(0, color=INK, lw=0.8)
ax.set_yticks(y); ax.set_yticklabels([f"{dd}（符号が変わる）" if dd in flip_dept else dd for dd in order]); ax.invert_yaxis()
ax.set_xlabel("共通費を配ったあとの利益（百万円）"); ax.set_title(f"配る基準を変えると、12部門のうち{flip4}部門で黒字と赤字が入れ替わる")
ax.legend(frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=9)
save(fig, "a429_one_company.png", SRC, y=-0.1)

# ---- 図2：2,000社での分布
fig, ax = plt.subplots(figsize=(8, 4))
vc = pd.Series(fl_base).value_counts().sort_index()
ax.bar(vc.index, vc.values / len(fl_base) * 100, color=BLUE)
for k, v in vc.items():
    ax.text(k, v / len(fl_base) * 100 + 0.4, f"{v / len(fl_base) * 100:.0f}%", ha="center", fontsize=9)
ax.set_xticks(vc.index); ax.set_xlabel("4つの基準のあいだで、黒字と赤字が入れ替わる部門の数（12部門中）"); ax.set_ylabel("会社の割合（%）")
ax.set_title("架空の会社2,000社：符号が変わる部門がない会社は少ない")
save(fig, "a429_flip_distribution.png", SRC)

# ---- 図3：共通費の大きさ、使い方の違いの大きさ
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4))
ax = axs[0]
ax.plot(sweep["共通費÷配る前の利益の合計"] * 100, sweep["符号が変わる部門の数（平均）"], marker="o", color=ORANGE)
ax.set_xlabel("共通費の合計 ÷ 配る前の利益の合計（%）"); ax.set_ylabel("符号が変わる部門の数（平均、12部門中）")
ax.set_title("共通費が大きいほど、入れ替わる部門が増える")
ax = axs[1]
ax.plot(sp["部門ごとの使い方の違いの大きさ"], sp["符号が変わる部門の数（平均）"], marker="o", color=BLUE)
ax.set_xlabel("部門ごとの、人・面積・時間の使い方の違いの大きさ（1＝基本の設定）"); ax.set_ylabel("符号が変わる部門の数（平均）")
ax.set_title("使い方がそろっていれば、基準を変えても同じ")
fig.tight_layout()
save(fig, "a429_sweeps.png", SRC)
print(json.dumps(main, ensure_ascii=False)[:4000])
