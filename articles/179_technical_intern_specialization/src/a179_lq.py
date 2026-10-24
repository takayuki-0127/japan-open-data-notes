"""179 在留資格別に見ると、どの県が技能実習に頼っているか（特化係数）"""
from common import *

d = load("foreign_workers_by_status_2025.csv").set_index("pref")
nat = d.loc["全国"]; p = d.drop("全国")
cats = {"専門的・技術的分野": "professional", "技能実習": "technical_intern", "身分に基づく": "status_based", "資格外活動": "permission_outside", "特定活動": "designated_activities"}
share = pd.DataFrame({k: p[v] / p.total * 100 for k, v in cats.items()})
share["特定技能"] = p.specified_skilled / p.total * 100
share["技術・人文知識・国際業務"] = p.engineer_humanities / p.total * 100
natshare = {k: nat[v] / nat.total * 100 for k, v in cats.items()}
natshare["特定技能"] = nat.specified_skilled / nat.total * 100
natshare["技術・人文知識・国際業務"] = nat.engineer_humanities / nat.total * 100
lq = share / pd.Series(natshare)
lq.columns = ["LQ_" + c for c in lq.columns]
out = pd.concat([p.total, share.round(2), lq.round(3)], axis=1)
out.to_csv(RES / "a179_share_lq.csv", encoding="utf-8-sig")

R = []
R.append("全国 share: " + ", ".join(f"{k}{v:.1f}%" for k, v in natshare.items()) + f" total {nat.total}")
t = lq["LQ_技能実習"].sort_values(ascending=False)
R.append("技能実習LQ top15: " + ", ".join(f"{k}{v:.2f}({share.loc[k,'技能実習']:.1f}%)" for k, v in t.head(15).items()))
R.append("技能実習LQ bottom8: " + ", ".join(f"{k}{v:.2f}({share.loc[k,'技能実習']:.1f}%)" for k, v in t.tail(8).items()))
R.append(f"LQ>1.5 count {(t>1.5).sum()}, LQ>2 count {(t>2).sum()}, LQ>1 count {(t>1).sum()}")
R.append(f"東京 技能実習 {p.loc['東京','technical_intern']} share {share.loc['東京','技能実習']:.1f}% of national intern {p.loc['東京','technical_intern']/nat.technical_intern*100:.1f}%; 東京 total share {p.loc['東京','total']/nat.total*100:.1f}%")
top_int = p.technical_intern.sort_values(ascending=False).head(6)
R.append("技能実習 人数 top: " + ", ".join(f"{k}{v}" for k, v in top_int.items()))
hi = t[t > 1.5].index
R.append(f"LQ>1.5 の県の技能実習 合計 {p.loc[hi,'technical_intern'].sum()} ({p.loc[hi,'technical_intern'].sum()/nat.technical_intern*100:.1f}% of national), 外国人労働者 {p.loc[hi,'total'].sum()/nat.total*100:.1f}%")
R.append(f"corr LQ技能実習 vs LQ特定技能 {lq['LQ_技能実習'].corr(lq['LQ_特定技能']):.3f}; vs log total {lq['LQ_技能実習'].corr(np.log(p.total)):.3f}; vs 身分 {lq['LQ_技能実習'].corr(lq['LQ_身分に基づく']):.3f}")
s2 = lq["LQ_特定技能"].sort_values(ascending=False)
R.append("特定技能LQ top10: " + ", ".join(f"{k}{v:.2f}({share.loc[k,'特定技能']:.1f}%)" for k, v in s2.head(10).items()))
both = share["技能実習"] + share["特定技能"]
R.append("技能実習+特定技能 share top8: " + ", ".join(f"{k}{v:.1f}%" for k, v in both.sort_values(ascending=False).head(8).items()) + f" | 全国 {natshare['技能実習']+natshare['特定技能']:.1f}% | 東京 {both['東京']:.1f}%")
for k in ["身分に基づく", "専門的・技術的分野", "資格外活動"]:
    s = lq["LQ_" + k].sort_values(ascending=False)
    R.append(f"{k}LQ top5: " + ", ".join(f"{a}{b:.2f}({share.loc[a,k]:.1f}%)" for a, b in s.head(5).items()))
# 地方別
reg = {"北海道・東北": ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島"], "四国": ["徳島", "香川", "愛媛", "高知"], "九州・沖縄": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"], "南関東": ["埼玉", "千葉", "東京", "神奈川"], "東海": ["岐阜", "静岡", "愛知", "三重"]}
for k, v in reg.items():
    R.append(f"{k}: 技能実習 share {p.loc[v,'technical_intern'].sum()/p.loc[v,'total'].sum()*100:.1f}%")
(RES / "a179_summary.txt").write_text("\n".join(R), encoding="utf-8"); print("\n".join(R))

# 図1 技能実習の特化係数
s = lq["LQ_技能実習"].sort_values()
fig, ax = plt.subplots(figsize=(7.5, 10))
ax.barh(s.index, s.values, color=[ORANGE if v >= 1.5 else (LIGHT if v >= 1 else GRAY) for v in s.values])
ax.axvline(1, color=INK, lw=0.8); ax.text(1.02, -0.9, "全国平均＝1", fontsize=8.5)
for i, (k, v) in enumerate(s.items()):
    ax.text(v + 0.03, i, f"{share.loc[k,'技能実習']:.0f}%", va="center", fontsize=7.5, color=GRAY)
ax.tick_params(axis="y", labelsize=8.5); ax.set_xlabel("技能実習の特化係数（数字は外国人労働者に占める技能実習の割合）")
ax.set_title("技能実習の特化係数（2025年10月末）", loc="left")
save(fig, "a179_lq_intern.png")

# 図2 在留資格の構成：特化係数上位5県・全国・東京・愛知など
sel = list(t.head(6).index) + ["全国", "愛知", "大阪", "東京"]
comp = pd.DataFrame({k: (d.loc[sel, v] / d.loc[sel, "total"] * 100) for k, v in cats.items()})
comp["その他"] = 100 - comp.sum(axis=1)
cols = {"技能実習": ORANGE, "専門的・技術的分野": BLUE, "身分に基づく": GREEN, "資格外活動": PURPLE, "特定活動": GRAY, "その他": "#dddddd"}
order = ["技能実習", "専門的・技術的分野", "身分に基づく", "資格外活動", "特定活動"]
fig, ax = plt.subplots(figsize=(8, 5))
left = np.zeros(len(sel))
for k in order:
    ax.barh(sel[::-1], comp.loc[sel[::-1], k], left=left, color=cols[k], label=k)
    for i, v in enumerate(comp.loc[sel[::-1], k]):
        if v >= 7: ax.text(left[i] + v / 2, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white")
    left += comp.loc[sel[::-1], k].values
ax.set_xlim(0, 100); ax.set_xlabel("外国人労働者に占める割合（%）")
ax.legend(ncol=5, frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0))
ax.set_title("在留資格の内訳：技能実習の割合が高い県と大都市圏", loc="left", pad=24)
save(fig, "a179_composition.png")

# 図3 技能実習と特定技能の特化係数
fig, ax = plt.subplots(figsize=(7.5, 6))
sz = p.total / p.total.max() * 600 + 15
ax.scatter(lq["LQ_技能実習"], lq["LQ_特定技能"], s=sz, color=BLUE, alpha=0.55, edgecolor="white")
for k in lq.index:
    if k in ["宮崎", "鹿児島", "香川", "長崎", "青森", "北海道", "熊本", "富山"] or k in ["東京", "大阪", "愛知", "静岡", "群馬"]:
        ax.annotate(k, (lq.loc[k, "LQ_技能実習"], lq.loc[k, "LQ_特定技能"]), fontsize=8.5, xytext=(4, 3), textcoords="offset points")
ax.axvline(1, color=GRAY, lw=0.7); ax.axhline(1, color=GRAY, lw=0.7)
ax.set_xlabel("技能実習の特化係数"); ax.set_ylabel("特定技能の特化係数")
ax.set_title("技能実習が多い県は、特定技能も多い（円の大きさ＝外国人労働者数）", loc="left")
save(fig, "a179_intern_vs_ssw.png")
