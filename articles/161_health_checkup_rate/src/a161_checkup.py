"""特定健診の受診率は、保険者の種類でどれだけ違うか（2008〜2023年度）"""
from common import *

k = load("checkup_rate.csv").set_index("year")
g = load("guidance_rate.csv").set_index("year")
N = {"kokuho": "市町村国保", "kokuho_kumiai": "国保組合", "kyokai": "協会けんぽ", "senin": "船員保険", "kenpo": "健保組合", "kyosai": "共済組合"}
def spread(vals, gap):
    """ラベルが重ならないように縦位置をずらす"""
    items = sorted(vals.items(), key=lambda x: x[1]); out = {}; last = -1e9
    for k_, v in items:
        v2 = max(v, last + gap); out[k_] = v2; last = v2
    return out


C = {"kokuho": ORANGE, "kokuho_kumiai": PURPLE, "kyokai": GREEN, "senin": GRAY, "kenpo": BLUE, "kyosai": INK}
L = []
for c, n in N.items():
    L.append(f"{n}: 健診 2008 {k.loc[2008,c]:.1f}% → 2019 {k.loc[2019,c]:.1f}% → 2020 {k.loc[2020,c]:.1f}% → 2023 {k.loc[2023,c]:.1f}%（+{k.loc[2023,c]-k.loc[2008,c]:.1f}pt）"
             f" / 保健指導 2023 {g.loc[2023,c]:.1f}%")
L.append(f"全体: 健診 {k.loc[2008,'all']}→{k.loc[2023,'all']}%  保健指導 {g.loc[2008,'all']}→{g.loc[2023,'all']}%")
gap = (k[["kenpo", "kyosai"]].max(axis=1) - k.kokuho)
L.append("健保組合・共済組合（高い方）と市町村国保の差: " + "、".join(f"{y} {gap[y]:.1f}pt" for y in [2008, 2011, 2015, 2019, 2023]))
L.append(f"市町村国保の規模別 2023: 大 {k.loc[2023,'kokuho_l']} 中 {k.loc[2023,'kokuho_m']} 小 {k.loc[2023,'kokuho_s']}（保健指導 大 {g.loc[2023,'kokuho_l']} 中 {g.loc[2023,'kokuho_m']} 小 {g.loc[2023,'kokuho_s']}）")
L.append(f"健保組合 2023: 総合 {k.loc[2023,'kenpo_sogo']} 単一 {k.loc[2023,'kenpo_tan']}（保健指導 総合 {g.loc[2023,'kenpo_sogo']} 単一 {g.loc[2023,'kenpo_tan']}）")
pd.concat({"checkup": k, "guidance": g}, axis=1).to_csv(RES / "a161_rates.csv", encoding="utf-8")
(RES / "a161_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：健診の実施率の推移
fig, ax = plt.subplots(figsize=(10, 5.2))
pos = spread({c: k.loc[2023, c] for c in N}, 3.2)
for c, n in N.items():
    ax.plot(k.index, k[c], color=C[c], lw=2.2 if c in ("kokuho", "kenpo", "kyokai") else 1.4, marker="o", ms=3)
    ax.text(2023.3, pos[c], f"{n} {k.loc[2023,c]:.1f}%", va="center", fontsize=9.5, color=C[c])
ax.plot(k.index, k["all"], color=GRAY, lw=1.2, ls="--")
ax.text(2023.3, 64.5, f"全体 {k.loc[2023,'all']:.1f}%", fontsize=9, color=GRAY)
ax.axhline(70, color=GRAY, lw=0.8, ls=":")
ax.text(2008, 71, "国の目標（全体70%）", fontsize=8.5, color=GRAY)
ax.set_xticks(range(2008, 2024, 3)); ax.set_xlim(2007.5, 2027.5); ax.set_ylim(0, 90); ax.set_ylabel("特定健診の実施率（%）")
ax.set_title("保険者の種類別、特定健診の実施率（2008〜2023年度）")
save(fig, "a161_trend.png")

# 図2：2023年度 健診と保健指導（細かい区分）
S = [("kokuho_l", "市町村国保（大）"), ("kokuho_m", "市町村国保（中）"), ("kokuho_s", "市町村国保（小）"), ("kokuho_kumiai", "国保組合"),
     ("kyokai", "協会けんぽ"), ("senin", "船員保険"), ("kenpo_sogo", "健保組合（総合）"), ("kenpo_tan", "健保組合（単一）"), ("kyosai", "共済組合")]
fig, ax = plt.subplots(figsize=(10, 5.4))
y = np.arange(len(S))[::-1]
ax.barh(y + 0.2, [k.loc[2023, c] for c, _ in S], height=0.38, color=BLUE, label="特定健診の実施率")
ax.barh(y - 0.2, [g.loc[2023, c] for c, _ in S], height=0.38, color=ORANGE, label="特定保健指導の実施率")
for yy, (c, _) in zip(y, S):
    ax.text(k.loc[2023, c] + 0.8, yy + 0.2, f"{k.loc[2023,c]:.1f}", va="center", fontsize=9)
    ax.text(g.loc[2023, c] + 0.8, yy - 0.2, f"{g.loc[2023,c]:.1f}", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels([n for _, n in S]); ax.set_xlim(0, 118); ax.set_xticks(range(0, 101, 20)); ax.set_xlabel("%（2023年度）")
ax.legend(frameon=False, loc="center right"); ax.set_title("健診は「会社の保険」が高く、保健指導は小さな市町村国保が高い")
save(fig, "a161_2023.png")

# 図3：特定保健指導の実施率の推移
fig, ax = plt.subplots(figsize=(10, 5))
pos = spread({c: g.loc[2023, c] for c in N}, 1.8)
for c, n in N.items():
    ax.plot(g.index, g[c], color=C[c], lw=2.2 if c in ("kokuho", "kenpo", "kyokai") else 1.4, marker="o", ms=3)
    ax.text(2023.3, pos[c], f"{n} {g.loc[2023,c]:.1f}%", va="center", fontsize=9.5, color=C[c])
ax.axhline(45, color=GRAY, lw=0.8, ls=":"); ax.text(2008, 46, "国の目標（全体45%）", fontsize=8.5, color=GRAY)
ax.set_xticks(range(2008, 2024, 3)); ax.set_xlim(2007.5, 2027.5); ax.set_ylim(0, 50); ax.set_ylabel("特定保健指導の実施率（%）")
ax.set_title("特定保健指導の実施率（2008〜2023年度）")
save(fig, "a161_guidance.png")
