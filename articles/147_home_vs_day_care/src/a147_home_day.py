"""訪問介護と通所介護、利用者の伸びの差は？（2008〜2025年度の年間実受給者数）"""
from common import *

nat, pref = load()
Y0, Y1 = 2008, 2025
d = nat.loc[Y0:Y1]
L = []
for c, n in [("total", "介護サービス全体"), ("houmon_kaigo", "訪問介護"), ("tsusho_all", "通所介護（地域密着型を含む）"),
             ("houmon_kango", "訪問看護"), ("fukushi_yogu", "福祉用具貸与"), ("tsusho_reha", "通所リハビリ"), ("houmon_nyuyoku", "訪問入浴")]:
    L.append(f"{n}: {Y0}年度 {d.loc[Y0,c]:,.1f}千人 → {Y1}年度 {d.loc[Y1,c]:,.1f}千人（{d.loc[Y1,c]/d.loc[Y0,c]-1:+.1%}）")
for a, b in [(2008, 2015), (2016, 2019), (2019, 2025), (2016, 2025)]:
    L.append(f"{a}→{b} 年率 訪問介護 {(d.loc[b,'houmon_kaigo']/d.loc[a,'houmon_kaigo'])**(1/(b-a))-1:+.2%} 通所介護 {(d.loc[b,'tsusho_all']/d.loc[a,'tsusho_all'])**(1/(b-a))-1:+.2%} 全体 {(d.loc[b,'total']/d.loc[a,'total'])**(1/(b-a))-1:+.2%}")
L.append(f"2019→2020 訪問介護 {d.loc[2020,'houmon_kaigo']/d.loc[2019,'houmon_kaigo']-1:+.1%} 通所介護 {d.loc[2020,'tsusho_all']/d.loc[2019,'tsusho_all']-1:+.1%} 訪問看護 {d.loc[2020,'houmon_kango']/d.loc[2019,'houmon_kango']-1:+.1%}")
for c, n in [("houmon_kaigo", "訪問介護"), ("tsusho_all", "通所介護"), ("houmon_kango", "訪問看護")]:
    s = d[c] / d.total
    L.append(f"{n}を使う人の割合（全体の受給者に対して）: {Y0} {s[Y0]:.1%} → 2015 {s[2015]:.1%} → {Y1} {s[Y1]:.1%}")
L.append(f"2016年度の切り替え：通所介護 2015 {d.loc[2015,'tsusho_kaigo']:.1f} → 2016 {d.loc[2016,'tsusho_kaigo']:.1f}、地域密着型通所介護 2016 {d.loc[2016,'chiiki_tsusho']:.1f}")
pref["houmon_ratio"] = pref.houmon_kaigo_2025 / pref.houmon_kaigo_2015
pref["tsusho_ratio"] = pref.tsusho_all_2025 / pref.tsusho_all_2015
pref["share_houmon_2025"] = pref.houmon_kaigo_2025 / pref.total_2025
pref["share_tsusho_2025"] = pref.tsusho_all_2025 / pref.total_2025
L.append(f"2015→2025 訪問介護が減った県 {(pref.houmon_ratio<1).sum()}、通所介護が減った県 {(pref.tsusho_ratio<1).sum()}、通所の伸びが訪問を上回った県 {(pref.tsusho_ratio>pref.houmon_ratio).sum()}")
L.append("訪問介護の伸び 上位: " + "、".join(f"{r.pref}{r.houmon_ratio-1:+.0%}" for r in pref.nlargest(5, "houmon_ratio").itertuples()))
L.append("訪問介護の伸び 下位: " + "、".join(f"{r.pref}{r.houmon_ratio-1:+.0%}" for r in pref.nsmallest(5, "houmon_ratio").itertuples()))
L.append("通所介護の伸び 上位: " + "、".join(f"{r.pref}{r.tsusho_ratio-1:+.0%}" for r in pref.nlargest(5, "tsusho_ratio").itertuples()))
L.append("通所介護の伸び 下位: " + "、".join(f"{r.pref}{r.tsusho_ratio-1:+.0%}" for r in pref.nsmallest(5, "tsusho_ratio").itertuples()))
L.append("2025年度 訪問介護を使う人の割合 上位: " + "、".join(f"{r.pref}{r.share_houmon_2025:.0%}" for r in pref.nlargest(5, "share_houmon_2025").itertuples())
         + " 下位: " + "、".join(f"{r.pref}{r.share_houmon_2025:.0%}" for r in pref.nsmallest(5, "share_houmon_2025").itertuples()))
L.append(f"相関（2015→2025の伸び 訪問 vs 通所）: {pref.houmon_ratio.corr(pref.tsusho_ratio):.2f}")
nat.to_csv(RES / "a147_national.csv", encoding="utf-8")
pref.to_csv(RES / "a147_pref_change.csv", index=False, encoding="utf-8")
(RES / "a147_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：人数の推移
fig, ax = plt.subplots(figsize=(9.5, 4.6))
ax.plot(d.index, d.houmon_kaigo / 1000, color=BLUE, lw=2.4, marker="o", ms=3.5, label="訪問介護")
ax.plot(d.index, d.tsusho_all / 1000, color=ORANGE, lw=2.4, marker="o", ms=3.5, label="通所介護（地域密着型を含む）")
ax.plot(d.index, d.houmon_kango / 1000, color=GREEN, lw=1.6, ls="--", label="訪問看護（参考）")
for y, t in [(2016, "小規模な通所介護が\n地域密着型に移る"), (2020, "コロナ")]:
    ax.axvline(y, color=GRAY, lw=0.8, ls=":")
    ax.text(y + 0.15, 2.45, t, fontsize=8.5, color=GRAY, va="top")
for c, col in [("houmon_kaigo", BLUE), ("tsusho_all", ORANGE), ("houmon_kango", GREEN)]:
    ax.text(Y1 + 0.3, d.loc[Y1, c] / 1000, f"{d.loc[Y1,c]/1000:.2f}", color=col, va="center", fontsize=9.5)
ax.set_ylim(0, 2.5); ax.set_xlim(Y0 - 0.5, Y1 + 1.5); ax.set_xticks(range(2008, 2026, 2))
ax.text(2016.2, 0.12, "2016年度以降の通所介護は2つの合計で、\n両方を使った人は二重に数えられる", fontsize=8, color=GRAY)
ax.set_ylabel("年間に1回以上使った人（百万人）")
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
ax.set_title("訪問介護と通所介護の年間実受給者数（要介護1〜5、各年度）")
save(fig, "a147_trend.png")

# 図2：期間ごとの年平均の伸び
P = [(2008, 2015, "2008→15年度"), (2016, 2019, "2016→19年度"), (2019, 2025, "2019→25年度")]
S = [("houmon_kaigo", "訪問介護", BLUE), ("tsusho_all", "通所介護", ORANGE), ("houmon_kango", "訪問看護", GREEN), ("total", "介護サービス全体", GRAY)]
rows = []
for a, b, lab in P:
    for c, n, col in S:
        rows.append(dict(period=lab, service=n, rate=((d.loc[b, c] / d.loc[a, c]) ** (1 / (b - a)) - 1) * 100))
gr = pd.DataFrame(rows); gr.to_csv(RES / "a147_growth_by_period.csv", index=False, encoding="utf-8")
fig, ax = plt.subplots(figsize=(9.5, 4.4))
w = 0.2; xs = np.arange(len(P))
for k, (c, n, col) in enumerate(S):
    v = gr[gr.service == n].rate.values
    ax.bar(xs + (k - 1.5) * w, v, width=w, color=col, label=n)
    for x0, vv in zip(xs + (k - 1.5) * w, v):
        ax.text(x0, vv + 0.15, f"{vv:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(xs); ax.set_xticklabels([p[2] for p in P]); ax.axhline(0, color=GRAY, lw=0.6)
ax.set_ylabel("年平均の増加率（%）"); ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper right")
ax.set_ylim(0, 8.5)
ax.set_title("期間ごとの利用者の伸び（年平均）：2019年度以降は訪問介護が通所介護を上回った")
save(fig, "a147_growth.png")

# 図3：都道府県ごとの、訪問介護を使う人の割合（2025年度）
p = pref.sort_values("share_houmon_2025")
fig, ax = plt.subplots(figsize=(9.5, 9.5))
ys = np.arange(len(p))
ax.barh(ys, p.share_houmon_2025 * 100, color=BLUE, height=0.7, label="訪問介護")
nat_share = nat.loc[2025, "houmon_kaigo"] / nat.loc[2025, "total"] * 100
ax.axvline(nat_share, color=INK, lw=0.8, ls="--"); ax.text(nat_share + 0.4, len(p) - 0.5, f"全国 {nat_share:.0f}%", fontsize=9)
ax.set_yticks(ys); ax.set_yticklabels(p.pref, fontsize=8.5)
ax.set_xlabel("介護サービスの受給者のうち、そのサービスを使った人の割合（2025年度、%）")
ax.set_title("訪問介護を使う人の割合は、大阪府45%から佐賀県14%まで")
save(fig, "a147_pref.png")
