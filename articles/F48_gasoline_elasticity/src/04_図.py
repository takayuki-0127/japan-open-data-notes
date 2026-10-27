"""図を作る（6枚）"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import DATA, RES, FIG, SUBSIDY_START, COVID

FIG.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "panel.csv", index_col=0)
d.index = pd.PeriodIndex(d.index, freq="M")
r = json.load(open(RES / "results.json"))
rob = pd.read_csv(RES / "robustness.csv")
C1, C2, C3, CG = "#2b6cb0", "#dd6b20", "#2f855a", "#a0aec0"
ts = lambda s: s.index.to_timestamp()

# 1. 価格と販売量の推移
x = d.loc["2017-01":"2026-08"]
q12 = (x.gas_kl.rolling(12).sum() / 1e6).loc["2017-12":]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.plot(ts(q12), q12, color=C1, lw=2.2, label="販売量（直近12か月の合計、左）")
ax.set_ylabel("ガソリン販売量（百万kℓ／12か月）", color=C1)
ax2 = ax.twinx()
ax2.plot(ts(x.price), x.price, color=C2, lw=1.4, label="レギュラー店頭価格（名目、右）")
ax2.plot(ts(x.rprice), x.rprice, color=C2, lw=1.4, ls="--", label="同（実質、2020年の物価）")
ax2.set_ylabel("円／ℓ", color=C2)
for a0, a1, lab, c in [(COVID[0], COVID[1], "コロナ期", CG), (SUBSIDY_START, "2025-12", "補助金", "#fbd38d")]:
    ax.axvspan(pd.Period(a0, "M").to_timestamp(), pd.Period(a1, "M").to_timestamp(), color=c, alpha=0.25, lw=0)
ax.text(pd.Period("2020-06", "M").to_timestamp(), 52.6, "コロナ期", fontsize=9, color="#4a5568")
ax.text(pd.Period("2023-02", "M").to_timestamp(), 52.6, "補助金（2022年1月〜）", fontsize=9, color="#9c4221")
ax.axvline(pd.Period("2026-01", "M").to_timestamp(), color="#c53030", lw=1, ls=":")
ax.text(pd.Period("2026-01", "M").to_timestamp(), 42.4, " 暫定税率\n 廃止", fontsize=8.5, color="#c53030")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=8.5, frameon=False)
ax.set_ylim(42, 53.5)
ax.set_title("ガソリンの販売量は2017→2025年で16%減り、店頭価格は上がった", fontsize=11.5)
fig.text(0.01, 0.005, "出典：経済産業省「資源・エネルギー統計」（石油連盟の集計表）、資源エネルギー庁「石油製品価格調査」、総務省「消費者物価指数」", fontsize=7.5, color="#4a5568")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f48_trend.png", dpi=150); plt.close(fig)

# 2. 散布図（前年同月比）
z = d.loc["2018-01":"2026-08"].dropna(subset=["dlq", "dlp"])
fig, ax = plt.subplots(figsize=(7.2, 5.2))
g = {"コロナ期（主分析では除外）": z[z.covid == 1], "補助金の前": z[(z.covid == 0) & (z["sub"] == 0)], "補助金の後（2022年〜）": z[(z.covid == 0) & (z["sub"] == 1)]}
for (lab, s), c in zip(g.items(), [CG, C1, C2]):
    ax.scatter(s.dlp * 100, s.dlq * 100, s=22, color=c, alpha=0.8, label=f"{lab}（{len(s)}か月）")
m = z[z.covid == 0]
b = r["ols"][0]; a = (m.dlq - b * m.dlp).mean()
xx = np.linspace(m.dlp.min(), m.dlp.max(), 10)
ax.plot(xx * 100, (a + b * xx) * 100, color="#1a202c", lw=1.5, label=f"最小二乗法の傾き {b:.3f}")
ax.axhline(0, color="#cbd5e0", lw=0.8); ax.axvline(0, color="#cbd5e0", lw=0.8)
ax.set_xlabel("実質店頭価格の前年同月比（%）"); ax.set_ylabel("1日当たり販売量の前年同月比（%）")
ax.set_ylim(-30, 25)
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
ax.set_title("価格が上がった月ほど量が少し減る。ただし傾きはごく小さい", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f48_scatter.png", dpi=150); plt.close(fig)

# 3. 最小二乗法と操作変数
rows = [("最小二乗法（全期間）", r["ols"], C1), ("操作変数（全期間）", r["iv"], C2),
        ("最小二乗法（補助金の前）", r["ols_pre"], C1), ("操作変数（補助金の前）", r["iv_pre"], C2),
        ("最小二乗法（補助金の後）", r["ols_post"], C1), ("操作変数（補助金の後）", r["iv_post"], C2)]
fig, ax = plt.subplots(figsize=(7.8, 4.4))
for i, (lab, (e, lo, hi), c) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.errorbar(e, y, xerr=[[e - lo], [hi - e]], fmt="o", color=c, capsize=4, ms=7)
    ax.text(0.62, y, f"{e:+.3f}（{lo:+.2f}〜{hi:+.2f}）", va="center", fontsize=9)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([x[0] for x in rows][::-1], fontsize=9.5)
ax.axvline(0, color="#718096", lw=0.8)
ax.set_xlim(-0.45, 1.05)
ax.set_xlabel("価格弾力性（価格1%の上昇で、販売量が何%変わるか）")
ax.set_title(f"操作変数（原油の円建て価格）では区間が広い。第1段階の F は {r['first_stage_F']:.1f}", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f48_ols_iv.png", dpi=150); plt.close(fig)

# 4. 短期と長期
fig, ax = plt.subplots(figsize=(7.4, 4.0))
items = [("短期（最小二乗法）", r["pa_ols"]["short"], C1), ("長期（最小二乗法）", [r["pa_ols"]["long"]] + r["pa_ols"]["long_ci"], C1),
         ("短期（操作変数）", r["pa_iv"]["short"], C2), ("長期（操作変数）", [r["pa_iv"]["long"]] + r["pa_iv"]["long_ci"], C2)]
for i, (lab, (e, lo, hi), c) in enumerate(items):
    y = len(items) - 1 - i
    ax.barh(y, e, color=c, alpha=0.35 if "短期" in lab else 0.7, height=0.55)
    ax.errorbar(e, y, xerr=[[e - lo], [hi - e]], fmt="none", color="#1a202c", capsize=4)
    ax.text(0.22, y, f"{e:+.3f}（{lo:+.2f}〜{hi:+.2f}）", va="center", fontsize=9)
ax.set_yticks(range(len(items))); ax.set_yticklabels([x[0] for x in items][::-1])
ax.axvline(0, color="#718096", lw=0.8); ax.set_xlim(-0.32, 0.45)
ax.set_xlabel("価格弾力性")
ax.set_title(f"部分調整モデル：前月の量の係数 {r['pa_ols']['c']:.2f}。長期は短期の約1.6倍", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f48_short_long.png", dpi=150); plt.close(fig)

# 5. 補助金の期間：原油と店頭価格の連動、暫定税率の廃止
roll = pd.read_csv(RES / "passthrough_rolling.csv")
roll["month"] = pd.PeriodIndex(roll["month"], freq="M")
roll = roll.set_index("month").reindex(pd.period_range(roll["month"].min(), roll["month"].max(), freq="M")).reset_index().rename(columns={"index": "month"})
roll["month"] = roll["month"].dt.to_timestamp()
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.3), gridspec_kw={"width_ratios": [1.35, 1]})
ax = axs[0]
ax.plot(roll["month"], roll["beta"], color=C2, lw=2, label="原油→店頭価格の連動（24か月の移動窓の傾き）")
ax.plot(roll["month"], roll["R2"], color=C1, lw=1.3, ls="--", label="当てはまり（R²）")
ax.axvspan(pd.Period(SUBSIDY_START, "M").to_timestamp(), pd.Period("2025-12", "M").to_timestamp(), color="#fbd38d", alpha=0.25, lw=0)
ax.axhline(0, color="#a0aec0", lw=0.8)
ax.set_title("補助金の期間に、原油と店頭価格の連動が弱まった", fontsize=10.5)
ax.legend(fontsize=8, frameon=False, loc="lower left")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax = axs[1]
ev = pd.read_csv(RES / "tax_event.csv", index_col=0)
xs = np.arange(len(ev))
ax.bar(xs - 0.18, ev["dlpn"] * 100, width=0.36, color=C2, label="店頭価格の前年同月比")
ax.bar(xs + 0.18, ev["dq_vs_trend"] * 100, width=0.36, color=C1, label="販売量（減少トレンドとの差）")
for i, (p, q) in enumerate(zip(ev["dlpn"], ev["dq_vs_trend"])):
    ax.text(i - 0.18, p * 100 - 1.2, f"{p*100:.0f}%", ha="center", va="top", fontsize=8.5)
    ax.text(i + 0.18, q * 100 + (0.4 if q > 0 else -1.2), f"{q*100:+.1f}%", ha="center", fontsize=8.5)
ax.axhline(0, color="#718096", lw=0.8)
ax.set_xticks(xs); ax.set_xticklabels(["2025年12月", "2026年1月", "2026年2月"])
ax.set_ylim(-28, 7)
ax.set_title(f"暫定税率の廃止の前後：価格{r['tax_event']['avg_dlpn']*100:.0f}%、量{r['tax_event']['avg_dq_vs_trend']*100:+.1f}%", fontsize=10.5)
ax.legend(fontsize=8, frameon=False, loc="lower center", ncol=2)
fig.tight_layout(); fig.savefig(FIG / "f48_subsidy.png", dpi=150); plt.close(fig)

# 6. 頑健性
fig, ax = plt.subplots(figsize=(8.6, 5.0))
n = len(rob)
for i, row in rob.iterrows():
    y = n - 1 - i
    ax.errorbar(row.OLS, y + 0.14, xerr=[[row.OLS - row.OLS_lo], [row.OLS_hi - row.OLS]], fmt="o", color=C1, capsize=3, ms=5, label="最小二乗法" if i == 0 else None)
    ax.errorbar(row.IV, y - 0.14, xerr=[[row.IV - row.IV_lo], [row.IV_hi - row.IV]], fmt="s", color=C2, capsize=3, ms=5, label="操作変数" if i == 0 else None)
ax.set_yticks(range(n)); ax.set_yticklabels([f"{s}（{k}か月）" for s, k in zip(rob["設定"], rob["n"])][::-1], fontsize=8.5)
ax.axvline(0, color="#718096", lw=0.8)
ax.set_xlabel("価格弾力性（95%区間）")
ax.legend(fontsize=8.5, frameon=False, loc="upper right")
ax.set_title("設定を変えた推定：多くは0〜−0.1付近だが、区間は広い", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f48_robust.png", dpi=150); plt.close(fig)
print("ok")
