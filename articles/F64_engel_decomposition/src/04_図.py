"""04 図"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, AGE6, AGE6_LABEL, setup_font

setup_font()
E = pd.read_csv(RES / "engel_series.csv", index_col=0)
DEC = pd.read_csv(RES / "decomposition.csv")
P = pd.read_csv(DATA / "age_panel.csv")
life = pd.read_csv(RES / "living_standard.csv", index_col=0)

# 図1 エンゲル係数（名目）と、価格を2020年にそろえたエンゲル係数
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(E.index, E["E_品目"], color="#999", lw=1.5, label="エンゲル係数（品目分類、2000年〜）")
ax.plot(E.index, E["E_用途"], color="#c0392b", lw=2.4, label="エンゲル係数（用途分類＝公表の定義）")
ax.plot(E.index, E["E_実質_用途"], color="#2471a3", lw=2.4, ls="--", label="食料の相対価格を2020年にそろえた場合（用途分類）")
ax.set_ylabel("消費支出に占める食料の割合（%）")
ax.set_ylim(20, 31)
ax2 = ax.twinx()
ax2.bar(E.index, E["RP"] * 100, color="#f5b041", alpha=0.25, width=0.8, label="食料の相対価格（2020年=100）")
ax2.set_ylim(60, 130)
ax2.set_ylabel("食料の相対価格（食料÷総合、2020年=100）")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8.5, frameon=False)
ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
ax.set_title("エンゲル係数は上がったが、価格をそろえるとほぼ横ばい（二人以上の世帯）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f64_engel.png"); plt.close(fig)

# 図2 食料の中身：外食・調理食品・素材など（名目と実質）
d = E.loc[2008:2025]
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)
for ax, kind, title in [(axes[0], "", "そのままの金額"), (axes[1], "_実質", "それぞれの価格を2020年にそろえた場合")]:
    if kind == "":
        out = d["外食_用途"]; ready = d["調理食品_用途"]; other = d["E_用途"] - out - ready
    else:
        out = d["外食_実質_用途"]; ready = d["調理食品_実質_用途"]; other = d["素材など_実質_用途"]
    ax.stackplot(d.index, other, ready, out, colors=["#a9cce3", "#f5b041", "#c0392b"],
                 labels=["素材など（米・肉・野菜・菓子・飲料など）", "調理食品（中食）", "外食"])
    ax.set_title(title, fontsize=10)
    ax.set_xlim(2008, 2025)
axes[0].set_ylabel("消費支出に占める割合（%）")
axes[0].legend(loc="lower left", fontsize=8, frameon=True)
fig.suptitle("食料の中身：中食は増えたが、素材などの数量は減った（用途分類、二人以上の世帯）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f64_components.png"); plt.close(fig)

# 図3 2013→2025 などの分解
base = DEC[DEC["設定"].str.startswith("基本")].set_index("期間")
cols = ["相対価格", "所得（消費水準）", "年齢構成", "家計簿改正・コロナ", "残り（好み・外食/中食など）"]
colors = ["#c0392b", "#2471a3", "#27ae60", "#999999", "#8e44ad"]
fig, ax = plt.subplots(figsize=(8, 4.3))
x = np.arange(len(base))
pos = np.zeros(len(base)); neg = np.zeros(len(base))
for c, col in zip(cols, colors):
    v = base[c].values
    b = np.where(v >= 0, pos, neg)
    ax.bar(x, v, bottom=b, color=col, label=c, width=0.55)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.scatter(x, base["変化"], color="black", zorder=3, s=40, label="エンゲル係数の変化（合計）")
for i, v in enumerate(base["変化"]):
    ax.text(i + 0.32, v, f"+{v:.1f}pt", va="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(base.index)
ax.axhline(0, color="black", lw=0.8)
ax.set_ylabel("ポイント")
ax.legend(fontsize=8, frameon=False, loc="upper right")
ax.set_title("エンゲル係数の上昇の分解：大部分は食料の相対価格（二人以上の世帯）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f64_decomp.png"); plt.close(fig)

# 図4 世帯主の年齢別のエンゲル係数と世帯の割合
two = P[(P.kind == "two") & P.group.isin(AGE6)].copy()
two["E"] = 100 * two.F / two.C
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4))
for y, col in [(2013, "#7f8c8d"), (2025, "#c0392b")]:
    t = two[two.year == y].set_index("group").loc[AGE6]
    axes[0].plot(AGE6_LABEL, t.E, marker="o", color=col, label=f"{y}年")
    axes[1].bar(np.arange(6) + (0 if y == 2013 else 0.4), t.w / t.w.sum() * 100, width=0.4, color=col, label=f"{y}年")
axes[0].set_ylabel("エンゲル係数（%）"); axes[0].set_title("世帯主の年齢別のエンゲル係数", fontsize=10); axes[0].legend(frameon=False)
axes[1].set_xticks(np.arange(6) + 0.2); axes[1].set_xticklabels(AGE6_LABEL)
axes[1].set_ylabel("世帯の割合（%）"); axes[1].set_title("世帯の割合（世帯主の年齢別）", fontsize=10); axes[1].legend(frameon=False)
fig.suptitle("どの年齢でも上がった。高齢の世帯が増えた分（年齢構成）は小さい", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f64_age.png"); plt.close(fig)

# 図5 頑健性：設定別の分解（2013→2025）
r = DEC[DEC["期間"].isin(["2013→2025", "2018→2025"])].copy()
fig, ax = plt.subplots(figsize=(8.5, 5.0))
y = np.arange(len(r))
left_p = np.zeros(len(r)); left_n = np.zeros(len(r))
for c, col in zip(cols, colors):
    v = r[c].values
    st = np.where(v >= 0, left_p, left_n)
    ax.barh(y, v, left=st, color=col, label=c, height=0.6)
    left_p += np.where(v >= 0, v, 0); left_n += np.where(v < 0, v, 0)
ax.set_yticks(y); ax.set_yticklabels([f"{a}（{p}）" for a, p in zip(r["設定"], r["期間"])], fontsize=8)
ax.invert_yaxis(); ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("ポイント")
ax.legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.13), ncol=3)
ax.set_title("設定を変えた分解：どの設定でも相対価格がいちばん大きい", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f64_robust.png"); plt.close(fig)

# 図6 生活の物差し：実質消費支出と実質可処分所得
L = life.loc[2008:2025]
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(L.index, L["実質消費支出_二人以上(2013=100)"], color="#c0392b", lw=2.2, label="実質消費支出（二人以上の世帯）")
ax.plot(L.index, L["実質消費支出_等価(2013=100)"], color="#c0392b", lw=1.4, ls="--", label="同・世帯人員の違いをならした値（√世帯人員で割る）")
ax.plot(L.index, L["実質食料_二人以上(2013=100)"], color="#f39c12", lw=2.0, label="実質食料支出（食料の物価で実質化）")
ax.plot(L.index, L["実質可処分所得_勤労者(2013=100)"], color="#2471a3", lw=2.2, label="実質可処分所得（勤労者世帯）")
ax.axhline(100, color="#999", lw=0.8)
ax.set_xticks(range(2008, 2026, 2))
ax.set_ylabel("2013年=100"); ax.legend(fontsize=8, frameon=False, loc="lower left")
ax.set_title("所得は下がっていないが、実質の消費は約8%減った", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f64_living.png"); plt.close(fig)
print("ok")
