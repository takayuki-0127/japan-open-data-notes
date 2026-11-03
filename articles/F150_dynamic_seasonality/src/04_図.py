import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, SERIES
from ds import profile

C = {"early": "#9aa5b1", "late": "#d1495b", "alt": "#2e86ab", "dark": "#333333"}
M = np.arange(1, 13)
ML = [f"{m}月" for m in M]
ss = pd.read_csv(RES / "seasonal_states.csv", parse_dates=["date"])

# 図1：出生の季節の形（年×月のヒートマップ）
b = ss[ss.series == "births"].set_index("date").seasonal_tv
b = 100 * (np.exp(b - b.groupby(b.index.year).transform("mean")) - 1)
H = b.groupby([b.index.year, b.index.month]).mean().unstack()
fig, ax = plt.subplots(figsize=(9, 6))
im = ax.imshow(H.values, aspect="auto", cmap="RdBu_r", vmin=-8, vmax=8)
ax.set_xticks(range(12)); ax.set_xticklabels(ML)
ax.set_yticks(range(0, len(H), 5)); ax.set_yticklabels(H.index[::5])
cb = fig.colorbar(im, ax=ax); cb.set_label("その年の平均との差（%）")
ax.set_title("出生数（1日あたり）の季節の形：1〜3月が年々低く、7〜9月が高くなった\n（季節が年々変わるモデルで取り出した季節成分）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig1_births_heatmap.png", dpi=150); plt.close()

# 図2：季節の振れ幅（最大の月と最小の月の差）の推移
ya = pd.read_csv(RES / "yearly_amplitude.csv")
fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
for ax, name in zip(axes, ["births", "inbound", "power"]):
    x = ya[ya.series == name]
    ax.plot(x.year, x.amplitude, color=C["late"], lw=2, marker="o", ms=3)
    ax.set_title(SERIES[name], fontsize=11); ax.set_ylim(0, max(36, x.amplitude.max() * 1.1)); ax.grid(alpha=.3)
    if name == "inbound": ax.axvspan(2020, 2022.9, color="#eee"); ax.text(2020.1, 2, "入国制限の\n期間は除外", fontsize=8)
axes[0].set_ylabel("季節の振れ幅（%ポイント）")
fig.suptitle("季節の振れ幅は、出生と電力では広がり、訪日では縮んだ", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig2_amplitude.png", dpi=150); plt.close()

# 図3：電力 気温を入れる前と後
pw = ss[ss.series == "power"].set_index("date").seasonal_tv
pt = pd.read_csv(RES / "power_seasonal_with_temp.csv", index_col=0, parse_dates=True).iloc[:, 0]
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, s, t in [(axes[0], pw, "気温を入れないモデルの季節成分"), (axes[1], pt, "気温（冷房度日・暖房度日）を入れたあとに残る季節成分")]:
    ax.plot(M, profile(s, (2017, 2019)).values, color=C["early"], lw=2.5, marker="o", label="2017〜19年")
    ax.plot(M, profile(s, (2023, 2025)).values, color=C["late"], lw=2.5, marker="o", label="2023〜25年")
    ax.axhline(0, color="#999", lw=.8); ax.set_xticks(M); ax.set_xticklabels(ML, fontsize=8); ax.set_title(t, fontsize=10); ax.grid(alpha=.3)
axes[0].set_ylabel("年の平均との差（%）"); axes[0].legend()
fig.suptitle("東京エリアの電力需要：夏の山が高くなったが、気温を入れるとほぼ消える", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig3_power_temp.png", dpi=150); plt.close()

# 図4：訪日 単純な平均の形と、構成を固定した場合、モデルの形
dec = pd.read_csv(RES / "inbound_mix_decomposition.csv", index_col=0)
iv = ss[ss.series == "inbound"].set_index("date").seasonal_tv
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(M, dec.early, color=C["early"], lw=2.5, marker="o", label="2005〜09年（実際）")
ax.plot(M, dec.late, color=C["late"], lw=2.5, marker="o", label="2024〜25年（実際）")
ax.plot(M, dec.early_shape_late_mix, color=C["alt"], lw=1.8, ls="--", label="国・地域の構成だけ2024〜25年にした場合")
ax.plot(M, profile(iv, (2024, 2025)).values, color=C["dark"], lw=1.5, ls=":", label="季節が変わるモデルの2024〜25年")
ax.axhline(0, color="#999", lw=.8); ax.set_xticks(M); ax.set_xticklabels(ML); ax.grid(alpha=.3)
ax.set_ylabel("1日あたりの人数の、トレンドとの差（%）"); ax.legend(fontsize=8.5, loc="lower left")
ax.set_title("訪日外客数：7・8月の山が消え、4月だけが目立つ形になった。国・地域の構成の変化では説明できない\n（各期間でトレンドを除いた形。点線のモデルは入国制限の前の緩やかな変化から学ぶため、追いついていない）", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "fig4_inbound_mix.png", dpi=150); plt.close()

# 図5：12か月先の予測の外れ方
fs = pd.read_csv(RES / "forecast_summary.csv")
lab = {"seasonal_naive": "前年の形をそのまま", "fixed": "季節を固定", "time_varying": "季節が年々変わる"}
fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
for ax, name in zip(axes, ["births", "inbound", "power"]):
    x = fs[fs.series == name].set_index("model").loc[["seasonal_naive", "fixed", "time_varying"]]
    bars = ax.bar([lab[i] for i in x.index], x.shape_mae_pct, color=[C["early"], C["alt"], C["late"]])
    for bb, v in zip(bars, x.shape_mae_pct): ax.text(bb.get_x() + bb.get_width() / 2, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_title(SERIES[name], fontsize=11); ax.tick_params(axis="x", labelsize=8); ax.grid(axis="y", alpha=.3)
axes[0].set_ylabel("季節の形の外れ方（%、平均）")
fig.suptitle("翌年12か月の予測：季節を年々変えると、形の外れ方はわずかに小さくなる", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig5_forecast.png", dpi=150); plt.close()
print("ok")
