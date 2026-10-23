"""よく出される飲み薬は、性別と年齢でどう違うか（第10回NDBオープンデータ：内服・外来（院外）、錠・カプセル）"""
from common import *

c = load("class_by_sex_age.csv")  # 単位：千錠（錠・カプセルのみ）
top = load("top100_tablets.csv")
B = ["0_14", "15_39", "40_64", "65_74", "75p"]
BL = ["0〜14歳", "15〜39歳", "40〜64歳", "65〜74歳", "75歳以上"]
M = ["m" + b for b in B]; F = ["f" + b for b in B]
c["name"] = c["class"].str.split(" ", n=1).str[1].str.replace("（ビタミンＢ１剤を除く。）", "").str.replace("（ビタミンＡ・Ｄ混合製剤を除く。）", "").str.replace("（抗ホルモン剤を含む。）", "")
c["male"] = c[M].sum(axis=1); c["female"] = c[F].sum(axis=1)
c["female_share"] = c.female / (c.male + c.female)
for b in B:
    c["all" + b] = c["m" + b] + c["f" + b]
A = ["all" + b for b in B]
c["share75"] = c.all75p / c[A].sum(axis=1)
tot = c[M + F].sum()
L = [f"錠・カプセルの合計：{tot.sum()/1e6:.1f}億錠（男 {tot[M].sum()/1e6:.1f}、女 {tot[F].sum()/1e6:.1f}、女性の割合 {tot[F].sum()/tot.sum():.1%}）",
     "年齢別の割合：" + "、".join(f"{l} {(tot['m'+b]+tot['f'+b])/tot.sum():.1%}" for b, l in zip(B, BL)),
     f"65歳以上の割合：{(tot[['m65_74','m75p','f65_74','f75p']].sum())/tot.sum():.1%}"]
L.append("薬効分類 上位15（千錠→億錠）:\n" + "\n".join(f"  {r['class']} {r.total/1e5:.1f}億錠 女性 {r.female_share:.0%} 75歳以上 {r.share75:.0%}" for _, r in c.head(15).iterrows()))
for s, cols in [("男", M), ("女", F)]:
    for col, l in zip(cols, BL):
        sh = (c.set_index("name")[col] / c[col].sum()).sort_values(ascending=False).head(5)
        L.append(f"{s}{l} 上位5: " + "、".join(f"{k} {v:.1%}" for k, v in sh.items()))
big = c[c.total >= 300000].sort_values("female_share")
L.append("女性の割合（30万千錠以上の分類）低い順:\n" + "\n".join(f"  {r['name']} {r.female_share:.1%}" for _, r in big.iterrows()))
top["name"] = top.drug.str.replace(r"[錠カプセル].*$", "", regex=True)
L.append(f"上位100品目の合計 {top.total_k.sum()/1e5:.1f}億錠（全体の {top.total_k.sum()/tot.sum():.1%}）")
L.append("上位10品目: " + "、".join(f"{r.drug} {r.total_k/1e5:.1f}億" for r in top.head(10).itertuples()))
cl = top.groupby("class").total_k.agg(["count", "sum"]).sort_values("sum", ascending=False)
names = c.assign(code=c["class"].str[:3].astype(int)).set_index("code").name
L.append("上位100品目の薬効分類別:\n" + "\n".join(f"  {k} {names.get(k,'')} {r['count']}品目 {r['sum']/1e5:.1f}億錠" for k, r in cl.head(10).iterrows()))
c.to_csv(RES / "a157_class_metrics.csv", index=False, encoding="utf-8")
(RES / "a157_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：上位15分類、年齢別の積み上げ（億錠）
t = c.head(15)[::-1]
cols = ["#d8e6f6", "#a9c9ef", "#6ea6e3", "#2a78d6", "#174a8a"]
fig, ax = plt.subplots(figsize=(9.5, 6.2))
y = np.arange(len(t)); left = np.zeros(len(t))
for a, l, col in zip(A, BL, cols):
    ax.barh(y, t[a] / 1e5, left=left, color=col, height=0.65, label=l); left += t[a].values / 1e5
for yy, v in zip(y, left):
    ax.text(v + 0.5, yy, f"{v:.0f}", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(t.name, fontsize=9.5)
ax.set_xlabel("1年間の数量（億錠、錠・カプセル、外来の院外処方）")
ax.legend(frameon=False, loc="lower right", fontsize=9); ax.set_title("よく出される飲み薬の種類（薬効分類、上位15）と年齢")
save(fig, "a157_classes.png")

# 図2：性・年齢ごとの割合（上位12分類）
h = c.head(12)
mat = np.array([[h[col].iloc[i] / c[col].sum() * 100 for col in M + F] for i in range(len(h))])
fig, ax = plt.subplots(figsize=(10, 6.2))
im = ax.imshow(mat, cmap="Blues", aspect="auto", vmin=0, vmax=mat.max())
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax.text(j, i, f"{mat[i,j]:.0f}", ha="center", va="center", fontsize=8.5, color="white" if mat[i, j] > mat.max() * 0.55 else INK)
ax.set_xticks(range(10)); ax.set_xticklabels([f"男\n{l}" for l in BL] + [f"女\n{l}" for l in BL], fontsize=8.5)
ax.set_yticks(range(len(h))); ax.set_yticklabels(h.name, fontsize=9.5)
ax.axvline(4.5, color="white", lw=3)
ax.set_title("性・年齢ごとに、錠・カプセル全体のうち各分類が占める割合（%）")
for s in ax.spines.values(): s.set_visible(False)
save(fig, "a157_heatmap.png")

# 図3：女性の割合（数量上位25分類）
big = c.head(25).sort_values("female_share")
fig, ax = plt.subplots(figsize=(9.5, 6.8))
y = np.arange(len(big))
colr = [ORANGE if v >= 0.6 else (BLUE if v <= 0.4 else GRAY) for v in big.female_share]
ax.barh(y, big.female_share * 100, color=colr, height=0.65)
for yy, v in zip(y, big.female_share):
    ax.text(v * 100 + 0.8, yy, f"{v*100:.0f}%", va="center", fontsize=8.5)
ax.axvline(tot[F].sum() / tot.sum() * 100, color=INK, lw=1, ls="--")
ax.text(tot[F].sum() / tot.sum() * 100 + 0.5, len(big) - 0.3, f"全体 {tot[F].sum()/tot.sum()*100:.0f}%", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(big.name, fontsize=9); ax.set_xlim(0, 105)
ax.set_xlabel("数量に占める女性の割合（%）"); ax.set_title("飲み薬の分類ごとの、女性の割合（数量の多い25分類）")
save(fig, "a157_female.png")
