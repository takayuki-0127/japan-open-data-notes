"""F243 04 図（Noto Sans CJK JP）"""
import json, os
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
B = os.path.join(os.path.dirname(__file__), ".."); F = f"{B}/figures"; R = f"{B}/results"
J = json.load(open(f"{R}/main.json")); A = J["A"]

# 図1 シンプソンのパラドックス（架空）
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
lab = ["アプリ", "Web", "全体"]
c0 = [20.0, 2.0, A["全体の購入率0"] * 100]; c1 = [18.0, 1.8, A["全体の購入率1"] * 100]
x = np.arange(3); ax[0].bar(x - 0.2, c0, 0.4, label="前の期間", color="#9aa7b8"); ax[0].bar(x + 0.2, c1, 0.4, label="今の期間", color="#2b6cb0")
for i in range(3): ax[0].text(i - 0.2, c0[i] + 0.4, f"{c0[i]:.1f}%", ha="center", fontsize=10); ax[0].text(i + 0.2, c1[i] + 0.4, f"{c1[i]:.1f}%", ha="center", fontsize=10)
ax[0].set_xticks(x, lab); ax[0].set_ylabel("購入率（%）"); ax[0].set_title("購入率：どちらのチャネルも1割下がったのに、全体は上がった"); ax[0].legend(frameon=False)
s0 = [10, 90]; s1 = [30, 70]
ax[1].barh(["前の期間", "今の期間"], [s0[0], s1[0]], color="#2b6cb0", label="アプリ"); ax[1].barh(["前の期間", "今の期間"], [s0[1], s1[1]], left=[s0[0], s1[0]], color="#c9d3df", label="Web")
for i, (a, b) in enumerate([s0, s1]): ax[1].text(a / 2, i, f"{a}%", ha="center", va="center", color="white"); ax[1].text(a + b / 2, i, f"{b}%", ha="center", va="center")
ax[1].set_xlabel("訪問の割合（%）"); ax[1].set_title("訪問の構成：購入率の高いアプリが10%→30%"); ax[1].legend(frameon=False, loc="lower right")
fig.suptitle("図1 架空の書店（ひかり書店：架空）の購入率。総訪問は20万で同じ", fontsize=12); fig.tight_layout(); fig.savefig(f"{F}/fig1_simpson.png", dpi=150); plt.close()

# 図2 分け方で答えが変わる（架空）
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
nv = A["素朴なツリーのシャープレイ"]
names = ["全体の購入率", "平均点数", "平均単価", "訪問数"]; vals = [nv[n] / 1e4 for n in names]
ax[0].barh(names[::-1], vals[::-1], color="#e67e22")
for i, v in enumerate(vals[::-1]): ax[0].text(v + 20, i, f"{v:+,.0f}万円", va="center", fontsize=10)
ax[0].set_title("チャネルを分けないツリー：\n「購入率が伸びた」に見える"); ax[0].set_xlabel("売上の変化への寄与（万円）"); ax[0].set_xlim(0, 1500)
sh = A["シャープレイ"]; rg = A["順番による幅"]; lm = A["LMDI"]
fac = ["構成", "購入率"]; lab2 = ["チャネル構成", "チャネル別の購入率"]
y = np.arange(2)
for i, f in enumerate(fac):
    ax[1].plot([rg[f][0] / 1e4, rg[f][1] / 1e4], [i, i], color="#888", lw=6, alpha=0.5, solid_capstyle="butt", label="並べる順番での幅（120通り）" if i == 0 else None)
    ax[1].plot(sh[f] / 1e4, i, "o", color="#2b6cb0", ms=9, label="シャープレイ値（順番の平均）" if i == 0 else None)
    ax[1].plot(lm[f] / 1e4, i, "D", color="#c0392b", ms=7, label="LMDI（対数の平均で分ける）" if i == 0 else None)
    ax[1].text(sh[f] / 1e4, i + 0.22, f"{sh[f]/1e4:+,.0f}万円", ha="center", fontsize=10)
ax[1].axvline(0, color="#333", lw=0.8); ax[1].set_yticks(y, lab2); ax[1].set_ylim(-0.6, 1.8)
ax[1].set_title("チャネルを分けたツリー：伸びたのは構成。\n順番で寄与の大きさは±1割ほど動く"); ax[1].set_xlabel("売上の変化への寄与（万円）"); ax[1].legend(frameon=False, fontsize=9, loc="center right")
fig.suptitle(f"図2 同じ売上の伸び（+{A['伸び率']*100:.0f}%、+{(A['売上1']-A['売上0'])/1e4:,.0f}万円）でも、ツリーの切り方で説明が変わる（架空）", fontsize=12)
fig.tight_layout(); fig.savefig(f"{F}/fig2_tree_cut_order.png", dpi=150); plt.close()

# 図3 家計調査：支出の変化を値段と量に（2019→2024、群別）
G = pd.read_csv(f"{R}/B_group_2019_2024.csv").set_index("group").sort_values("変化")
fig, ax = plt.subplots(figsize=(11, 4.8))
yy = np.arange(len(G))
ax.barh(yy, G["価格_S"], color="#c0392b", label="値段の効果"); ax.barh(yy, G["量_S"], color="#2b6cb0", label="量の効果")
ax.plot(G["変化"], yy, "k|", ms=16, mew=2.5, label="支出の変化（合計）")
for i, (g, r) in enumerate(G.iterrows()): ax.text(max(r["価格_S"], 0) + 300, i, f"{r['変化']:+,.0f}円", va="center", fontsize=10)
ax.set_yticks(yy, G.index); ax.axvline(0, color="#333", lw=0.8); ax.set_xlabel("1世帯あたり年間の支出の変化（円）")
b = J["B"]; ax.legend(frameon=False, loc="lower right")
ax.set_title(f"図3 食料127品目の支出 2019→2024年：{b['変化']:+,.0f}円（{b['変化率']*100:+.1f}%）＝値段 {b['価格S']:+,.0f}円＋量 {b['量S']:+,.0f}円（中点で分けた値）", fontsize=12)
fig.tight_layout(); fig.savefig(f"{F}/fig3_kakei_price_qty.png", dpi=150); plt.close()

# 図4 構成の効果：100gあたり平均価格（2019→2024）と、分け方の比較
MX = pd.read_csv(f"{R}/B_mix_rate_by_group.csv"); m = MX[MX["期間"] == "2019→2024"].set_index("群")
m = m.loc[["肉類", "魚介類", "果物", "野菜・海藻", "穀類", "油脂・調味料"]]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [1.3, 1]})
yy = np.arange(len(m))
ax[0].barh(yy - 0.2, m["値段の効果"] / m["100gあたり平均価格0"] * 100, 0.4, color="#c0392b", label="品目の値段（率）")
ax[0].barh(yy + 0.2, m["構成の効果"] / m["100gあたり平均価格0"] * 100, 0.4, color="#7f8c8d", label="品目の構成（ミックス）")
ax[0].plot(m["変化率"] * 100, yy, "k|", ms=16, mew=2.5, label="平均価格の変化")
for i, (g, r) in enumerate(m.iterrows()): ax[0].text(max(r["値段の効果"] / r["100gあたり平均価格0"] * 100, 0) + 0.8, i - 0.2, f"平均 {r['変化率']*100:+.1f}%", va="center", fontsize=9)
ax[0].set_yticks(yy, m.index); ax[0].axvline(0, color="#333", lw=0.8); ax[0].set_xlabel("100gあたり平均価格の変化への寄与（%）"); ax[0].legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3)
ax[0].set_title("100gあたりの平均価格：肉類は品目の値段で+12.6%、\n安い肉へ移った分で−3.8%、合わせて+8.8%")
P = pd.read_csv(f"{R}/B_total_by_method_period.csv"); P = P[P["期間"].isin(["2019→2024", "2004→2024"])]
nm = {"L": "値段を先に", "P": "量を先に", "S": "中点（シャープレイ）", "LMDI": "LMDI"}
for j2, per in enumerate(["2019→2024", "2004→2024"]):
    p = P[P["期間"] == per].set_index("方法").loc[["L", "P", "S", "LMDI"]]
    ax[1].scatter(p["価格"] / 1000, [j2 * 5 + i for i in range(4)], color="#c0392b", s=40)
    for i, (mm, r) in enumerate(p.iterrows()): ax[1].text(r["価格"] / 1000 + 2, j2 * 5 + i, f"{nm[mm]}：値段{r['価格']/1000:+.1f}千円", va="center", fontsize=9)
ax[1].set_yticks([1.5, 6.5], ["2019→2024", "2004→2024"]); ax[1].set_xlim(60, 230); ax[1].set_xlabel("値段の効果（千円）")
ax[1].set_title("分ける順番で値段の効果が変わる。\n期間が長いほど差が大きい")
fig.suptitle("図4 家計調査の食料品：構成の効果と、分け方による違い", fontsize=12); fig.tight_layout(); fig.subplots_adjust(bottom=0.24); fig.savefig(f"{F}/fig4_mix_and_method.png", dpi=150); plt.close()

# 図5 商業動態統計：全店と既存店の前年比
m5 = pd.read_csv(f"{B}/data/meti_yoy_all_vs_existing.csv"); m5["t"] = pd.PeriodIndex(m5.ym, freq="M").to_timestamp()
m5 = m5[m5.t >= "1990-01-01"]
C = pd.read_csv(f"{R}/C_all_vs_existing.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={"width_ratios": [1.6, 1]})
s = m5[m5["業態"] == "スーパー"].set_index("t")
ax[0].plot(s.index, s["全店"].rolling(12).mean(), color="#2b6cb0", label="全店の前年比（12か月平均）")
ax[0].plot(s.index, s["既存店"].rolling(12).mean(), color="#e67e22", label="既存店の前年比（12か月平均）")
ax[0].fill_between(s.index, s["既存店"].rolling(12).mean(), s["全店"].rolling(12).mean(), color="#2b6cb0", alpha=0.12, label="差＝店の数の増減など")
ax[0].axhline(0, color="#333", lw=0.8); ax[0].set_ylabel("前年同月比（%）"); ax[0].legend(frameon=False, fontsize=9); ax[0].set_title("スーパー：全店は伸び、既存店はマイナスの時期が長い")
c = C[~C["時期"].str.startswith("全期間")].pivot(index="時期", columns="業態", values="向きが逆の月の割合") * 100
c.plot.bar(ax=ax[1], color={"スーパー": "#2b6cb0", "百貨店": "#9aa7b8"}, rot=0)
for i, (e, r) in enumerate(c.iterrows()):
    ax[1].text(i - 0.13, r["スーパー"] + 1, f"{r['スーパー']:.0f}", ha="center", fontsize=9); ax[1].text(i + 0.13, r["百貨店"] + 1, f"{r['百貨店']:.0f}", ha="center", fontsize=9)
ax[1].set_ylabel("全店と既存店で前年比の向きが逆の月（%）"); ax[1].set_xlabel(""); ax[1].legend(frameon=False); ax[1].set_title("向きが逆の月の割合")
fig.suptitle("図5 商業動態統計：「売上が伸びた」は、店が増えたからか、1店ごとに伸びたからか（1990年1月〜2026年8月）", fontsize=12)
fig.tight_layout(); fig.savefig(f"{F}/fig5_all_vs_existing.png", dpi=150); plt.close()
print("figs ok")
