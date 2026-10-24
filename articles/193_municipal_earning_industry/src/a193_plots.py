"""A193 市区町村の「稼ぐ力」はどの産業が支えているか（集計済みデータから図と要約）"""
from common import *
ind = load("muni_by_industry.csv"); nat = load("national_industry.csv"); mfg = load("muni_by_mfg_share.csv"); size = load("muni_by_size.csv")
n = int(ind.n_top1.sum())
ind["name"] = ind.ind.map(IND); nat["name"] = nat.ind.map(IND)
t = ind[ind.n_top1 > 0].sort_values("n_top1")
t2 = t[t.n_top1 >= 5]
# fig1: 付加価値1位の産業（規模別積み上げ）
cols = ["top1_w0_5k", "top1_w5k_20k", "top1_w20k_100k", "top1_w100k_plus"]; lab = ["従事者5千人未満", "5千〜2万人", "2万〜10万人", "10万人以上"]
fig, ax = plt.subplots(figsize=(8, 4.8)); left = np.zeros(len(t2))
for c, l, col in zip(cols, lab, [LIGHT, "#7fb0e8", BLUE, INK]):
    ax.barh(t2.name, t2[c], left=left, color=col, label=l); left += t2[c].values
for y, (v, p) in enumerate(zip(t2.n_top1, t2.n_top1 / n * 100)): ax.text(v + 8, y, f"{v}（{p:.0f}%）" if p >= 1 else f"{v}（{p:.1f}%）", va="center", fontsize=9)
ax.set_xlabel("市区町村の数"); ax.set_title(f"純付加価値額が最も大きい産業（{n:,}市区町村）"); ax.legend(frameon=False, fontsize=8.5, loc="lower right"); ax.set_xlim(0, 1080)
save(fig, "a193_top1.png")
# fig2: 特化係数が最も高い産業
q = ind[ind.n_lq_top >= 15].sort_values("n_lq_top")
fig, ax = plt.subplots(figsize=(8, 4.8)); ax.barh(q.ind.map(IND), q.n_lq_top, color=ORANGE)
for y, (v, m) in enumerate(zip(q.n_lq_top, q.med_lq)): ax.text(v + 6, y, f"{v}（中央値 {m:.1f}倍）", va="center", fontsize=9)
ax.set_xlabel("市区町村の数"); ax.set_title("特化係数が最も高い産業（構成比5%以上の産業のうち）"); ax.set_xlim(0, 640)
save(fig, "a193_lq.png")
# fig3: 製造業の構成比と従事者1人当たり純付加価値額
lb = [f"{a}〜{b}%" if b < 100 else f"{a}%以上" for a, b in zip(mfg.mfg_share_lo, mfg.mfg_share_hi)]
fig, ax = plt.subplots(figsize=(8, 4.6)); x = np.arange(len(mfg))
ax.bar(x, mfg.med_va_per_worker, color=BLUE, width=0.6)
ax.errorbar(x, mfg.med_va_per_worker, yerr=[mfg.med_va_per_worker - mfg.q1, mfg.q3 - mfg.med_va_per_worker], fmt="none", ecolor=INK, capsize=4, lw=1)
for i, (v, k) in enumerate(zip(mfg.med_va_per_worker, mfg.n)): ax.text(i, 30, f"{v:.0f}万円\n({k})", ha="center", color="white", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(lb); ax.set_xlabel("純付加価値額に占める製造業の割合（カッコ内は市区町村数）"); ax.set_ylabel("事業従事者1人当たり純付加価値額（万円）")
ax.set_title("製造業の割合と1人当たりの稼ぎ（中央値、ひげは25〜75%）"); ax.set_ylim(0, 620)
save(fig, "a193_mfg.png")
with open(RES / "a193_summary.txt", "w") as f:
    f.write(f"市区町村数 {n}\n純付加価値1位の産業:\n" + t.sort_values("n_top1", ascending=False)[["name", "n_top1", "med_va_per_worker_top1", "med_top1_pct"]].assign(pct=lambda d: (d.n_top1 / n * 100).round(1)).to_string(index=False) + "\n\n")
    f.write("全国の純付加価値の構成比:\n" + nat.sort_values("va_share_pct", ascending=False)[["name", "va_share_pct"]].head(6).to_string(index=False) + "\n\n")
    f.write("特化係数1位:\n" + ind.sort_values("n_lq_top", ascending=False)[["ind", "n_lq_top", "med_lq"]].head(8).assign(name=lambda d: d.ind.map(IND)).to_string(index=False) + "\n\n")
    f.write("規模別:\n" + size.to_string(index=False) + "\n\n製造業割合別:\n" + mfg.to_string(index=False) + "\n")
