"""04 図：6枚"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, SEXES, COL, RATE_BASE, AGE_GROUP_LABELS

FIG.mkdir(exist_ok=True)
a65 = pd.read_csv(RES / "a65_by_year.csv")
d5 = pd.read_csv(RES / "delta5.csv")
dec = pd.read_csv(RES / "decomposition.csv")
rate = pd.read_csv(RES / "rate_sensitivity.csv")
main = json.loads((RES / "main.json").read_text())
proj = pd.read_csv(RES / "ipss_projection_a65.csv")
rq = pd.read_csv(RES / "reask_cohort_vs_period.csv")
col = f"a65_{RATE_BASE*100:.1f}"; dcol = f"d_{RATE_BASE*100:.1f}"
SRC = "出典：日本版死亡データベース（JMD）から作成。割引率は年1.7%（令和6年財政検証のスプレッド）"

# 図1 a65 の推移と見通し
fig, ax = plt.subplots(figsize=(8, 4.6))
for s in SEXES:
    t = a65[a65.sex == s]
    ax.plot(t.year, t[col], color=COL[s], lw=2, label=f"{s}（実績）")
    p = proj[(proj.sex == s) & (proj.case == "死亡中位")]
    ax.plot(p.year, p[col], color=COL[s], lw=1.5, ls="--", label=f"{s}（将来推計人口の中位に合わせた見通し）")
    for y in (2014, 2019, 2024):
        v = t[t.year == y][col].iloc[0]
        ax.scatter([y], [v], color=COL[s], zorder=3, s=18)
        ax.annotate(f"{v:.2f}", (y, v), textcoords="offset points", xytext=(-8, 7 if s == "女" else -14), fontsize=8, color=COL[s])
ax.set_title("65歳から一生、毎年1円を払うのに要るお金（65歳の年金現価）")
ax.set_ylabel("円（毎年1円あたり）"); ax.set_xlim(1960, 2071); ax.grid(alpha=.3)
ax.legend(fontsize=8, loc="upper left")
fig.text(0.01, 0.01, SRC, fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f268_1_a65_trend.png"); plt.close(fig)

# 図2 5年ごとの変化
fig, ax = plt.subplots(figsize=(8, 4.6))
for s in SEXES:
    t = d5[(d5.sex == s) & (d5.start >= 1970)]
    ax.plot(t.end, t[dcol] * 100, color=COL[s], lw=2, marker="o", ms=3, label=s)
    pm = main["projection"][s]["死亡中位"]["per5_2020_2070"] * 100
    ax.axhline(pm, color=COL[s], ls="--", lw=1)
    ax.text(1976, pm + (0.3 if s == "男" else -0.75), f"{s}：将来推計人口の中位の見通し（2020→2070年の5年あたり）{pm:.1f}%", fontsize=7.5, color=COL[s])
ax.axhline(0, color="black", lw=.8)
ax.set_title("生命表が5年新しくなると、65歳の年金現価は何％動いたか")
ax.set_xlabel("5年の終わりの年（例：2019 は 2014→2019年）"); ax.set_ylabel("％"); ax.set_ylim(-2, 9)
ax.grid(alpha=.3); ax.legend(fontsize=9)
fig.text(0.01, 0.01, SRC, fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f268_2_delta5.png"); plt.close(fig)

# 図3 年齢の分解
fig, axes = plt.subplots(1, 2, figsize=(9, 4.4), sharey=True)
for ax, s in zip(axes, SEXES):
    x = np.arange(len(AGE_GROUP_LABELS)); w = 0.38
    for i, (y0, c) in enumerate([(2014, COL[s]), (2019, "gray")]):
        t = dec[(dec.sex == s) & (dec.start == y0)].set_index("age_group").loc[AGE_GROUP_LABELS]
        ax.bar(x + (i - 0.5) * w, t.contrib_pct_of_base * 100, w, color=c, alpha=.85 if i == 0 else .6,
               label=f"{y0}→{y0+5}年（合計 {t.total_pct.iloc[0]*100:+.1f}%）")
    ax.axhline(0, color="black", lw=.8)
    ax.set_xticks(x); ax.set_xticklabels(AGE_GROUP_LABELS, rotation=30, fontsize=8)
    ax.set_title(s); ax.grid(axis="y", alpha=.3); ax.legend(fontsize=8)
axes[0].set_ylabel("年金現価の変化への寄与（％）")
fig.suptitle("その変化は何歳の死亡率から来たか（年齢層ごとに死亡率を入れ替えて分けた）")
fig.text(0.01, 0.01, SRC, fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 0.95)); fig.savefig(FIG / "f268_3_decomposition.png"); plt.close(fig)

# 図4 割引率との比較
fig, ax = plt.subplots(figsize=(8, 4.4))
labels = ["生命表\n2014→2019年", "生命表\n2019→2024年", "割引率を\n0.25ポイント下げる", "割引率を\n0.5ポイント下げる"]
x = np.arange(len(labels)); w = 0.38
for i, s in enumerate(SEXES):
    r = rate[(rate.sex == s) & (rate.year == 2014)].set_index("rate_to")["pct_change"]
    vals = [main["hypotheses"]["H1"][s], main["hypotheses"]["H2"][s]["d_2019_2024"],
            r.loc[r.index[np.isclose(r.index, RATE_BASE - 0.0025)][0]], r.loc[r.index[np.isclose(r.index, RATE_BASE - 0.005)][0]]]
    b = ax.bar(x + (i - 0.5) * w, np.array(vals) * 100, w, color=COL[s], label=s)
    for xx, v in zip(x + (i - 0.5) * w, vals):
        ax.text(xx, v * 100 + (0.12 if v >= 0 else -0.12), f"{v*100:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.axhline(0, color="black", lw=.8)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("65歳の年金現価の変化（％）"); ax.grid(axis="y", alpha=.3); ax.legend()
ax.set_title("生命表の5年の更新と、割引率の小さな変更の比べ（割引率は2014年の表で計算）")
fig.text(0.01, 0.01, SRC, fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f268_4_rate_vs_table.png"); plt.close(fig)

# 図5 過去の5年あたりの伸びと、見通しの伸び
fig, ax = plt.subplots(figsize=(8, 4.4))
cats = ["実績\n1990→2019年", "見通し 死亡高位\n2020→2070年", "見通し 死亡中位\n2020→2070年", "見通し 死亡低位\n2020→2070年"]
x = np.arange(len(cats)); w = 0.38
for i, s in enumerate(SEXES):
    vals = [main["hist_1990_2019"][s]["geo_per5"]] + [main["projection"][s][c]["per5_2020_2070"] for c in ("死亡高位", "死亡中位", "死亡低位")]
    ax.bar(x + (i - 0.5) * w, np.array(vals) * 100, w, color=COL[s], label=s)
    for xx, v in zip(x + (i - 0.5) * w, vals):
        ax.text(xx, v * 100 + 0.05, f"{v*100:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=9)
ax.set_ylabel("5年あたりの伸び（％）"); ax.grid(axis="y", alpha=.3); ax.legend()
ax.set_title("将来推計人口の見通しでの年金現価の伸び（5年あたり）と、過去30年の実績")
fig.text(0.01, 0.01, "見通し：Lee–Carter（1970〜2024年で当てはめ）の死亡率を、2070年の平均寿命が将来推計人口（令和5年推計）の仮定に合うよう延ばした。" + "\n" + SRC, fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(FIG / "f268_5_projection_pace.png"); plt.close(fig)

# 図6 問い直し：期間生命表とコーホート
fig, ax = plt.subplots(figsize=(8, 4.6))
for s in SEXES:
    t = rq[(rq.sex == s) & (rq.kind == "過去（実績）")]
    ax.plot(t.year65, t.period_short_pct * 100, color=COL[s], lw=2, marker="o", ms=3, label=f"{s}：その年の生命表")
    ax.plot(t.year65, t.period_plus5_short_pct * 100, color=COL[s], lw=1.2, ls=":", marker="s", ms=3, label=f"{s}：5年後の生命表に替えた場合")
    f = rq[(rq.sex == s) & (rq.kind == "これから（見通し）")].set_index("case")
    ax.errorbar([2024 + (0.6 if s == "女" else 0)], [f.loc["死亡中位", "period_short_pct"] * 100],
                yerr=[[(f.loc["死亡中位", "period_short_pct"] - f.loc["死亡低位", "period_short_pct"]) * 100],
                      [(f.loc["死亡高位", "period_short_pct"] - f.loc["死亡中位", "period_short_pct"]) * 100]],
                fmt="D", color=COL[s], capsize=4, label=f"{s}：2024年に65歳（見通し、中位と高位〜低位）")
ax.axhline(0, color="black", lw=.8)
ax.set_xlabel("65歳になった年"); ax.set_ylabel("実際に生きた死亡率で出した値との差（％）")
ax.set_title("その年の生命表で出した年金現価は、実際より何％低かったか")
ax.grid(alpha=.3); ax.legend(fontsize=7.5, loc="center", bbox_to_anchor=(0.62, 0.45))
fig.text(0.01, 0.01, SRC + "\n1990年に65歳の人は2024年に99歳（100歳以上は2024年の死亡率で延ばした）。2024年に65歳の人は将来推計人口の仮定に合わせた見通し", fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(FIG / "f268_6_cohort_vs_period.png"); plt.close(fig)
print("ok")
