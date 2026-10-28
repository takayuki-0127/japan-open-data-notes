import numpy as np, pandas as pd
from common import RES, FIG, plt

cv = pd.read_csv(RES / "curves.csv")
er = pd.read_csv(RES / "curve_errors.csv")
hr = pd.read_csv(RES / "hazard_ratios.csv")
def curve(s, m):
    c = cv[(cv.scheme == s) & (cv.method == m)].sort_values("month")
    return c.month / 12, 100 * (1 - c.S)
TRUE = ("真の値", "KM（日単位）")

# 図1 区間打ち切りとは（模式図）
fig, ax = plt.subplots(figsize=(8, 3.6))
surveys = [2016.75, 2021.75, 2026.75]
for x in surveys:
    ax.axvline(x, color="#999", ls=":", lw=1)
    ax.text(x, 4.75, f"調査\n{int(x)}年9月", ha="center", va="bottom", fontsize=8, color="#555")
ex = [(2016.2, 2019.4, 1), (2017.5, 2023.1, 1), (2019.0, None, 0), (2022.3, 2024.0, 1)]
for i, (s, e, evt) in enumerate(ex):
    y = 4 - i
    ax.plot([s, e if e else 2026.75], [y, y], color="#bbb", lw=6, solid_capstyle="butt")
    ax.plot(s, y, "o", color="#333")
    if evt:
        ax.plot(e, y, "x", color="#c0392b", ms=10, mew=2)
        lo = max([u for u in surveys if u < e] + [s]); hi = min(u for u in surveys if u >= e)
        ax.annotate("", xy=(hi, y - 0.32), xytext=(lo, y - 0.32), arrowprops=dict(arrowstyle="<->", color="#2c7fb8", lw=1.6))
        ax.text((lo + hi) / 2, y - 0.62, "この間のどこかで閉鎖", ha="center", fontsize=8, color="#2c7fb8")
    else:
        ax.text(2026.9, y, "残っている（打ち切り）", va="center", fontsize=8)
ax.set_xlim(2015.5, 2029.3); ax.set_ylim(0.2, 5.4); ax.set_yticks([]); ax.set_xlabel("年")
ax.set_title("5年おきの調査だと、閉鎖の日は分からず「どの調査の間か」だけが分かる\n●設立　×本当の閉鎖日（調査では見えない）", fontsize=10)
for sp in ["left", "right", "top"]: ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "f105_concept.png", dpi=150); plt.close()

# 図2 Turnbull で、調査の間隔を変えても曲線は戻るか
fig, ax = plt.subplots(figsize=(7.5, 4.6))
x, y = curve(*TRUE); ax.plot(x, y, color="black", lw=2.6, label="本当の値（閉鎖日が分かる）")
for s, c in [("1年おき", "#2c7fb8"), ("5年おき", "#e6550d"), ("1回だけ（2026-09-30）", "#31a354")]:
    x, y = curve(s, "Turnbull"); ax.plot(x, y, color=c, lw=1.6, label=f"{s}の調査から（Turnbull）")
ax.set_xlim(0, 10); ax.set_ylim(0, 12); ax.set_xlabel("設立からの年数"); ax.set_ylabel("閉鎖した割合（%）")
ax.set_title("仮定を置かない Turnbull 推定なら、5年おきや1回だけの調査でも曲線はほぼ戻る", fontsize=10)
ax.legend(fontsize=8.5, loc="upper left"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f105_turnbull.png", dpi=150); plt.close()

# 図3 5年おきの調査で、簡単な方法と比べる
fig, ax = plt.subplots(figsize=(7.5, 4.6))
x, y = curve(*TRUE); ax.plot(x, y, color="black", lw=2.6, label="本当の値")
for m, c, ls in [("右端で代入", "#c0392b", "-"), ("中点で代入", "#8e44ad", "-"), ("Turnbull", "#e6550d", "--"), ("対数正規", "#2c7fb8", "--")]:
    x, y = curve("5年おき", m); ax.plot(x, y, color=c, lw=1.7, ls=ls, label={"右端で代入": "閉鎖を確認した調査の日を閉鎖日とみなす（右端）", "中点で代入": "2つの調査の真ん中を閉鎖日とみなす（中点）", "Turnbull": "Turnbull（区間のまま）", "対数正規": "対数正規（区間のまま）"}[m])
ax.set_xlim(0, 10); ax.set_ylim(0, 16); ax.set_xlabel("設立からの年数"); ax.set_ylabel("閉鎖した割合（%）")
ax.set_title("5年おきの調査：「見つけた日＝閉鎖日」とすると、5年後は3.5%（本当は5.3%）", fontsize=10)
ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f105_methods.png", dpi=150); plt.close()

# 図4 誤差のヒートマップ
S = ["1年おき", "2年おき", "3年おき", "5年おき", "1回だけ（2026-09-30）"]
Mth = ["右端で代入", "中点で代入", "Turnbull", "区分指数（1年ごと）", "ワイブル", "対数ロジスティック", "対数正規"]
P = er.pivot_table(index="method", columns="scheme", values="max_abs_err_pt").loc[Mth, S]
fig, ax = plt.subplots(figsize=(8, 4.4))
im = ax.imshow(P.values, cmap="Reds", vmin=0, vmax=4)
for i in range(len(Mth)):
    for j in range(len(S)):
        v = P.values[i, j]; ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=9, color="white" if v > 2.5 else "black")
ax.set_xticks(range(len(S))); ax.set_xticklabels(["1年おき", "2年おき", "3年おき", "5年おき", "1回だけ"])
ax.set_yticks(range(len(Mth))); ax.set_yticklabels(["右端で代入", "中点で代入", "Turnbull（仮定なし）", "区分指数（1年ごと）", "ワイブル", "対数ロジスティック", "対数正規"])
ax.set_title("0〜10年の閉鎖割合の、本当の値からの最大のずれ（ポイント）", fontsize=10)
fig.colorbar(im, ax=ax, shrink=.8, label="ポイント")
fig.tight_layout(); fig.savefig(FIG / "f105_error_heatmap.png", dpi=150); plt.close()

# 図5 ハザード比
order = ["1年おき", "2年おき", "3年おき", "5年おき", "1回だけ（2026-09-30）"]
fig, axes = plt.subplots(1, 2, figsize=(9, 4.6), sharey=True)
for ax, v in zip(axes, ["合同会社", "東京23区"]):
    tv = hr[(hr.scheme == "真の値") & (hr["var"] == v)].HR.iloc[0]
    ax.axvline(tv, color="black", lw=1.5, label="本当の値（閉鎖日を使う）")
    for k, (m, c, off) in enumerate([("区間打ち切り", "#e6550d", -0.2), ("中点で代入", "#8e44ad", 0), ("右端で代入", "#c0392b", 0.2)]):
        h = hr[(hr["var"] == v) & (hr.method == m)].set_index("scheme").loc[order]
        yy = np.arange(len(order)) + off
        ax.errorbar(h.HR, yy, xerr=[h.HR - h.lo, h.hi - h.HR], fmt="o", color=c, ms=4, label=m)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(["1年おき", "2年おき", "3年おき", "5年おき", "1回だけ"])
    ax.invert_yaxis(); ax.set_title(f"{v}のハザード比", fontsize=10); ax.grid(alpha=.3, axis="x")
h_, l_ = axes[0].get_legend_handles_labels()
fig.legend(h_, l_, fontsize=8.5, loc="lower center", ncol=4, frameon=False)
fig.suptitle("差（ハザード比）は、区間のまま扱えば1回だけの調査でもほぼ同じ。右端で代入するとずれる", fontsize=10)
fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(FIG / "f105_hr.png", dpi=150); plt.close()
print("ok")
