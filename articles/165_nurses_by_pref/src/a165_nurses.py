"""A165 看護師は、人口あたりでどの県に多いか：都道府県ランキングとタイル地図"""
from common import *
from matplotlib.colors import Normalize
from matplotlib import cm

d = load("nurses_by_pref_2024.csv")
nat = d[d.pref == "全国"].iloc[0]
d = d[d.pref != "全国"].copy()
for k in ["nurse", "assoc_nurse", "nurse_fte", "assoc_nurse_fte", "phn", "midwife"]:
    d[k + "_per100k"] = d[k] / d["population"] * 1e5
d["both_per100k"] = d["nurse_per100k"] + d["assoc_nurse_per100k"]
d["assoc_share"] = d["assoc_nurse"] / (d["nurse"] + d["assoc_nurse"]) * 100
d["rank_nurse"] = d["nurse_per100k"].rank(ascending=False).astype(int)
d["rank_both"] = d["both_per100k"].rank(ascending=False).astype(int)
out = d[["pref", "nurse_per100k", "assoc_nurse_per100k", "both_per100k", "assoc_share", "nurse_fte_per100k", "phn_per100k", "midwife_per100k", "rank_nurse", "rank_both"]].round(1)
out.sort_values("rank_nurse").to_csv(RES / "a165_pref_per100k.csv", index=False, encoding="utf-8-sig")
nat_n = nat["nurse"] / nat["population"] * 1e5
nat_a = nat["assoc_nurse"] / nat["population"] * 1e5
corr = np.corrcoef(d["nurse_per100k"], d["assoc_nurse_per100k"])[0, 1]
west = d["pref"].isin(["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄", "徳島", "香川", "愛媛", "高知", "鳥取", "島根", "岡山", "広島", "山口"])
t = pd.read_csv(DATA / "nurses_national_trend.csv")
s = out.sort_values("rank_nurse")
with open(RES / "a165_summary.txt", "w", encoding="utf-8") as f:
    f.write(f"全国 看護師 {nat_n:.1f}、准看護師 {nat_a:.1f}（人口10万対）\n")
    f.write("看護師 上位5:\n" + s.head(5).to_string(index=False) + "\n下位5:\n" + s.tail(5).to_string(index=False) + "\n")
    f.write(f"最大/最小 = {s.nurse_per100k.max()/s.nurse_per100k.min():.2f}倍\n")
    f.write(f"看護師+准看護師 最大/最小 = {out.both_per100k.max()/out.both_per100k.min():.2f}倍、上位: {out.sort_values('rank_both').pref.head(5).tolist()}\n")
    f.write(f"看護師と准看護師（10万対）の相関 r={corr:.2f}\n")
    f.write(f"中国・四国・九州・沖縄17県の平均 看護師 {d[west].nurse_per100k.mean():.0f}／その他30都道府県 {d[~west].nurse_per100k.mean():.0f}\n")
    f.write(f"准看護師の割合: 全国 {nat['assoc_nurse']/(nat['nurse']+nat['assoc_nurse'])*100:.1f}%、最大 {out.loc[out.assoc_share.idxmax(),'pref']} {out.assoc_share.max():.1f}%、最小 {out.loc[out.assoc_share.idxmin(),'pref']} {out.assoc_share.min():.1f}%\n")
    f.write("全国推移:\n" + t.to_string(index=False) + "\n")

# 図1 ランキング（看護師、准看護師を重ねる）
s2 = d.sort_values("nurse_per100k")
fig, ax = plt.subplots(figsize=(8.2, 10.5))
y = np.arange(len(s2))
ax.barh(y, s2["nurse_per100k"], color=BLUE, height=0.75, label="看護師")
ax.barh(y, s2["assoc_nurse_per100k"], left=s2["nurse_per100k"], color=LIGHT, height=0.75, label="准看護師")
ax.set_yticks(y); ax.set_yticklabels(s2["pref"], fontsize=8.5)
for yi, v in zip(y, s2["nurse_per100k"]):
    ax.text(v - 15, yi, f"{v:.0f}", va="center", ha="right", fontsize=7, color="white")
ax.axvline(nat_n, color=ORANGE, lw=1.2, ls="--"); ax.text(nat_n + 10, -1.6, f"全国の看護師 {nat_n:.0f}", color=ORANGE, fontsize=8.5)
ax.set_xlabel("人口10万人当たりの就業者数（人）"); ax.set_ylim(-2.2, len(s2) - 0.3)
ax.set_title("人口10万人当たりの就業看護師・准看護師（2024年末）")
ax.legend(loc="lower right", frameon=False)
save(fig, "a165_rank.png")

# 図2 タイル地図
pos = {"北海道": (12, 0), "青森": (12, 2), "秋田": (11, 3), "岩手": (12, 3), "石川": (8, 4), "富山": (9, 4), "新潟": (10, 4), "山形": (11, 4), "宮城": (12, 4),
       "福井": (8, 5), "岐阜": (9, 5), "長野": (10, 5), "群馬": (11, 5), "福島": (12, 5), "島根": (4, 6), "鳥取": (5, 6), "兵庫": (6, 6), "京都": (7, 6), "滋賀": (8, 6),
       "愛知": (9, 6), "山梨": (10, 6), "埼玉": (11, 6), "栃木": (12, 6), "福岡": (2, 7), "山口": (3, 7), "広島": (4, 7), "岡山": (5, 7), "大阪": (6, 7), "奈良": (7, 7),
       "三重": (8, 7), "静岡": (10, 7), "東京": (11, 7), "茨城": (12, 7), "長崎": (0, 8), "佐賀": (1, 8), "大分": (2, 8), "愛媛": (4, 8), "香川": (5, 8), "和歌山": (7, 8),
       "神奈川": (11, 8), "千葉": (12, 8), "熊本": (1, 9), "宮崎": (2, 9), "高知": (4, 9), "徳島": (5, 9), "鹿児島": (1, 10), "沖縄": (0, 11)}
assert len(pos) == 47 and set(pos) == set(d.pref)
norm = Normalize(800, 1800); cmap = plt.get_cmap("Blues")
fig, ax = plt.subplots(figsize=(8.6, 7.6))
for _, r in d.iterrows():
    cx, cy = pos[r.pref]; v = r.nurse_per100k; col = cmap(norm(v))
    ax.add_patch(plt.Rectangle((cx, -cy), 0.94, 0.94, color=col))
    tc = "white" if norm(v) > 0.55 else INK
    ax.text(cx + 0.47, -cy + 0.6, r.pref, ha="center", va="center", fontsize=8, color=tc)
    ax.text(cx + 0.47, -cy + 0.28, f"{v:.0f}", ha="center", va="center", fontsize=8, color=tc)
ax.set_xlim(-0.2, 13.2); ax.set_ylim(-11.3, 1.1); ax.set_aspect("equal"); ax.axis("off")
sm = cm.ScalarMappable(norm=norm, cmap=cmap)
cb = fig.colorbar(sm, ax=ax, shrink=0.45, location="right", pad=0.01); cb.set_label("看護師（人口10万対）")
ax.set_title("人口10万人当たりの就業看護師（2024年末、タイル地図）")
save(fig, "a165_map.png")

# 図3 看護師と准看護師
fig, ax = plt.subplots(figsize=(8.6, 5.4))
ax.scatter(d.loc[~west, "nurse_per100k"], d.loc[~west, "assoc_nurse_per100k"], color=GRAY, s=30, label="北海道・本州（中国地方を除く）")
ax.scatter(d.loc[west, "nurse_per100k"], d.loc[west, "assoc_nurse_per100k"], color=ORANGE, s=34, label="中国・四国・九州・沖縄")
lab = set(s.head(6).pref) | set(s.tail(4).pref) | set(out.sort_values("assoc_share").pref.tail(3)) | {"東京", "大阪", "北海道"}
for _, r in d[d.pref.isin(lab)].iterrows():
    ax.annotate(r.pref, (r.nurse_per100k, r.assoc_nurse_per100k), textcoords="offset points", xytext=(-26, 4) if r.pref == "熊本" else (4, 3), fontsize=8.5)
ax.axvline(nat_n, color=GRAY, lw=0.8, ls=":"); ax.axhline(nat_a, color=GRAY, lw=0.8, ls=":")
ax.set_xlabel("看護師（人口10万対）"); ax.set_ylabel("准看護師（人口10万対）")
ax.set_title(f"看護師と准看護師の多さ（都道府県、2024年末、相関 r={corr:.2f}）")
ax.legend(loc="upper left", frameon=False)
save(fig, "a165_scatter.png")
print(open(RES / "a165_summary.txt", encoding="utf-8").read())
