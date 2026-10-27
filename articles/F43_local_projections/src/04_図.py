"""図を作る（figures/ に PNG で保存）"""
import numpy as np
import pandas as pd
from common import DATA, RES, FIG, LABELS, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, setup_font

plt = setup_font()
P = pd.read_csv(DATA / "panel.csv", parse_dates=["month"], index_col=0)
UNIT = {"ip": "%", "cpi": "%", "unemp": "%ポイント", "fx": "%（上＝円安）"}


def src(fig, extra=""):
    fig.text(0.01, -0.03, SOURCE + extra, fontsize=6.6, color="#8a8984", wrap=True)


# 図1：金利の推移と、月ごとの動きの大きさ
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [2.2, 1]})
ax = axs[0]
ax.plot(P.index, P.call, color=BLUE, lw=1.6, label="短期金利（無担保コール O/N、月平均）")
ax.plot(P.index, P.long, color=ORANGE, lw=1.4, label="長期金利（10年国債）")
ax.axvspan(pd.Timestamp("1985-07-01"), pd.Timestamp("2008-12-01"), color=LIGHT, alpha=0.25)
ax.text(pd.Timestamp("1996-06-01"), 6.6, "基本の推定期間\n1985年7月〜2008年12月", fontsize=9, color=BLUE)
ax.axhline(0, color=INK, lw=0.6); ax.set_ylabel("年%"); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("1995年ごろから短期金利はほぼ0に張り付いた", loc="left", fontsize=12)
vol = pd.read_csv(RES / "rate_volatility.csv", index_col=0)
ax = axs[1]; x = np.arange(len(vol)); w = 0.38
ax.bar(x - w / 2, vol.call, w, color=BLUE, label="短期金利"); ax.bar(x + w / 2, vol.long, w, color=ORANGE, label="長期金利")
for i, (a, b) in enumerate(zip(vol.call, vol.long)):
    ax.text(i - w / 2, a + 0.004, f"{a:.2f}", ha="center", fontsize=8.5); ax.text(i + w / 2, b + 0.004, f"{b:.2f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(["1986〜\n2008年", "1995〜\n2008年", "2009〜\n2026年"]); ax.set_ylabel("前月差の標準偏差（%ポイント）")
ax.legend(frameon=False, fontsize=9); ax.set_title("金利が月に動く大きさ", loc="left", fontsize=12)
src(fig); fig.savefig(FIG / "a43_rates.png"); plt.close(fig)


def irf_grid(df, title, fname, color, note=""):
    fig, axs = plt.subplots(2, 2, figsize=(10.5, 7))
    for ax, v in zip(axs.flat, ["ip", "cpi", "unemp", "fx"]):
        s = df[df["var"] == v]
        ax.fill_between(s.h, s.lo, s.hi, color=color, alpha=0.18, lw=0)
        ax.plot(s.h, s.est, color=color, lw=2)
        ax.axhline(0, color=INK, lw=0.7); ax.set_title(LABELS[v], loc="left", fontsize=11)
        ax.set_xlabel("ショックからの月数"); ax.set_ylabel(UNIT[v]); ax.set_xticks([0, 6, 12, 18, 24, 30, 36])
    fig.suptitle(title, x=0.01, ha="left", fontsize=13)
    fig.tight_layout(); src(fig, note); fig.savefig(FIG / fname); plt.close(fig)


V = pd.read_csv(RES / "irf_var_main.csv"); L = pd.read_csv(RES / "irf_lp_main.csv")
irf_grid(V, "VAR：短期金利が0.25%ポイント上がったとき（1985〜2008年、帯は90%区間）", "a43_var.png", BLUE,
         "（帯は残差ブートストラップ400回）")
irf_grid(L, "局所射影：同じショック・同じ制御変数で、月数ごとに回帰（帯は90%区間）", "a43_lp.png", ORANGE,
         "（帯は Newey–West の標準誤差）")

# 図4：VAR と局所射影の比較（生産・物価）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, v in zip(axs, ["ip", "cpi"]):
    for df, c, lab in [(V, BLUE, "VAR"), (L, ORANGE, "局所射影")]:
        s = df[df["var"] == v]
        ax.fill_between(s.h, s.lo, s.hi, color=c, alpha=0.13, lw=0); ax.plot(s.h, s.est, color=c, lw=2, label=lab)
    ax.axhline(0, color=INK, lw=0.7); ax.set_title(LABELS[v], loc="left", fontsize=12); ax.set_xlabel("ショックからの月数"); ax.set_ylabel("%")
    ax.set_xticks([0, 6, 12, 18, 24, 30, 36]); ax.legend(frameon=False, fontsize=9)
fig.suptitle("同じ識別でも、2つの手法の形は違った。生産が下がるのは局所射影の3年後だけ", x=0.01, ha="left", fontsize=12.5)
fig.tight_layout(); src(fig); fig.savefig(FIG / "a43_compare.png"); plt.close(fig)

# 図5：長期金利のショック（1995〜2026年 と 2009〜2026年）
R = pd.read_csv(RES / "robustness.csv")
VL = pd.read_csv(RES / "irf_var_long.csv"); LL = pd.read_csv(RES / "irf_lp_long.csv")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, v in zip(axs, ["ip", "cpi"]):
    for df, c, lab in [(VL, BLUE, "VAR"), (LL, ORANGE, "局所射影")]:
        s = df[df["var"] == v]
        ax.fill_between(s.h, s.lo, s.hi, color=c, alpha=0.13, lw=0); ax.plot(s.h, s.est, color=c, lw=2, label=lab)
    ax.axhline(0, color=INK, lw=0.7); ax.set_title(LABELS[v], loc="left", fontsize=12); ax.set_xlabel("ショックからの月数"); ax.set_ylabel("%")
    ax.set_xticks([0, 6, 12, 18, 24, 30, 36]); ax.legend(frameon=False, fontsize=9)
fig.suptitle("長期金利が0.25%ポイント上がったとき（1995〜2026年）：生産はむしろ増えた", x=0.01, ha="left", fontsize=12.5)
fig.tight_layout(); src(fig, "（長期金利は景気がよいときに上がるため、ショックがうまく取り出せていないと考えられる）"); fig.savefig(FIG / "a43_long.png"); plt.close(fig)

# 図6：頑健性（24か月後の生産・物価）
cases = list(dict.fromkeys(R["case"]))
fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.4), sharey=True)
for ax, v in zip(axs, ["ip", "cpi"]):
    s = R[(R["var"] == v) & (R.h == 24)].set_index("case").loc[cases]
    y = np.arange(len(cases))
    ax.errorbar(s.var_est, y + 0.15, xerr=[s.var_est - s.var_lo, s.var_hi - s.var_est], fmt="o", color=BLUE, ms=5, capsize=2, label="VAR")
    ax.errorbar(s.lp_est, y - 0.15, xerr=[s.lp_est - s.lp_lo, s.lp_hi - s.lp_est], fmt="s", color=ORANGE, ms=5, capsize=2, label="局所射影")
    ax.axvline(0, color=INK, lw=0.7); ax.set_title(f"{LABELS[v]}（24か月後、%）", loc="left", fontsize=11)
    ax.set_yticks(y); ax.set_yticklabels(cases, fontsize=8.5)
axs[0].invert_yaxis(); axs[0].legend(frameon=False, fontsize=9, loc="lower left")
fig.suptitle("設定を変えると、生産の向きも物価の上がり方も入れ替わった", x=0.01, ha="left", fontsize=12.5)
fig.tight_layout(); src(fig); fig.savefig(FIG / "a43_robust.png"); plt.close(fig)
print("figures done")
