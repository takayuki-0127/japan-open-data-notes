"""P02 図。results/ から figures/ を作る。使い方: cd src && python p02_fig.py"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
R, FG = HERE / "results", HERE / "figures"; FG.mkdir(exist_ok=True)
BLUE, ORANGE, GREEN, GRAY, RED = "#1f5f8b", "#c0692b", "#2e7d4f", "#9a9a9a", "#b5452b"
def clean(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)

# 図1 SRM
A = pd.read_csv(R / "A_srm.csv")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.3), dpi=120)
cols = {0.005: "#9bb7cf", 0.01: BLUE, 0.02: ORANGE, 0.05: RED}
for loss, c in cols.items():
    d = A[A.loss == loss]
    axs[0].plot(d.days, d.srm_detect_rate_p001 * 100, marker="o", color=c, label=f"処置群の記録が {loss*100:g}% 落ちる")
    axs[1].plot(d.days, d.mean_lift_hat * 100, marker="o", color=c, label=f"{loss*100:g}% 落ちる")
d0 = A[A.loss == 0]
axs[1].plot(d0.days, d0.mean_lift_hat * 100, marker="o", color=GRAY, ls="--", label="落ちない")
axs[0].set_title("割り付けの比率のずれ（SRM）を見つけられた割合\nカイ二乗検定 p<0.001・効果なし（A/A）", fontsize=10)
axs[0].set_xlabel("日数（1日 5,000人）"); axs[0].set_ylabel("%"); axs[0].legend(fontsize=8)
axs[1].axhline(0, color="#444", lw=.8)
axs[1].set_title("そのときの「効果」の推定（本当は 0%）", fontsize=10)
axs[1].set_xlabel("日数"); axs[1].set_ylabel("相対差の平均（%）"); axs[1].legend(fontsize=8)
for ax in axs: clean(ax); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FG / "p02_01_srm.png"); plt.close(fig)

# 図2 トレンドに見える効果／縮まない幅
B1 = pd.read_csv(R / "B1_aa_trend.csv"); P = np.load(R / "B1_paths_sample.npy")
B2 = pd.read_csv(R / "B2_ci_width.csv")
fig, axs = plt.subplots(1, 3, figsize=(13, 4.2), dpi=120)
for p in P:
    axs[0].plot(np.arange(1, len(p) + 1), p * 100, color=BLUE, alpha=.35, lw=1)
axs[0].axhline(0, color="#444", lw=.8)
axs[0].set_title("効果なし（A/A）の累積の差を毎日見る\n30回分", fontsize=10); axs[0].set_xlabel("日"); axs[0].set_ylabel("処置÷対照−1（%）")
axs[1].bar(B1.day, B1.share_outside_final_ci * 100, color=ORANGE)
axs[1].set_title("その日の推定が、14日目の95%区間の\n外にある割合", fontsize=10); axs[1].set_xlabel("日"); axs[1].set_ylabel("%")
axs[2].plot(B2.days, B2.rel_ci_buy * 100, marker="o", color=GREEN, label="1回でも買った割合")
axs[2].plot(B2.days, B2.rel_ci_sessions * 100, marker="o", color=RED, label="1人あたりの訪問数")
axs[2].set_title("区間の半分の幅（相対・%）\n日数を延ばしたとき", fontsize=10); axs[2].set_xlabel("日数"); axs[2].legend(fontsize=8)
for ax in axs: clean(ax); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FG / "p02_02_trend_width.png"); plt.close(fig)

# 図3 CUPED
C = pd.read_csv(R / "C_cuped.csv")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), dpi=120, gridspec_kw={"width_ratios": [1.3, 1]})
rr = np.linspace(0, 0.95, 50)
axs[0].plot(rr, (1 - rr ** 2) * 100, color=GRAY, ls="--", label="論文の式：1−ρ²")
pre = C[(C.new_share == 0) & (C.pre_days > 0)]
axs[0].scatter(pre.rho, pre.var_ratio * 100, color=BLUE, zorder=3, label="前の期間の長さを変えた")
for _, r in pre.iterrows():
    axs[0].annotate(f"{int(r.pre_days)}日", (r.rho, r.var_ratio * 100), textcoords="offset points", xytext=(5, 4), fontsize=8)
nw = C[C.new_share > 0]
axs[0].scatter(nw.rho, nw.var_ratio * 100, color=ORANGE, marker="s", zorder=3, label="前の期間14日・新規の人あり")
for _, r in nw.iterrows():
    axs[0].annotate(f"新規{int(r.new_share*100)}%", (r.rho, r.var_ratio * 100), textcoords="offset points", xytext=(5, -10), fontsize=8)
axs[0].set_xlabel("テスト中の値と前の値の相関 ρ"); axs[0].set_ylabel("調整後の分散 ÷ 調整前（%）")
axs[0].set_title("CUPED で残る分散は、ほぼ 1−ρ² になる", fontsize=10); axs[0].legend(fontsize=8)
bad = C[C.setting.str.contains("やってはいけない")].iloc[0]
good = C[C.setting == "前の期間 14日"].iloc[0]
axs[1].bar(["本当の効果", "調整なし", "前の14日で調整", "テスト中の値で調整"],
           [3.0, good.mean_raw * 100, good.mean_adj * 100, bad.mean_adj * 100], color=[GRAY, BLUE, GREEN, RED])
axs[1].set_ylabel("推定した効果の平均（%）"); axs[1].set_title("処置の影響を受ける値で調整すると\n効果が消える", fontsize=10)
axs[1].tick_params(axis="x", labelsize=8)
for ax in axs: clean(ax)
axs[0].grid(alpha=.3)
fig.tight_layout(); fig.savefig(FG / "p02_03_cuped.png"); plt.close(fig)

# 図4 mSPRT
D = pd.read_csv(R / "D_msprt.csv"); path = json.load(open(R / "D_path_example.json"))
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.4), dpi=120, gridspec_kw={"width_ratios": [1, 1.3]})
days = np.arange(1, len(path["naive"]) + 1)
axs[0].plot(days, path["naive"], marker="o", color=RED, label="ふつうの p 値（毎日計算）")
axs[0].plot(days, path["msprt"], marker="o", color=BLUE, label="いつ見てもよい p 値（mSPRT）")
axs[0].axhline(0.05, color="#444", ls="--", lw=.8); axs[0].set_yscale("log")
axs[0].set_title("効果なしの1例：ふつうの p 値は途中で 0.05 を割る\n（いつ見てもよい p 値は下がるだけで、戻らない）", fontsize=10)
axs[0].set_xlabel("日"); axs[0].set_ylabel("p 値（対数軸）"); axs[0].legend(fontsize=8)
order = ["14日目に1回だけ見る", "毎日見て p<0.05 で止める", "1時間ごとに見て p<0.05 で止める",
         "mSPRT τ=基準の5%", "mSPRT τ=基準の10%", "mSPRT τ=基準の20%", "mSPRT τ=基準の40%"]
x = np.arange(len(order))
f0 = D[D.truth == "差なし"].set_index("method").loc[order].reject * 100
f1 = D[D.truth == "+10%"].set_index("method").loc[order].reject * 100
axs[1].bar(x - 0.2, f0, width=0.4, color=RED, label="差がないのに「差あり」（誤検出）")
axs[1].bar(x + 0.2, f1, width=0.4, color=BLUE, label="+10% を見つけた（検出力）")
axs[1].set_xticks(x, ["固定\n14日目", "毎日\n見る", "1時間ごと\n見る", "mSPRT\nτ 5%", "mSPRT\nτ 10%", "mSPRT\nτ 20%", "mSPRT\nτ 40%"], fontsize=8)
axs[1].axhline(5, color="#444", ls="--", lw=.8); axs[1].set_ylabel("%"); axs[1].legend(fontsize=8)
axs[1].set_title("14日まで・1時間ごとに見た場合（各4,000回）", fontsize=10)
for ax in axs: clean(ax)
fig.tight_layout(); fig.savefig(FG / "p02_04_msprt.png"); plt.close(fig)
print("ok")
