"""559 前後の差で比べるか、前の値を入れた回帰で比べるかで、効果の答えが変わるのはなぜか（正解の分かるデータで試す）

架空の店 400店。1日の売上（万円）を施策の前と後に測る。店ごとの「ふだんの水準」μ と、その日ごとの振れ e がある。
  前：y0 = μ + e0　　後：y1 = μ + 効果 × 施策 + e1（本当の効果は 2万円）
施策をする店の決め方（割り付けの仕組み）を3通りに変え、
「前後の差の比較」と「前の値を入れた回帰（共分散分析）」の答えを比べる。
"""
import json
import numpy as np, pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import save, RES, SQL, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED, N, REPS, TAU = 559, 400, 2000, 2.0
rng = np.random.default_rng(SEED)
SRC = "架空のデータ（作成者が乱数で作成、seed 559）"
SD_MU, SD_E = 8.0, 6.0      # ふだんの水準の店ごとの違いと、その日ごとの振れ。前後の相関は 64/(64+36)=0.64


def make(scheme, sd_mu=SD_MU, sd_e=SD_E, n=N):
    grp = rng.random(n) < 0.5                               # C で使う2つの系列（タイプ）
    mu = 40 + sd_mu * rng.normal(size=n) - np.where(grp, 5.0, 0.0) * (scheme == "C")
    y0 = mu + sd_e * rng.normal(size=n)
    if scheme == "A":                                       # くじで決める
        d = rng.random(n) < 0.5
    elif scheme == "B":                                     # 前の売上が低い30%の店にする
        d = y0 < np.quantile(y0, 0.3)
    else:                                                   # もともと水準の低い系列の店にする
        d = grp
    y1 = mu + TAU * d + sd_e * rng.normal(size=n)
    return y0, y1, d.astype(float)


def est(y0, y1, d):
    change = (y1 - y0)[d == 1].mean() - (y1 - y0)[d == 0].mean()
    post = y1[d == 1].mean() - y1[d == 0].mean()
    X = np.column_stack([np.ones_like(y0), d, y0])
    b, *_ = np.linalg.lstsq(X, y1, rcond=None)
    e = y1 - X @ b; s2 = e @ e / (len(y0) - 3); V = s2 * np.linalg.inv(X.T @ X)
    Xc = np.column_stack([np.ones_like(y0), d]); bc, *_ = np.linalg.lstsq(Xc, y1 - y0, rcond=None)
    ec = (y1 - y0) - Xc @ bc; Vc = (ec @ ec / (len(y0) - 2)) * np.linalg.inv(Xc.T @ Xc)
    return dict(change=change, ancova=b[1], post=post, slope=b[2], pre_gap=y0[d == 1].mean() - y0[d == 0].mean(),
                se_change=np.sqrt(Vc[1, 1]), se_ancova=np.sqrt(V[1, 1]))


SCH = {"A": "A くじで決める", "B": "B 前の売上が\n低い30%の店にする", "C": "C もともと水準の\n低い系列の店にする"}

# ---- 1. 3つの仕組み × 2,000回
rows, dist = [], {}
for s in SCH:
    R = pd.DataFrame([est(*make(s)) for _ in range(REPS)])
    dist[s] = R
    rows.append(dict(scheme=s, change_mean=R.change.mean(), change_sd=R.change.std(), ancova_mean=R.ancova.mean(),
                     ancova_sd=R.ancova.std(), post_mean=R.post.mean(), slope_mean=R.slope.mean(), pre_gap_mean=R.pre_gap.mean(),
                     cover_change=np.mean(abs(R.change - TAU) <= 1.96 * R.se_change), cover_ancova=np.mean(abs(R.ancova - TAU) <= 1.96 * R.se_ancova),
                     gap=(R.ancova - R.change).mean()))
summ = pd.DataFrame(rows); summ.round(4).to_csv(RES / "by_scheme.csv", index=False)

# ---- 2. 前後の相関（信頼性）を変える。ふだんの水準の違い sd_mu を動かし、全体の振れは 10 に固定
rows = []
for rho in [0.2, 0.4, 0.6, 0.8, 0.95]:
    sd_mu, sd_e = np.sqrt(100 * rho), np.sqrt(100 * (1 - rho))
    for s in ["B", "C"]:
        R = pd.DataFrame([est(*make(s, sd_mu, sd_e)) for _ in range(REPS // 4)])
        rows.append(dict(rho=rho, scheme=s, change=R.change.mean(), ancova=R.ancova.mean(), slope=R.slope.mean()))
byr = pd.DataFrame(rows); byr.round(4).to_csv(RES / "by_reliability.csv", index=False)

# ---- 3. 例の1回（B）と SQL の確認
y0, y1, d = make("B")
ex = pd.DataFrame({"store_id": np.arange(N), "treated": d.astype(int), "sales_before": y0.round(4), "sales_after": y1.round(4)})
ex.to_csv(RES / "example_stores_B.csv", index=False)
e2 = est(ex.sales_before.to_numpy(), ex.sales_after.to_numpy(), ex.treated.to_numpy().astype(float))
con = duckdb.connect(config={"threads": 1}); con.register("stores", pd.read_csv(RES / "example_stores_B.csv"))
sq = con.execute(open(SQL / "a559_change_vs_ancova.sql", encoding="utf-8").read()).df(); sq.to_csv(RES / "sql_check_B.csv", index=False)
sql_check = dict(python_change=e2["change"], sql_change=float(sq.change_score_diff.iloc[0]), python_ancova=e2["ancova"], sql_ancova=float(sq.ancova_effect.iloc[0]))
json.dump(dict(true_effect=TAU, sd_mu=SD_MU, sd_e=SD_E, n=N, reps=REPS, sql_check=sql_check, example_B=e2),
          open(RES / "a559_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# ---- 図1：3つの仕組みで、2つの方法の答え
fig, ax = plt.subplots(figsize=(9, 4.4))
for i, s in enumerate(SCH):
    for j, (k, c, lab) in enumerate([("change", ORANGE, "前後の差の比較"), ("ancova", BLUE, "前の値を入れた回帰")]):
        v = dist[s][k]; x = i + (j - 0.5) * 0.36
        ax.boxplot(v, positions=[x], widths=0.28, showfliers=False, whis=(5, 95), patch_artist=True,
                   boxprops=dict(facecolor=c, alpha=0.35, color=c), medianprops=dict(color=INK), whiskerprops=dict(color=c), capprops=dict(color=c))
        ax.text(x, np.percentile(v, 95) + 0.25, f"{v.mean():.2f}", ha="center", fontsize=9, color=c)
ax.axhline(TAU, color=GREEN, ls="--", lw=1.2); ax.text(2.55, TAU + 0.15, "本当の効果 2", color=GREEN, va="bottom", fontsize=9)
ax.set_xticks(range(3), list(SCH.values()), fontsize=9.5); ax.set_xlim(-0.6, 3.0); ax.set_ylabel("推定した効果（万円）")
ax.plot([], [], color=ORANGE, lw=6, alpha=0.4, label="前後の差の比較"); ax.plot([], [], color=BLUE, lw=6, alpha=0.4, label="前の値を入れた回帰")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("施策をする店の決め方で、正しい方法が入れ替わる")
save(fig, "a559_schemes.png", SRC + "。400店×2,000回。箱は四分位、ひげは5〜95%、数字は平均")

# ---- 図2：例の1回（B）の散布図。前の売上が低い店ほど、後で上がる（平均への回帰）
fig, ax = plt.subplots(figsize=(6.6, 5))
for v, c, lab in [(0, GRAY, "施策なし"), (1, ORANGE, "施策あり（前の売上が低い30%）")]:
    m = d == v; ax.scatter(y0[m], y1[m], s=10, color=c, alpha=0.6, label=lab)
lo, hi = min(y0.min(), y1.min()), max(y0.max(), y1.max())
ax.plot([lo, hi], [lo, hi], ls="--", color=INK, lw=0.9); ax.text(hi - 12, hi - 9, "前と同じ", fontsize=9, rotation=38)
xs = np.linspace(lo, hi, 50); b = e2["slope"]; a0 = y1[d == 0].mean() - b * y0[d == 0].mean()
ax.plot(xs, a0 + b * xs, color=BLUE, lw=1.4); ax.text(xs[-1] - 2, a0 + b * xs[-1] - 3.5, f"傾き {b:.2f}", color=BLUE, fontsize=9, ha="right")
ax.set_xlabel("施策の前の1日の売上（万円）"); ax.set_ylabel("施策の後の1日の売上（万円）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("B：前の売上が低い店は、施策がなくても後で上がる")
save(fig, "a559_scatter_B.png", SRC + "。例の1回、400店。青い線は前の値を入れた回帰の傾き")

# ---- 図3：前後の相関（信頼性）を変えたときのずれ
fig, ax = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for a, s in zip(ax, ["B", "C"]):
    dd = byr[byr.scheme == s]
    a.plot(dd.rho, dd.change, "o-", color=ORANGE, label="前後の差の比較"); a.plot(dd.rho, dd.ancova, "s-", color=BLUE, label="前の値を入れた回帰")
    a.axhline(TAU, color=GREEN, ls="--", lw=1.2); a.set_xlabel("前と後の売上の相関（ふだんの水準が占める割合）"); a.set_title(SCH[s].replace("\n", ""))
    a.set_xticks(dd.rho, [f"{v:.2f}" for v in dd.rho])
ax[0].set_ylabel("推定した効果の平均（万円）"); ax[0].legend(frameon=False, fontsize=9)
save(fig, "a559_reliability.png", SRC + "。各条件500回の平均。全体の振れ（標準偏差10万円）は固定")
print(summ.round(3).to_string()); print(byr.round(3).to_string()); print(sql_check)
