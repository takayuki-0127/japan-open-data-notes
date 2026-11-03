"""図を6枚つくる（figures/）。"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

FIG.mkdir(exist_ok=True)
ORDER = ["Cox", "Cox＋交互作用", "Cox＋スプライン", "RSF", "GBM-Cox", "GBM-Cox(深さ1)", "GBM-離散時間"]
COL = {"Cox": "#555555", "Cox＋交互作用": "#999999", "Cox＋スプライン": "#bbbbbb", "RSF": "#2a9d8f", "GBM-Cox": "#e76f51",
       "GBM-Cox(深さ1)": "#f4a261", "GBM-離散時間": "#264653"}
main = pd.concat([pd.read_csv(RES / "main_metrics.csv"), pd.read_csv(RES / "decomp_metrics.csv")])
main["gain"] = (1 - main.IBS / main.IBS_KM) * 100
models = [m for m in ORDER if m in set(main.model)]

# 図1：C 指数と、KM に比べた Brier スコアの改善（5回の分割、点＝各回、棒＝平均）
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
for a, (col, lab) in zip(ax, [("C_uno", "Uno の C 指数（8年まで）"), ("gain", "統合 Brier スコアの改善（%、特徴量なしの KM 比）")]):
    for i, m in enumerate(models):
        v = main.loc[main.model == m, col].values
        a.barh(i, v.mean(), color=COL[m], alpha=0.85)
        a.scatter(v, np.full(len(v), i) + np.linspace(-0.25, 0.25, len(v)), s=12, color="k", zorder=3)
        a.text(v.max(), i, f"  {v.mean():.3f}" if col == "C_uno" else f"  {v.mean():.2f}", va="center", ha="left", fontsize=9)
    a.set_yticks(range(len(models))); a.set_yticklabels(models); a.invert_yaxis(); a.set_title(lab, fontsize=11)
    if col == "C_uno":
        a.set_xlim(0.5, 0.635); a.axvline(0.5, color="k", lw=0.5)
ax[1].set_yticklabels([]); ax[1].set_xlim(0, 2.2)
fig.suptitle("10万社・閉鎖までの時間：機械学習でも Cox とほぼ同じ（ランダム分割 70:30 を5回）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig1_model_comparison.png", dpi=150); plt.close(fig)

# 図2：時点別 AUC（5回の平均）
fig, ax = plt.subplots(figsize=(7.5, 4.6))
d = main[main.model.isin(["Cox", "RSF", "GBM-Cox", "GBM-離散時間"])].groupby("model")[["AUC_1y", "AUC_3y", "AUC_5y"]].mean()
for m, r in d.iterrows():
    ax.plot([1, 3, 5], r.values, "-o", color=COL[m], label=m, lw=2)
ax.set_xticks([1, 3, 5]); ax.set_xticklabels(["1年", "3年", "5年"]); ax.set_ylabel("時点別 AUC（累積／動的）")
ax.set_title("「何年以内に閉鎖するか」の見分けやすさ：差は 0.01〜0.02", fontsize=12); ax.legend(frameon=False); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "fig2_auc_by_time.png", dpi=150); plt.close(fig)

# 図3：5年の較正（十分位ごとの予測と実績、5回の平均）
cal = pd.read_csv(RES / "calibration_main.csv")
cal = cal[(cal.t == 5) & cal.model.isin(["Cox", "RSF", "GBM-Cox", "GBM-離散時間"])].groupby(["model", "decile"])[["pred", "obs"]].mean().reset_index()
fig, ax = plt.subplots(figsize=(6.2, 5.6))
for m, g in cal.groupby("model"):
    ax.plot(g.pred * 100, g.obs * 100, "-o", color=COL[m], label=m, ms=4)
lim = max(cal.pred.max(), cal.obs.max()) * 100 * 1.08
ax.plot([0, lim], [0, lim], "k--", lw=0.8); ax.set_xlim(0, lim); ax.set_ylim(0, lim)
ax.set_xlabel("予測した5年以内の閉鎖率（%、十分位ごとの平均）"); ax.set_ylabel("実際（KM、%）")
ax.set_title("5年の較正：どのモデルも対角線の近く。\n予測の幅は 3%〜12% ほどしかない", fontsize=11); ax.legend(frameon=False); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "fig3_calibration_5y.png", dpi=150); plt.close(fig)

# 図4：検証の分け方・特徴量・標本の大きさを変えたときの「Cox との差」（Uno の C）
rows = []
def add(df, label, key=None):
    for m in ["RSF", "GBM-Cox", "GBM-離散時間"]:
        base = df[df.model == "Cox"].set_index(key)["C_uno"] if key else df[df.model == "Cox"]["C_uno"]
        x = df[df.model == m].set_index(key)["C_uno"] if key else df[df.model == m]["C_uno"]
        diff = (x - base).values if key else x.values - base.values
        rows.append({"setting": label, "model": m, "mean": np.mean(diff), "lo": np.min(diff), "hi": np.max(diff)})
mm = pd.read_csv(RES / "main_metrics.csv"); add(mm, "ランダム分割（基本）", "split")
for f, lab, key in [("group_metrics.csv", "都道府県で分ける", "fold"), ("temporal_metrics.csv", "時間で分ける（2021年以降の設立を評価）", None),
                    ("e01_metrics.csv", "閉鎖＝清算の結了等だけ", None)]:
    p = RES / f
    if p.exists():
        add(pd.read_csv(p), lab, key)
p = RES / "feat_metrics.csv"
if p.exists():
    fe = pd.read_csv(p)
    for fs, lab in [("all_no_rate", "市区町村の閉鎖率を除く"), ("basic", "特徴量4つだけ")]:
        add(fe[fe.featset == fs], lab)
p = RES / "lc_metrics.csv"
if p.exists():
    lc = pd.read_csv(p)
    for n in (30000, 10000):
        add(lc[lc.n == n], f"標本 {n//10000}万社" if n >= 10000 else f"標本 {n}", "split")
r = pd.DataFrame(rows); r.to_csv(RES / "delta_vs_cox.csv", index=False)
sets = list(dict.fromkeys(r.setting))
fig, ax = plt.subplots(figsize=(9, 0.55 * len(sets) + 1.6))
for j, m in enumerate(["RSF", "GBM-Cox", "GBM-離散時間"]):
    g = r[r.model == m].set_index("setting").reindex(sets)
    y = np.arange(len(sets)) + (j - 1) * 0.25
    ax.errorbar(g["mean"], y, xerr=[g["mean"] - g.lo, g.hi - g["mean"]], fmt="o", color=COL[m], label=m, capsize=2)
ax.axvline(0, color="k", lw=0.8); ax.set_yticks(range(len(sets))); ax.set_yticklabels(sets); ax.invert_yaxis()
ax.set_xlabel("Uno の C 指数の差（機械学習 − Cox）。点＝平均、線＝分割ごとの最小〜最大")
ax.set_title("平均の差は、どの条件でも ±0.02 の中（1万社では分割ごとのぶれが大きい）", fontsize=12); ax.legend(frameon=False, loc="upper right"); ax.grid(alpha=0.3, axis="x")
fig.tight_layout(); fig.savefig(FIG / "fig4_robustness_delta.png", dpi=150); plt.close(fig)

# 図5：半合成データ（本当のハザードを決めて作り直す）
p = RES / "synth_metrics.csv"
if p.exists():
    sy = pd.read_csv(p)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    truths = ["線形", "曲がり・交互作用あり"]; ms = ["本当のリスク", "Cox", "Cox＋交互作用", "RSF", "GBM-Cox", "GBM-離散時間"]
    w = 0.13
    for i, m in enumerate(ms):
        v = [sy[(sy.truth == t) & (sy.model == m)].C_uno.mean() for t in truths]
        ax.bar(np.arange(2) + (i - 2.5) * w, v, w, color=COL.get(m, "#e9c46a"), label=m)
        for k, x in enumerate(v):
            ax.text(k + (i - 2.5) * w, x + 0.003, f"{x:.3f}", ha="center", fontsize=7.5, rotation=90)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["本当のハザードが線形", "曲がり・交互作用あり"]); ax.set_ylim(0.5, max(0.7, sy.C_uno.max() + 0.04))
    ax.set_ylabel("Uno の C 指数"); ax.legend(frameon=False, ncol=3, fontsize=9, loc="upper left")
    ax.set_title("半合成データ：曲がりや交互作用が本当にあれば、機械学習はそれを拾う", fontsize=12)
    fig.tight_layout(); fig.savefig(FIG / "fig5_semisynthetic.png", dpi=150); plt.close(fig)

# 図6：並べ替えによる特徴量の重要度（C の下がり方）
im = pd.read_csv(RES / "importance.csv"); im = im[im.permuted != "なし"]
order = im[im.model == "GBM-Cox"].sort_values("dC", ascending=False).permuted.tolist()
fig, ax = plt.subplots(figsize=(9, 5.2))
for j, m in enumerate(["Cox", "RSF", "GBM-Cox"]):
    g = im[im.model == m].set_index("permuted").reindex(order)
    ax.barh(np.arange(len(order)) + (j - 1) * 0.27, g.dC, 0.27, color=COL[m], label=m)
ax.set_yticks(range(len(order))); ax.set_yticklabels(order); ax.invert_yaxis(); ax.axvline(0, color="k", lw=0.6)
ax.set_xlabel("その特徴量をばらばらに並べ替えたときの Uno の C の下がり幅")
ax.set_title("同じ精度でも、頼っている特徴量はモデルごとに違う\n（地域区分・都道府県・市区町村の規模・閉鎖率は互いに似た情報）", fontsize=11)
ax.legend(frameon=False, loc="lower right"); ax.grid(alpha=0.3, axis="x")
fig.tight_layout(); fig.savefig(FIG / "fig6_importance.png", dpi=150); plt.close(fig)
print("ok")
