"""研究者が増えたのはどの産業か：産業別の増減、シフトシェア分解、専門分野の分解"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, leaves, short, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, PURPLE, LIGHT, SOURCE

df = load()
LEAF = leaves(df)
P0, P1 = (2012, 2014), (2023, 2025)     # 年ごとの振れが大きいので3年平均で比べる


def pavg(d, p, col="total"):
    return d[d.year.between(*p)].groupby("no")[col].mean()


name = df[df.year == 2021].set_index("no").name.map(short)
lv = df[df.year == 2021].set_index("no").level

# ---- 全体 --------------------------------------------------------------
tot = df[df.no == 1].set_index("year").total
T0, T1 = tot.loc[P0[0]:P0[1]].mean(), tot.loc[P1[0]:P1[1]].mean()
g = T1 / T0 - 1

# ---- 産業別（いちばん細かい産業）とシフトシェア ---------------------------
r0, r1 = pavg(df, P0).reindex(LEAF), pavg(df, P1).reindex(LEAF)
ss = pd.DataFrame({"name": name.reindex(LEAF), "r0": r0, "r1": r1})
ss["change"] = ss.r1 - ss.r0
ss["growth_pct"] = (ss.r1 / ss.r0 - 1) * 100
ss["national_part"] = ss.r0 * g                 # 全体と同じ率で増えた場合の増加
ss["industry_part"] = ss.change - ss.national_part   # その産業ならではの上積み・下振れ
ss["share0"] = ss.r0 / ss.r0.sum() * 100; ss["share1"] = ss.r1 / ss.r1.sum() * 100
ss = ss.sort_values("change", ascending=False)
ss.round(1).to_csv(RES / "a139_industry_shiftshare.csv")

# 大分類（製造業／情報通信業／学術研究・専門技術サービス業／その他）でまとめる
def big(no):
    if 6 <= no <= 33: return "製造業"
    if 36 <= no <= 39: return "情報通信業"
    if 44 <= no <= 46: return "学術研究、専門・技術サービス業"
    return "その他の産業"
ss["big"] = [big(n) for n in ss.index]
bg = ss.groupby("big")[["r0", "r1", "change", "national_part", "industry_part"]].sum()
bg["growth_pct"] = (bg.r1 / bg.r0 - 1) * 100
bg["share_of_total_change"] = bg.change / bg.change.sum() * 100
bg.round(1).to_csv(RES / "a139_bigsector.csv")

# ---- 専門分野の分解：産業の伸び（構成効果）と産業内のシフト ----------------
# 分野グループ（足すと総数になる）
df2 = df.copy()
df2["sci_other"] = df2["sci"] - df2["info"]
df2["eng_other"] = df2["eng"] - df2["elec"] - df2["mech"]
FG = {"info": "情報科学", "sci_other": "理学（情報以外）", "elec": "電気・通信", "mech": "機械・船舶・航空",
      "eng_other": "工学（その他）", "agri": "農学", "health": "保健", "social_hum": "人文・社会科学"}
rows = []
E0, E1 = pavg(df2, P0).reindex(LEAF), pavg(df2, P1).reindex(LEAF)
for f, lab in FG.items():
    f0, f1 = pavg(df2, P0, f).reindex(LEAF), pavg(df2, P1, f).reindex(LEAF)
    s0, s1 = (f0 / E0).fillna(0), (f1 / E1).fillna(0)
    ind_effect = ((E1 - E0) * s0).sum()        # 産業の人数が増減した分（分野の割合は最初のまま）
    within = (E1 * (s1 - s0)).sum()            # 同じ産業の中で、その分野の割合が変わった分
    tot0, tot1 = f0.sum(), f1.sum()
    rows.append(dict(field=lab, r0=tot0, r1=tot1, change=tot1 - tot0, industry_effect=ind_effect, within_effect=within,
                     resid=tot1 - tot0 - ind_effect - within, growth_pct=(tot1 / tot0 - 1) * 100))
fd = pd.DataFrame(rows).set_index("field")
fd.round(1).to_csv(RES / "a139_field_decomposition.csv")

# 情報科学の研究者がどの産業で増えたか
i0, i1 = pavg(df2, P0, "info").reindex(LEAF), pavg(df2, P1, "info").reindex(LEAF)
info_ind = pd.DataFrame({"name": name.reindex(LEAF), "info0": i0, "info1": i1, "change": i1 - i0,
                         "share_in_industry0": i0 / E0 * 100, "share_in_industry1": i1 / E1 * 100}).sort_values("change", ascending=False)
info_ind.round(1).to_csv(RES / "a139_info_by_industry.csv")

# ---- 図1：産業別の増減と、全体並みなら -------------------------------------
top = pd.concat([ss.head(10), ss.tail(6)])
top = top.iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 7))
y = np.arange(len(top))
ax.barh(y, top.change / 1000, color=[BLUE if v > 0 else ORANGE for v in top.change], height=0.65, label="実際の増減")
ax.scatter(top.national_part / 1000, y, color=INK, s=22, zorder=3, label=f"全体と同じ率（+{g*100:.1f}%）なら")
ax.set_yticks(y); ax.set_yticklabels(top.name)
ax.axvline(0, color=INK, lw=0.6)
for yi, (v, gp) in enumerate(zip(top.change, top.growth_pct)):
    ax.text(v / 1000 + (0.3 if v > 0 else -0.3), yi, f"{gp:+.0f}%", va="center", ha="left" if v > 0 else "right", fontsize=9, color=INK)
ax.set_xlabel("研究者数の増減（千人）")
ax.set_title(f"研究者数の増減：{P0[0]}〜{P0[1]%100}年平均→{P1[0]}〜{P1[1]%100}年平均（企業、増加上位10・減少上位6）", loc="left", fontsize=12)
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.02, 0.98))
fig.text(0.01, -0.02, SOURCE + "。いちばん細かい産業区分。％は増減率", fontsize=8, color=GRAY)
fig.savefig(FIG / "a139_industry_change.png"); plt.close(fig)

# ---- 図2：主な産業の推移 ---------------------------------------------------
SEL = [(38, "情報サービス", PURPLE), (10, "医薬品", GREEN), (31, "自動車", BLUE), (25, "電子部品・デバイス", "#5f9ed1"),
       (29, "情報通信機械", ORANGE), (44, "学術・開発研究機関", INK)]
fig, ax = plt.subplots(figsize=(9.5, 5))
for no, lab, c in SEL:
    s = df[df.no == no].set_index("year").total / 1000
    ax.plot(s.index, s.values, color=c, lw=2, marker="o", ms=3)
    ax.text(2025.3, s.iloc[-1], lab, color=c, va="center", fontsize=10)
ax.set_xlim(2011.5, 2027.8); ax.set_ylabel("研究者数（千人）"); ax.set_ylim(0, None)
ax.set_title("主な産業の研究者数（企業、調査年ごと）", loc="left")
fig.text(0.01, -0.03, SOURCE + "。調査年（3月31日現在の人数）", fontsize=8, color=GRAY)
fig.savefig(FIG / "a139_trend.png"); plt.close(fig)

# ---- 図3：専門分野の分解 ---------------------------------------------------
fd2 = fd.sort_values("change")
fig, ax = plt.subplots(figsize=(9, 5))
y = np.arange(len(fd2))
ax.barh(y - 0.18, fd2.industry_effect / 1000, height=0.34, color=LIGHT, label="産業の人数の増減による分")
ax.barh(y + 0.18, fd2.within_effect / 1000, height=0.34, color=BLUE, label="同じ産業の中で割合が変わった分")
ax.scatter(fd2.change / 1000, y, color=INK, marker="D", s=24, zorder=3, label="実際の増減")
ax.set_yticks(y); ax.set_yticklabels(fd2.index); ax.axvline(0, color=INK, lw=0.6)
ax.set_xlabel("研究者数の増減（千人）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("専門分野別の増減を2つに分ける（企業、2012〜14年平均→2023〜25年平均）", loc="left", fontsize=12)
fig.text(0.01, -0.03, SOURCE, fontsize=8, color=GRAY)
fig.savefig(FIG / "a139_field_decomp.png"); plt.close(fig)

print(f"total {T0:.0f} -> {T1:.0f}  g={g*100:.2f}%")
print(ss[["name", "r0", "r1", "change", "growth_pct", "national_part", "industry_part", "share0", "share1"]].round(1).to_string())
print(bg.round(1).to_string())
print(fd.round(0).to_string())
print(info_ind.head(8).round(1).to_string())
