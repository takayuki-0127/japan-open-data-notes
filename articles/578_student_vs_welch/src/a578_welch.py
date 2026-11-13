"""578 群で散らばりが違うとき、ふつうのt検定は何%の回で「差あり」と言うか（seed 578）"""
import json
import numpy as np, pandas as pd, duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(578)
SRC = "架空のデータ（作成者が乱数で作成、seed 578）"
SIMS = 20000
SIZES = [(20, 20), (10, 40), (40, 10)]          # (A群の人数, B群の人数)
RATIOS = [1, 1.5, 2, 3, 4]                      # B群の標準偏差 ÷ A群の標準偏差


def rates(n1, n2, ratio, delta=0.0, sims=SIMS):
    a = rng.normal(0, 1, (sims, n1))
    b = rng.normal(delta, ratio, (sims, n2))
    ps = stats.ttest_ind(a, b, axis=1, equal_var=True).pvalue
    pw = stats.ttest_ind(a, b, axis=1, equal_var=False).pvalue
    pl = stats.levene(a, b, axis=1, center="median").pvalue        # 先に等分散を検定して選ぶ方法
    p2 = np.where(pl < 0.05, pw, ps)
    return float((ps < .05).mean()), float((pw < .05).mean()), float((p2 < .05).mean())


rows = []
for n1, n2 in SIZES:
    for r in RATIOS:
        s, w, two = rates(n1, n2, r)
        rows.append({"n_a": n1, "n_b": n2, "sd_ratio": r, "student": s, "welch": w, "two_stage": two})
fp = pd.DataFrame(rows); fp.to_csv(RES / "false_positive.csv", index=False)

# 差があるとき（等分散）の検出力：ウェルチで損はどのくらいか
prow = []
for n1, n2 in [(20, 20), (10, 40)]:
    for dlt in [0, 0.25, 0.5, 0.75, 1.0]:
        s, w, two = rates(n1, n2, 1, delta=dlt)
        prow.append({"n_a": n1, "n_b": n2, "delta": dlt, "student": s, "welch": w, "two_stage": two})
pw = pd.DataFrame(prow); pw.to_csv(RES / "power_equal_var.csv", index=False)

# 例の1回（A群10人・B群40人、B群の散らばり3倍）。SQL で t 値を出して scipy と比べる
a = rng.normal(0, 1, 10).round(3); b = rng.normal(0, 3, 40).round(3)
DATA.mkdir(exist_ok=True)
ex = pd.DataFrame({"grp": ["A"] * 10 + ["B"] * 40, "value": np.r_[a, b]})
ex.to_csv(DATA / "example_two_groups.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("obs", ex)
sq = con.execute(open(SQL / "a578_t_values.sql", encoding="utf-8").read()).df()
sq.to_csv(RES / "sql_t_values.csv", index=False)
ts, tw = stats.ttest_ind(a, b, equal_var=True), stats.ttest_ind(a, b, equal_var=False)
ok = bool(np.isclose(sq.t_student[0], ts.statistic) and np.isclose(sq.t_welch[0], tw.statistic) and np.isclose(sq.df_welch[0], tw.df))
example = {"t_student": float(ts.statistic), "p_student": float(ts.pvalue), "t_welch": float(tw.statistic), "p_welch": float(tw.pvalue), "df_welch": float(tw.df)}

# 図1：差がないのに「差あり」と言う割合（3つの人数の組み合わせ）
fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
for ax, (n1, n2) in zip(axes, SIZES):
    s = fp[(fp.n_a == n1) & (fp.n_b == n2)]
    ax.plot(s.sd_ratio, s.student * 100, "o-", color=ORANGE, label="ふつうのt検定（等分散）")
    ax.plot(s.sd_ratio, s.welch * 100, "s-", color=BLUE, label="ウェルチの検定")
    ax.axhline(5, color=INK, lw=1, ls="--")
    for x, v in zip(s.sd_ratio, s.student * 100): ax.text(x, v + 0.8, f"{v:.1f}", ha="center", fontsize=8.5, color=ORANGE)
    ax.set_title(f"A群{n1}人・B群{n2}人"); ax.set_xlabel("B群の標準偏差 ÷ A群の標準偏差")
axes[0].set_ylabel("差がないのに「差あり」（%）"); axes[0].legend(fontsize=8.5, loc="upper left")
save(fig, "a578_false_positive.png", SRC + "。各20,000回。点線は狙いの5%")

# 図2：少ない群の散らばりが大きいときの3つの方法
s = fp[(fp.n_a == 40) & (fp.n_b == 10)]
fig, ax = plt.subplots(figsize=(8, 4.2))
x = np.arange(len(RATIOS)); w = 0.27
for i, (c, lab, col) in enumerate([("student", "ふつうのt検定", ORANGE), ("two_stage", "等分散を先に検定して選ぶ", GRAY), ("welch", "ウェルチの検定", BLUE)]):
    v = s[c].to_numpy() * 100
    ax.bar(x + (i - 1) * w, v, w, color=col, label=lab)
    for xx, vv in zip(x + (i - 1) * w, v): ax.text(xx, vv + 0.4, f"{vv:.1f}", ha="center", fontsize=8)
ax.axhline(5, color=INK, lw=1, ls="--")
ax.set_xticks(x, [f"{r}倍" for r in RATIOS]); ax.set_xlabel("人数の少ないB群（10人）の標準偏差 ÷ A群（40人）の標準偏差")
ax.set_ylabel("差がないのに「差あり」（%）"); ax.legend(fontsize=9)
ax.set_title("先に等分散を検定して選んでも、ずれは残る")
save(fig, "a578_two_stage.png", SRC + "。各20,000回")

# 図3：等分散で差があるときの検出力
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, (n1, n2) in zip(axes, [(20, 20), (10, 40)]):
    s = pw[(pw.n_a == n1) & (pw.n_b == n2)]
    ax.plot(s.delta, s.student * 100, "o-", color=ORANGE, label="ふつうのt検定")
    ax.plot(s.delta, s.welch * 100, "s--", color=BLUE, label="ウェルチの検定")
    for x, v1, v2 in zip(s.delta, s.student * 100, s.welch * 100):
        if x > 0: ax.text(x, v1 + 3, f"{v1:.0f}/{v2:.0f}", ha="center", fontsize=8.5)
    ax.set_title(f"等分散・A群{n1}人・B群{n2}人"); ax.set_xlabel("本当の差（標準偏差の何倍か）")
axes[0].set_ylabel("「差あり」と言えた割合（%）"); axes[0].legend(fontsize=9)
save(fig, "a578_power.png", SRC + "。各20,000回。数字は ふつう/ウェルチ（%）")

main = {"sims": SIMS, "sql_matches_scipy": ok, "example": example,
        "false_positive": fp.round(4).to_dict(orient="records"), "power": pw.round(4).to_dict(orient="records")}
json.dump(main, open(RES / "a578_main.json", "w"), ensure_ascii=False, indent=1)
print(fp.round(4).to_string()); print(pw.round(4).to_string()); print(example, "sql ok", ok)
