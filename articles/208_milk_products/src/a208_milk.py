"""A208 飲む牛乳の生産は減り、何が増えたのか：牛乳等5品目の構成比と、生乳の用途別処理量の推移"""
from common import *

d = load().set_index("year")
P = list(LABEL)
tot = d[P].sum(axis=1)
share = d[P].div(tot, axis=0) * 100
use = d[["shori_gyunyu", "shori_nyuseihin", "shori_sonota"]]
use_sh = use.div(use.sum(axis=1), axis=0) * 100

out = []
def p(s): out.append(s); print(s)
for y in [1985, 1994, 2000, 2013, 2020, 2024]:
    p(f"{y}: 合計{tot[y]/1e4:.1f}万kl " + " ".join(f"{LABEL[c]}{d.loc[y,c]/1e4:.1f}万kl({share.loc[y,c]:.1f}%)" for c in P))
for c in P:
    s = d[c]; p(f"{LABEL[c]}: 最大{s.idxmax()}年{s.max()/1e4:.1f}万kl 2024年{s[2024]/1e4:.1f}万kl 最大比{(s[2024]/s.max()-1)*100:+.1f}% 1985比{(s[2024]/s[1985]-1)*100:+.1f}%")
p(f"5品目合計 最大{tot.idxmax()}年{tot.max()/1e4:.1f}万kl 2024年{tot[2024]/1e4:.1f}万kl ({(tot[2024]/tot.max()-1)*100:+.1f}%)")
fermented_drink = share.hakkonyu + share.nyuinryo
p(f"はっ酵乳+乳飲料の割合 1985 {fermented_drink[1985]:.1f}% 2024 {fermented_drink[2024]:.1f}%")
p(f"はっ酵乳/牛乳 1985 {d.hakkonyu[1985]/d.gyunyu[1985]*100:.1f}% 2024 {d.hakkonyu[2024]/d.gyunyu[2024]*100:.1f}%")
for y in [1985, 1996, 2008, 2009, 2010, 2024]:
    p(f"用途 {y}: 牛乳等向け{use.loc[y,'shori_gyunyu']/1e4:.1f}万t({use_sh.loc[y,'shori_gyunyu']:.1f}%) 乳製品向け{use.loc[y,'shori_nyuseihin']/1e4:.1f}万t({use_sh.loc[y,'shori_nyuseihin']:.1f}%) 生乳計{d.seinyu[y]/1e4:.1f}万t")
p(f"生乳生産 最大{d.seinyu.idxmax()}年{d.seinyu.max()/1e4:.1f}万t 2024 {d.seinyu[2024]/1e4:.1f}万t ({(d.seinyu[2024]/d.seinyu.max()-1)*100:+.1f}%)")
p(f"乳製品向けが牛乳等向けを上回る年: なし" if (use.shori_nyuseihin < use.shori_gyunyu).all() else "")
# 10年ごとの変化
for a, b in [(1985, 1995), (1995, 2005), (2005, 2015), (2015, 2024)]:
    p(f"{a}->{b}: " + " ".join(f"{LABEL[c]}{(d.loc[b,c]-d.loc[a,c])/1e4:+.1f}" for c in P) + " 万kl")
(RES / "summary.txt").write_text("\n".join(out), encoding="utf-8")
share.round(2).to_csv(RES / "product_share_pct.csv")
use_sh.round(2).rename(columns={"shori_gyunyu": "牛乳等向け", "shori_nyuseihin": "乳製品向け", "shori_sonota": "その他"}).to_csv(RES / "use_share_pct.csv")

C = {"gyunyu": BLUE, "kakounyu_seibun": LIGHT, "nyuinryo": ORANGE, "hakkonyu": GREEN, "nyusankin": PURPLE}
fig, ax = plt.subplots(figsize=(8.5, 4.8))
for c in P:
    ax.plot(d.index, d[c] / 1e4, color=C[c], lw=2.2 if c in ("gyunyu", "hakkonyu") else 1.6, label=LABEL[c])
ax.set_ylabel("生産量（万kl）"); ax.set_ylim(0); ax.legend(frameon=False, fontsize=9, ncol=2)
ax.set_title("牛乳は1994年の434万klから307万klへ。はっ酵乳は5.5倍に")
save(fig, "a208_products.png")

fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.stackplot(d.index, *[share[c] for c in P], colors=[C[c] for c in P], labels=[LABEL[c] for c in P], alpha=.9)
ax.set_ylim(0, 100); ax.set_xlim(1985, 2024); ax.set_ylabel("5品目合計に占める割合（%）")
ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(1.0, 1))
ax.set_title(f"牛乳の割合は{share.gyunyu[1985]:.0f}%から{share.gyunyu[2024]:.0f}%に")
save(fig, "a208_share.png")

fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.plot(d.index, d.seinyu / 1e4, color=INK, lw=2, label="生乳生産量")
ax.plot(d.index, use.shori_gyunyu / 1e4, color=BLUE, lw=2, label="牛乳等向け")
ax.plot(d.index, use.shori_nyuseihin / 1e4, color=ORANGE, lw=2, label="乳製品向け（バター・脱脂粉乳・チーズなど）")
ax.set_ylim(0); ax.set_ylabel("万t"); ax.legend(frameon=False, fontsize=9)
ax.set_title("生乳の行き先：牛乳等向けが減り、乳製品向けとの差が縮んだ")
save(fig, "a208_use.png")
