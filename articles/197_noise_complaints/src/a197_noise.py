"""騒音の苦情の発生源は、工場から何に変わったか（公害苦情調査、2004〜2024年度）"""
from common import *

d, g = load()
sh = g.drop(columns="合計").div(g["合計"], axis=0)
g.to_csv(RES / "a197_by_group.csv", encoding="utf-8")
sh.round(4).to_csv(RES / "a197_share.csv", encoding="utf-8")
L = [f"騒音の苦情 合計: 2004 {g.loc[2004,'合計']:,} → 2019 {g.loc[2019,'合計']:,} → 2020 {g.loc[2020,'合計']:,} → 2024 {g.loc[2024,'合計']:,}（2004比 {g.loc[2024,'合計']/g.loc[2004,'合計']-1:+.1%}）"]
for k in sh.columns:
    L.append(f"{k}: {g.loc[2004,k]:,}件({sh.loc[2004,k]:.1%}) → {g.loc[2024,k]:,}件({sh.loc[2024,k]:.1%})  増減 {g.loc[2024,k]/g.loc[2004,k]-1:+.1%}")
L.append(f"製造業の最大 {g['製造業'].idxmax()} {g['製造業'].max():,}、建設業の最大 {g['建設業'].idxmax()} {g['建設業'].max():,}")
L.append(f"建設業÷製造業: 2004 {g.loc[2004,'建設業']/g.loc[2004,'製造業']:.1f}倍 → 2024 {g.loc[2024,'建設業']/g.loc[2024,'製造業']:.1f}倍")
L.append(f"2019→2020 増加 {g.loc[2020,'合計']-g.loc[2019,'合計']:+,}（建設業 {g.loc[2020,'建設業']-g.loc[2019,'建設業']:+,}、飲食店・宿泊業 {g.loc[2020,'飲食店・宿泊業']-g.loc[2019,'飲食店・宿泊業']:+,}、個人 {g.loc[2020,'個人']-g.loc[2019,'個人']:+,}）")
c = pd.read_csv(DATA / "noise_by_cause.csv").set_index("year")
lab = {"construction_work": "工事・建設作業", "industrial_machinery": "産業用機械の作動", "restaurant": "飲食店の営業", "karaoke": "カラオケ",
       "home_appliance": "家庭生活（機器）", "home_pet": "家庭生活（ペット）", "home_other": "家庭生活（その他）", "car": "自動車の運行",
       "aircraft": "航空機の運航", "rail": "鉄道の運行", "other": "その他", "unknown": "不明"}
cc = c[list(lab)].rename(columns=lab)
cc["その他の原因"] = c.drop(columns=["total"] + list(lab)).sum(axis=1)
home = cc[["家庭生活（機器）", "家庭生活（ペット）", "家庭生活（その他）"]].sum(axis=1)
for y in [2022, 2024]:
    t = c.loc[y, "total"]
    L.append(f"{y} 主な発生原因: " + "、".join(f"{k} {v:,}({v/t:.1%})" for k, v in cc.loc[y].sort_values(ascending=False).head(7).items()) + f"／家庭生活 計 {home[y]:,}({home[y]/t:.1%})")
(RES / "a197_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

COL = {"建設業": BLUE, "製造業": ORANGE, "飲食店・宿泊業": GREEN, "卸売・小売業": PURPLE, "運輸業": "#c9a227",
       "その他の会社・事業所": GRAY, "個人": INK, "その他・不明（会社・事業所以外）": LIGHT}
# 図1：発生源別の件数の推移
fig, ax = plt.subplots(figsize=(9.5, 5))
for k in ["建設業", "製造業", "個人", "飲食店・宿泊業", "卸売・小売業", "運輸業"]:
    ax.plot(g.index, g[k], color=COL[k], lw=2.2 if k in ("建設業", "製造業") else 1.5, marker="o", ms=3)
    ax.text(2024.3, g.loc[2024, k], f"{k} {g.loc[2024,k]:,}", color=COL[k], va="center", fontsize=9)
ax.set_xlim(2003.5, 2028.5); ax.set_xticks(range(2004, 2025, 4)); ax.set_ylim(0)
ax.set_ylabel("騒音の苦情の受付件数（件）"); ax.set_xlabel("年度")
ax.set_title("騒音の苦情の発生源（産業別、主なもの）")
save(fig, "a197_trend.png")

# 図2：構成比 2004 vs 2024
fig, ax = plt.subplots(figsize=(9, 5))
ks = list(sh.columns)[::-1]; ys = np.arange(len(ks))
ax.barh(ys + 0.2, sh.loc[2004, ks] * 100, height=0.38, color=LIGHT, label="2004年度")
ax.barh(ys - 0.2, sh.loc[2024, ks] * 100, height=0.38, color=BLUE, label="2024年度")
for y, k in zip(ys, ks):
    ax.text(sh.loc[2004, k] * 100 + 0.4, y + 0.2, f"{sh.loc[2004,k]*100:.1f}", va="center", fontsize=8.5, color=GRAY)
    ax.text(sh.loc[2024, k] * 100 + 0.4, y - 0.2, f"{sh.loc[2024,k]*100:.1f}", va="center", fontsize=8.5)
ax.set_yticks(ys); ax.set_yticklabels(ks); ax.set_xlabel("騒音の苦情に占める割合（%）")
ax.legend(frameon=False, loc="lower right"); ax.set_title("騒音の苦情の発生源の割合（2004年度と2024年度）")
save(fig, "a197_share.png")

# 図3：主な発生原因（2024、2022を点で）
o = cc.loc[2024].sort_values()
fig, ax = plt.subplots(figsize=(9, 5.5))
ys = np.arange(len(o))
ax.barh(ys, o.values, color=[BLUE if k == "工事・建設作業" else (ORANGE if k == "産業用機械の作動" else (GREEN if k.startswith("家庭") else GRAY)) for k in o.index], height=0.7, label="2024年度")
ax.scatter(cc.loc[2022, o.index], ys, color=INK, s=14, zorder=3, label="2022年度")
for y, k, v in zip(ys, o.index, o.values):
    ax.text(max(v, cc.loc[2022, k]) + 120, y, f"{v:,}", va="center", fontsize=8.5)
ax.set_yticks(ys); ax.set_yticklabels(o.index); ax.set_xlabel("件")
ax.legend(frameon=False, loc="lower right"); ax.set_title("騒音の苦情の主な発生原因（2024年度）")
save(fig, "a197_cause.png")
