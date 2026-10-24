"""営業用と自家用、トラック輸送の割合はどう変わったか（1960〜2025年度）"""
from common import *

d = load("truck_transport_fy.csv")
d["sh_ton"] = d.ton_eigyo / d.ton_total * 100
d["sh_tkm"] = d.tkm_eigyo / d.tkm_total * 100
d["km_e"] = d.tkm_eigyo / d.ton_eigyo * 1000   # 1トンあたり平均輸送距離（km）
d["km_j"] = d.tkm_jika / d.ton_jika * 1000
d.round(2).to_csv(RES / "a186_shares.csv", index=False)
A, B, C = (d[d.basis == k] for k in "ABC")
g = lambda s, y, c: float(s.loc[s.year == y, c].iloc[0])
L = []
for s, y in [(A, 1960), (A, 1970), (A, 1990), (A, 2000), (A, 2009), (B, 2009), (B, 2012), (C, 2015), (C, 2019), (C, 2020), (C, 2025)]:
    r = s[s.year == y].iloc[0]
    L.append(f"{y}({r.basis}) 営業用 重さ{r.sh_ton:.1f}% " + (f"トンキロ{r.sh_tkm:.1f}% 平均距離 営業{r.km_e:.1f}km 自家{r.km_j:.1f}km " if pd.notna(r.sh_tkm) else "")
             + f"営業{r.ton_eigyo/1e5:.1f}億t 自家{r.ton_jika/1e5:.1f}億t")
L.append(f"自家用の最大 {A.loc[A.ton_jika.idxmax(),'year']}年度 {A.ton_jika.max()/1e5:.1f}億t → 2025年度 {g(C,2025,'ton_jika')/1e5:.1f}億t")
L.append(f"営業用の最大（系列A）{A.loc[A.ton_eigyo.idxmax(),'year']}年度 {A.ton_eigyo.max()/1e5:.1f}億t; 系列C 2019→2025 {g(C,2025,'ton_eigyo')/g(C,2019,'ton_eigyo')-1:+.1%}")
L.append(f"系列C 2015→2025 合計 {g(C,2025,'ton_total')/g(C,2015,'ton_total')-1:+.1%} 営業 {g(C,2025,'ton_eigyo')/g(C,2015,'ton_eigyo')-1:+.1%} 自家 {g(C,2025,'ton_jika')/g(C,2015,'ton_jika')-1:+.1%}")
t = load("truck_ton_by_type_fy2015_2025.csv").set_index("year")
for y in [2020, 2025]:
    r = t.loc[y]; f = r.eigyo_futsu_total
    L.append(f"{y} 営業用普通車の内訳 16t以上{r.eigyo_futsu_ge16t/f:.1%} 11-16t{r.eigyo_futsu_11_16t/f:.1%} 6.5-11t{r.eigyo_futsu_6_5_11t/f:.1%} 3t未満{r.eigyo_futsu_lt3t/f:.1%} ; 自家用 普通{r.jika_futsu/r.jika_total:.1%} 小型{r.jika_kogata/r.jika_total:.1%} 特種{r.jika_tokushu/r.jika_total:.1%}")
(RES / "a186_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

def breaks(ax):
    for x, lab in [(2009.5, "2010年度に\n調査方法変更"), (2014.5, "")]:
        ax.axvline(x, color=GRAY, lw=0.8, ls=":")
    ax.text(2010.2, ax.get_ylim()[1] * 0.97, "2010〜14年度は\n調べ方が変わり接続せず", fontsize=8, color=GRAY, va="top")

# 図1：営業用の割合（重さ・トンキロ）
fig, ax = plt.subplots(figsize=(10, 4.4))
for s, ls in [(A, "-"), (B, "--"), (C, "-")]:
    ax.plot(s.year, s.sh_ton, color=BLUE, lw=2, ls=ls, label="輸送トン数（重さ）" if s is A else None)
    ax.plot(s.year, s.sh_tkm, color=ORANGE, lw=2, ls=ls, label="輸送トンキロ（重さ×距離）" if s is A else None)
ax.set_ylim(0, 100); ax.set_ylabel("営業用の割合（%）"); ax.set_xlim(1958, 2027)
ax.set_title("トラック輸送のうち営業用（運送会社）の割合")
breaks(ax); ax.legend(frameon=False, loc="lower right")
save(fig, "a186_share.png")

# 図2：営業用と自家用の輸送トン数
fig, ax = plt.subplots(figsize=(10, 4.4))
for s, ls in [(A, "-"), (B, "--"), (C, "-")]:
    ax.plot(s.year, s.ton_eigyo / 1e5, color=BLUE, lw=2, ls=ls, label="営業用" if s is A else None)
    ax.plot(s.year, s.ton_jika / 1e5, color=GREEN, lw=2, ls=ls, label="自家用" if s is A else None)
ax.set_ylabel("億トン"); ax.set_ylim(0, 40); ax.set_xlim(1958, 2027)
ax.set_title("トラックの輸送トン数：営業用と自家用"); breaks(ax); ax.legend(frameon=False, loc="upper left")
save(fig, "a186_tons.png")

# 図3：1トンあたりの平均輸送距離
fig, ax = plt.subplots(figsize=(10, 4.4))
for s in [A, C]:
    ax.plot(s.year, s.km_e, color=BLUE, lw=2, label="営業用" if s is A else None)
    ax.plot(s.year, s.km_j, color=GREEN, lw=2, label="自家用" if s is A else None)
ax.set_ylabel("km（トンキロ÷トン）"); ax.set_ylim(0, 120); ax.set_xlim(1958, 2027)
ax.axvspan(2009.5, 2014.5, color=LIGHT, alpha=0.4, lw=0)
ax.text(2010, 115, "2010〜14年度\nトンキロなし", fontsize=8, color=GRAY, va="top")
ax.set_title("1トンの荷物を平均何km運んでいるか"); ax.legend(frameon=False, loc="upper left")
save(fig, "a186_distance.png")
