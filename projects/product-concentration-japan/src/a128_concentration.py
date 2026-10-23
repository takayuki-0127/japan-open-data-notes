"""記事128：製造品の出荷金額で「一つの県に集中」している品目はどれか（上位1県のシェアとHHI、2024年実績）"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import load, concentration, FIG, RES, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT

df = load()
C = concentration(df)
C.to_csv(RES / "a128_concentration_all.csv", index=False)
MIN = 10000          # 全国の出荷金額100億円（1万百万円）以上の品目
MAXSEC = 0.2         # 秘匿（X）の県の合計が全国の20%以下の品目だけで順位を付ける
Y = 2024
x = C[(C.year == Y) & (C.total_mil_yen >= MIN)].copy()
rank = x[x.secret_share <= MAXSEC].sort_values("top1_low", ascending=False)
rank.to_csv(RES / "a128_rank_2024.csv", index=False)

# --- 1. 上位の品目
t = rank.head(20).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 8))
lab = [f"{i if len(i) <= 22 else i[:21] + '…'}（{p}）" for i, p in zip(t.item, t.top_pref)]
ax.barh(lab, t.top1_low * 100, color=ORANGE, height=0.65)
for i, v in enumerate(t.top1_low):
    ax.text(v * 100 + 0.8, i, f"{v*100:.0f}%", va="center", fontsize=8)
ax.set_xlim(0, 108); ax.tick_params(axis="y", labelsize=8.5)
ax.set_xlabel("出荷金額で最も多い都道府県のシェア（%）")
ax.set_title(f"1つの県に集中している製造品（{Y}年、全国100億円以上）", loc="left")
fig.text(0, -0.03, "秘匿（X）の県の合計が全国の20%以下の品目。シェアは公表された値で計算。" + "\n" + SOURCE, fontsize=7, color=GRAY)
fig.savefig(FIG / "a128_top.png"); plt.close(fig)

# --- 2. 分布（全品目、秘匿の幅つき）
bins = np.arange(0, 1.05, 0.05)
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.hist(x.top1_low, bins=bins, color=BLUE, alpha=0.85, label="下限（公表された値だけ）")
ax.hist(x.top1_high, bins=bins, histtype="step", color=ORANGE, lw=2, label="上限（秘匿分が1県にまとまる場合）")
ax.axvline(0.5, color=INK, lw=0.8, ls="--")
ax.set_xlabel("最も多い都道府県のシェア"); ax.set_ylabel("品目の数")
ax.set_title(f"上位1県のシェアの分布（{Y}年、全国100億円以上の{len(x):,}品目）", loc="left")
ax.legend(frameon=False); fig.text(0, -0.03, SOURCE, fontsize=7, color=GRAY)
fig.savefig(FIG / "a128_dist.png"); plt.close(fig)

# --- 3. 1位の品目が多い県
cnt = pd.DataFrame({"top_items": x.top_pref.value_counts(),
                    "top_items_share50": x[x.top1_low >= 0.5].top_pref.value_counts()}).fillna(0).astype(int)
cnt = cnt.sort_values("top_items", ascending=False)
cnt.to_csv(RES / "a128_pref_top_counts_2024.csv")
c = cnt.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(7.5, 5.5))
ax.barh(c.index, c.top_items, color=LIGHT, label="出荷金額が全国1位の品目数")
ax.barh(c.index, c.top_items_share50, color=ORANGE, label="うち、その県だけで全国の50%以上")
for i, (a, b) in enumerate(zip(c.top_items, c.top_items_share50)):
    ax.text(a + 2, i, f"{a}（{b}）", va="center", fontsize=8)
ax.set_title(f"出荷金額が全国1位の品目の数（{Y}年、全国100億円以上）", loc="left")
ax.legend(frameon=False, loc="lower right"); fig.text(0, -0.03, SOURCE, fontsize=7, color=GRAY)
fig.savefig(FIG / "a128_pref.png"); plt.close(fig)

# --- 2021年との比較
a = C[C.year == 2024].set_index("item_code"); b = C[C.year == 2021].set_index("item_code")
j = a.join(b, rsuffix="_2021", how="inner")
j = j[(j.total_mil_yen >= MIN) & (j.total_mil_yen_2021 >= MIN)]
cmp = {"common_items": len(j), "same_top_pref": (j.top_pref == j.top_pref_2021).mean(),
       "corr_top1_low": j.top1_low.corr(j.top1_low_2021), "median_top1_low_2024": j.top1_low.median(),
       "median_top1_low_2021": j.top1_low_2021.median()}
pd.Series(cmp).to_csv(RES / "a128_compare_2021.csv")
summ = {"items_100oku": len(x), "ranked_items": len(rank), "share50_low": int((x.top1_low >= 0.5).sum()),
        "share50_high": int((x.top1_high >= 0.5).sum()), "median_top1_low": x.top1_low.median(),
        "median_hhi_low": x.hhi_low.median(), "hhi_low_ge_2500": int((x.hhi_low >= 2500).sum()),
        "hhi_high_ge_2500": int((x.hhi_high >= 2500).sum()), "items_with_secret": int((x.n_secret > 0).sum()),
        "median_secret_share": x.secret_share.median()}
pd.Series(summ).to_csv(RES / "a128_summary_2024.csv")
print(summ); print(cmp)
print(rank.head(20)[["item", "total_mil_yen", "top_pref", "top1_low", "top1_high", "n_pref", "n_secret"]].round(3).to_string())
print(cnt.head(10).to_string())
