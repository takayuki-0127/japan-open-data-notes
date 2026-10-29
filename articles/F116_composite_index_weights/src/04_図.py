"""図を描く（県の名前は出さず、地方の色だけで示す）。"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import kendalltau
from common import DATA, RES, FIG, SEED

meta = pd.read_csv(DATA / "indicator_meta.csv", index_col=0)
X = pd.read_csv(DATA / "indicators_main.csv", index_col=0)
S = json.load(open(RES / "summary.json"))
rk = pd.read_csv(RES / "ranks_by_scheme.csv", index_col=0)
iv = pd.read_csv(RES / "rank_intervals_by_pref.csv")
bod = pd.read_csv(RES / "bod_alpha.csv")

def region(c):
    for lo, hi, nm in [(1, 1, "北海道"), (2, 7, "東北"), (8, 14, "関東"), (15, 23, "中部"), (24, 30, "近畿"),
                       (31, 35, "中国"), (36, 39, "四国"), (40, 47, "九州・沖縄")]:
        if lo <= c <= hi:
            return nm
REG = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
COL = dict(zip(REG, plt.cm.tab10(np.arange(8))))

# 図1 指標どうしの相関（向きをそろえたあと）
Z = X.values * meta["sign"].values
C = np.corrcoef(Z, rowvar=False)
fig, ax = plt.subplots(figsize=(8.6, 7.4))
im = ax.imshow(C, cmap="RdBu_r", vmin=-1, vmax=1)
lab = [f"{s}（{d}）" for s, d in zip(meta["short"], meta["domain"])]
ax.set_xticks(range(len(lab))); ax.set_yticks(range(len(lab)))
ax.set_xticklabels(lab, rotation=90, fontsize=7); ax.set_yticklabels(lab, fontsize=7)
fig.colorbar(im, ax=ax, shrink=0.8, label="相関係数（どれも「大きいほど暮らしやすい」向き）")
ax.set_title(f"向きをそろえても、指標の組の{S['corr_share_negative']*100:.0f}%は逆向きに動く（47都道府県）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig1_indicator_correlation.png"); plt.close(fig)

# 図2 作り方ごとの順位（線は県。名前は出さない）
cols = list(rk.columns)
short = ["基準\n（z得点・等ウエイト）", "分野を\n等ウエイト", "第1主成分\nの負荷量", "主成分6個\nを寄与率で", "最小最大\nで正規化", "順位で\n正規化", "幾何平均", "データ包絡\n（下限3%）"]
fig, ax = plt.subplots(figsize=(10, 6.2))
for c in rk.index:
    ax.plot(range(len(cols)), rk.loc[c].values, color=COL[region(c)], alpha=0.65, lw=1.2, marker="o", ms=3)
ax.invert_yaxis(); ax.set_xticks(range(len(cols))); ax.set_xticklabels(short, fontsize=8)
ax.set_ylabel("順位（1が最も高い得点）"); ax.set_yticks([1, 10, 20, 30, 40, 47])
for r in REG:
    ax.plot([], [], color=COL[r], label=r)
ax.legend(ncol=8, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), frameon=False)
sp = S["spread_across_schemes"]
ax.set_title(f"同じ20指標でも、作り方を変えると順位が動く（8通りで最大と最小の差：中央値{sp['median']:.0f}位、最大{sp['max']:.0f}位）", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig2_rank_by_scheme.png"); plt.close(fig)

# 図3 重みをでたらめに変えたときの順位の幅
fig, axes = plt.subplots(1, 2, figsize=(10.5, 7), sharey=True)
for ax, kind, ttl in zip(axes, ["indicator", "domain"], ["20指標の重みをでたらめに（10,000回）", "6分野の重みをでたらめに（10,000回）"]):
    d = iv[iv.kind == kind].sort_values("base_rank").reset_index(drop=True)
    for i, r in d.iterrows():
        cc = COL[region(int(r.pref_code))]
        ax.plot([r.p05, r.p95], [i + 1, i + 1], color=cc, lw=2.4, alpha=0.8)
        ax.plot(r.base_rank, i + 1, "k|", ms=6)
    ax.set_xlim(0.5, 47.5)
    ax.set_xlabel("順位（5〜95%点の範囲、｜は基準の順位）"); ax.set_title(ttl, fontsize=10)
    m = S["mc"][kind]
    ax.text(46.5, 1.5, f"幅の中央値 {m['幅（5〜95%点）の中央値']:.0f}位\n幅20位以上 {m['幅が20位以上の県']}県", ha="right", va="top", fontsize=8.5,
            bbox=dict(fc="white", ec="0.7"))
axes[0].set_ylabel("県（基準の順位の順。名前は出していない）"); axes[0].invert_yaxis()
for r in REG:
    axes[1].plot([], [], color=COL[r], lw=3, label=r)
axes[1].legend(fontsize=7.5, loc="lower left", ncol=2)
fig.suptitle("重みの決め方しだいで、多くの県は20位以上の幅で動く", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "fig3_rank_intervals.png"); plt.close(fig)

# 図4 データ包絡：各県に一番有利な重みを選ばせると
fig, ax = plt.subplots(figsize=(7.6, 4.6))
x = bod["重みの下限（合計に対する割合）"] * 100
ax.bar(x, bod["得点1（最良）の県"], width=0.7, color="#4C72B0", label="得点1（1位タイ）の県")
ax.plot(x, bod["得点0.95以上の県"], "o-", color="#DD8452", label="得点0.95以上の県")
for xi, v in zip(x, bod["得点1（最良）の県"]):
    ax.text(xi, v + 0.8, f"{v}", ha="center", fontsize=9)
ax.set_xlabel("各指標の重みの下限（合計に対する%。5%は全指標が等ウエイト）")
ax.set_ylabel("県の数（47のうち）"); ax.set_ylim(0, 52); ax.legend(fontsize=9)
ax.set_title("各県に一番有利な重みを選ばせると、下限を置かない限り47県すべてが1位タイ", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig4_bod.png"); plt.close(fig)

# 図5 頑健性：基準の順位とのケンドールτ
rng = np.random.default_rng(SEED)
Zs = (Z - Z.mean(0)) / Z.std(0)
base = rk.iloc[:, 0].values
def rk_of(s): return pd.Series(-s).rank().values
t10 = [kendalltau(base, rk_of(Zs[:, rng.choice(20, 10, replace=False)].mean(1)))[0] for _ in range(1000)]
W = rng.dirichlet(np.ones(20), size=2000)
tw = [kendalltau(base, rk_of(Zs @ w))[0] for w in W]
drop = pd.read_csv(RES / "drop_one.csv")
fig, ax = plt.subplots(figsize=(8.6, 4.8))
ax.hist(tw, bins=40, alpha=0.6, color="#4C72B0", label="20指標の重みをでたらめに（2,000回）", density=True)
ax.hist(t10, bins=40, alpha=0.6, color="#DD8452", label="20指標から10個をでたらめに選ぶ（1,000回）", density=True)
for t in drop["τ"]:
    ax.axvline(t, color="#55A868", lw=0.8, alpha=0.7)
ax.axvline(np.nan, color="#55A868", label="指標を1つ外す（20通り、緑の線）")
sch = pd.DataFrame(S["schemes"])
for _, r in sch.iloc[1:].iterrows():
    ax.plot(r["基準とのケンドールτ"], 0.15, "kv", ms=6)
ax.plot([], [], "kv", label="作り方を変える（7通り、▼）")
ax.set_xlabel("基準の順位とのケンドールのτ（1なら同じ並び）"); ax.set_ylabel("密度"); ax.legend(fontsize=8.5, loc="upper left")
ax.set_title("1つの指標を外す程度なら並びはほぼ保たれるが、重みや指標の選び方を変えると大きく崩れる", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "fig5_robustness.png"); plt.close(fig)
print("ok")
