# 図を作る
import json, pathlib, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
R = pathlib.Path(__file__).resolve().parents[1]; F = R/"figures"; F.mkdir(exist_ok=True)
d = pd.read_csv(R/"results/r2_cp_series.csv"); d["t"] = pd.PeriodIndex(d.ym, freq="M").to_timestamp()
S = json.load(open(R/"results/summary.json"))
C1, C2, C3, GR = "#2b6cb0", "#c05621", "#2f855a", "#888888"
def shade(a, tc=GR):
    a.axvline(pd.Timestamp("2013-04-01"), color=tc, lw=.8, ls=":")
    a.text(pd.Timestamp("2013-05-01"), a.get_ylim()[1]*.97, "2013年4月：調査方法の変更\n（郵送へ）", fontsize=7.5, color=tc, va="top")

# 1. 回答の割合（積み上げ）
C7 = ['d5', 'd2_5', 'd0_2', 'zero', 'u0_2', 'u2_5', 'u5', 'dk']
lab = ['下がる 5%以上', '下がる 2〜5%', '下がる 2%未満', '0%程度', '上がる 2%未満', '上がる 2〜5%', '上がる 5%以上', '分からない']
cols = ['#1a365d', '#2c5282', '#63b3ed', '#cbd5e0', '#fbd38d', '#ed8936', '#9c4221', '#e2e8f0']
fig, a = plt.subplots(figsize=(10, 4.6))
a.stackplot(d.t, *[d[c] for c in C7], labels=lab, colors=cols)
a.set_ylim(0, 100); a.set_ylabel("回答の割合（%）"); a.margins(x=0)
a.legend(ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.08), frameon=False)
shade(a, "white")
a.set_title("1年後の物価の見通し（消費動向調査、二人以上の世帯）：「5%以上上がる」は2026年9月に48%", fontsize=11)
fig.tight_layout(); fig.savefig(F/"f72_shares.png", dpi=150); plt.close()

# 2. 推定した予想インフレ率と実際の物価
fig, a = plt.subplots(figsize=(10, 4.6))
a.fill_between(d.t, d.mu - d.sigma, d.mu + d.sigma, color=C1, alpha=.12, label="予想のばらつき（平均±1標準偏差）")
a.plot(d.t, d.mu, color=C1, lw=2, label="家計の予想インフレ率（Carlson–Parkin 法）")
a.plot(d.t, d.all_now, color=GR, lw=1.2, label="その月の消費者物価（総合、前年同月比）")
a.plot(d.t, d.all_t12, color=C2, lw=1.2, ls="--", label="1年後に実際になった物価上昇率")
a.axhline(2, color="k", lw=.6, ls=":"); a.text(d.t.iloc[2], 2.15, "2%", fontsize=8)
a.axhline(0, color="k", lw=.5); a.set_ylabel("%"); a.margins(x=0)
a.legend(fontsize=8, loc="upper left", frameon=False); shade(a)
a.set_title("家計の予想は、実際の物価より平均で2ポイントほど高く、いまの物価と一緒に動いていた", fontsize=11)
fig.tight_layout(); fig.savefig(F/"f72_expect_vs_cpi.png", dpi=150); plt.close()

# 3. ずらした相関と、期間別のずれ
cc = pd.read_csv(R/"results/r4_leadlag.csv"); tb = pd.read_csv(R/"results/r3_compare_period.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].bar(cc.lag_months, cc["corr"], color=[C2 if l == 12 else (C1 if l == 0 else "#a0aec0") for l in cc.lag_months])
ax[0].set_xlabel("物価上昇率の時点（月。0＝同じ月、+12＝1年後、−12＝1年前）"); ax[0].set_ylabel("予想インフレ率との相関"); ax[0].set_ylim(0, 1)
ax[0].set_title("予想は「1年後の物価」より「いまの物価」とよく合う", fontsize=10)
for l in [-12, 0, 12]:
    v = cc.loc[cc.lag_months == l, "corr"].iloc[0]; ax[0].text(l, v+.02, f"{v:.2f}", ha="center", fontsize=8)
t = tb[tb.period != "全期間"]
x = np.arange(len(t)); w = .27
ax[1].bar(x-w, t.mu_mean, w, color=C1, label="予想インフレ率")
ax[1].bar(x, t.cpi_now_mean, w, color=GR, label="その月の物価")
ax[1].bar(x+w, t.cpi_t12_mean, w, color=C2, label="1年後の物価")
for i, r in enumerate(t.itertuples()):
    ax[1].text(i-w, r.mu_mean+.1, f"{r.mu_mean:.1f}", ha="center", fontsize=8)
    ax[1].text(i+w, max(r.cpi_t12_mean, 0)+.1, f"{r.cpi_t12_mean:.1f}", ha="center", fontsize=8)
ax[1].set_xticks(x); ax[1].set_xticklabels(t.period, fontsize=8.5); ax[1].axhline(0, color="k", lw=.5)
ax[1].set_ylabel("期間平均（%）"); ax[1].legend(fontsize=8, frameon=False)
ax[1].set_title("どの期間でも、予想は1年後の実際より高い", fontsize=10)
fig.tight_layout(); fig.savefig(F/"f72_leadlag_bias.png", dpi=150); plt.close()

# 4. 年齢・年収別
g = pd.read_csv(R/"results/r7_groups_summary.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ag = g[g.sheet.str.contains("平成25")]
for per, c in [("2013/4〜2021/12", "#a0aec0"), ("2022/1〜", C1)]:
    s = ag[ag.period == per]; ax[0].plot(s.group, s.mu, "o-", color=c, label=per)
ax[0].set_title("世帯主の年齢別（2013年4月〜）", fontsize=10); ax[0].set_ylabel("予想インフレ率の期間平均（%）"); ax[0].legend(fontsize=8, frameon=False)
ax[0].tick_params(axis="x", labelsize=8)
ic = g[g.type == "年収"]
for per, c in [("2004/4〜2013/3", "#cbd5e0"), ("2013/4〜2021/12", "#a0aec0"), ("2022/1〜", C1)]:
    s = ic[ic.period == per]; ax[1].plot(s.group.str.replace("万円", "").str.replace("300未満", "300未満").str.replace(r"〜(\d+)未満", r"〜\1", regex=True), s.mu, "o-", color=c, label=per)
ax[1].set_title("世帯の年間収入別（万円）", fontsize=10); ax[1].legend(fontsize=8, frameon=False); ax[1].tick_params(axis="x", labelsize=7.5, rotation=20)
fig.suptitle("年齢が高いほど、年収が低いほど、予想インフレ率は高めだった", fontsize=11)
fig.tight_layout(); fig.savefig(F/"f72_groups.png", dpi=150); plt.close()

# 5. 頑健性
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for k, lab_, c, ls in [("mu", "基本（正規分布、δ=0.75）", C1, "-"), ("mid", "中点の平均（±5%以上を±6%とみなす）", C2, "-"), ("rob_t5", "t分布（自由度5）", C3, "--"), ("rob_mid_open8", "中点の平均（±8%とみなす）", "#805ad5", ":")]:
    ax[0].plot(d.t, d[k], color=c, ls=ls, lw=1.3 if k != "mu" else 2, label=lab_)
ax[0].legend(fontsize=7.5, frameon=False); ax[0].set_ylabel("%"); ax[0].margins(x=0)
ax[0].set_title("水準は「5%以上」の扱いで変わるが、動きはそろう", fontsize=10)
rb = pd.read_csv(R/"results/r8_robustness.csv")
names = {"mu": "基本", "mid": "中点（±6）", "rob_delta0.25": "δ=0.25", "rob_delta0.5": "δ=0.5", "rob_delta1.0": "δ=1.0", "rob_t5": "t分布", "rob_mid_open8": "中点（±8）", "rob_logistic": "ロジスティック", "rob_dk_as_zero": "分からない→0%"}
rb["name"] = rb.setting.map(names)
x = np.arange(len(rb)); w = .27
for i, (per, c) in enumerate([("2004/4〜2013/3", "#cbd5e0"), ("2013/4〜2021/12", "#a0aec0"), ("2022/1〜", C1)]):
    ax[1].bar(x+(i-1)*w, rb[per], w, color=c, label=per)
ax[1].set_xticks(x); ax[1].set_xticklabels(rb.name, rotation=35, fontsize=7.5, ha="right"); ax[1].set_ylabel("期間平均（%）"); ax[1].set_ylim(0, 6.6); ax[1].legend(fontsize=7.5, frameon=False, ncol=3, loc="upper center")
ax[1].set_title("9通りの設定でも、期間の並びは同じ", fontsize=10)
fig.tight_layout(); fig.savefig(F/"f72_robust.png", dpi=150); plt.close()
print("ok")
