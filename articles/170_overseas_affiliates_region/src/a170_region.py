"""日本企業の海外現地法人は、中国からどこへ移ったのか（2015〜2024年度）"""
from common import *

d = load("affiliates_by_region_fy2015_2024.csv"); d["code"] = d["code"].astype(str)
Y = [c for c in d.columns if c.startswith("fy")]; yrs = [int(c[2:]) for c in Y]
def tab(m):
    t = d[d.metric == m].set_index("region")[Y].astype(float); return t
F, E, S = tab("firms"), tab("employees"), tab("sales_mjpy")
TOP = ["中国", "ASEAN10", "北米", "欧州", "その他アジア", "中南米", "オセアニア", "中東", "アフリカ"]
# 地域の合計チェック（北米+中南米+アジア+中東+欧州+オセアニア+アフリカ = 全地域）
for t, nm in [(F, "firms"), (E, "employees"), (S, "sales")]:
    s = t.loc[["北米", "中南米", "アジア", "中東", "欧州", "オセアニア", "アフリカ"]].sum() - t.loc["全地域"]
    print(nm, "地域合計−全地域 の最大差:", s.abs().max())
share = lambda t: t.loc[TOP].div(t.loc["全地域"]) * 100
fs, es, ss = share(F), share(E), share(S)
a, b = "fy2015", "fy2024"
out = pd.DataFrame({"firms2015": F.loc[TOP, a], "firms2024": F.loc[TOP, b], "firm_share2015": fs[a], "firm_share2024": fs[b],
                    "emp2015": E.loc[TOP, a], "emp2024": E.loc[TOP, b], "emp_chg_pct": (E.loc[TOP, b] / E.loc[TOP, a] - 1) * 100,
                    "emp_share2015": es[a], "emp_share2024": es[b], "sales_share2015": ss[a], "sales_share2024": ss[b]})
out.round(2).to_csv(RES / "a170_region_2015_2024.csv", encoding="utf-8")
pd.concat({"firm_share": fs, "emp_share": es, "sales_share": ss}).round(2).to_csv(RES / "a170_shares_by_year.csv", encoding="utf-8")
cross = [y for y, c, s_ in zip(yrs, F.loc["中国"], F.loc["ASEAN10"]) if s_ > c]
L = [f"現地法人数 全地域 {F.loc['全地域',a]:.0f} → {F.loc['全地域',b]:.0f}", out.round(1).to_string(),
     f"ASEAN10の法人数が中国（香港含む）を上回った年度: {cross}",
     f"中国の常時従業者数 {E.loc['中国',a]/1e4:.1f}万 → {E.loc['中国',b]/1e4:.1f}万（{E.loc['中国',b]/E.loc['中国',a]-1:+.1%}）",
     f"中国本土の法人数 {F.loc['中国本土',a]:.0f} → {F.loc['中国本土',b]:.0f}；EU 2019 {F.loc['ＥＵ','fy2019']:.0f} → 2020 {F.loc['ＥＵ','fy2020']:.0f}（英国の離脱）"]
(RES / "a170_summary.txt").write_text("\n\n".join(L), encoding="utf-8"); print("\n\n".join(L))

C = {"中国": ORANGE, "ASEAN10": BLUE, "北米": GREEN, "欧州": PURPLE, "その他アジア": GRAY}
LB = {"中国": "中国（香港を含む）", "ASEAN10": "ASEAN10", "北米": "北米", "欧州": "欧州", "その他アジア": "その他アジア"}
# 図1：法人数
fig, ax = plt.subplots(figsize=(9.5, 4.8))
for k, c in C.items():
    ax.plot(yrs, F.loc[k].values, color=c, lw=2.2 if k in ("中国", "ASEAN10") else 1.6, marker="o", ms=3)
    ax.text(2024.2, F.loc[k, b], LB[k], color=c, fontsize=8.5, va="center")
ax.set_xlim(2015, 2026.6); ax.set_xticks(yrs); ax.set_ylim(0, 8800); ax.set_ylabel("現地法人数（社、年度末）")
ax.set_title("現地法人の数は2021年度にASEAN10が中国を上回った")
save(fig, "a170_firms.png")

# 図2：常時従業者数（2015年度=100）
fig, ax = plt.subplots(figsize=(9.5, 4.8))
for k, c in C.items():
    v = E.loc[k] / E.loc[k, a] * 100
    ax.plot(yrs, v.values, color=c, lw=2.2 if k in ("中国", "ASEAN10") else 1.6, marker="o", ms=3)
    ax.text(2024.2, v[b] + {"その他アジア": 1.6, "北米": 0, "欧州": -2.2}.get(k, 0), f"{LB[k]} {v[b]:.0f}", color=c, fontsize=8.5, va="center")
ax.axhline(100, color=INK, lw=0.6); ax.set_xlim(2015, 2027.2); ax.set_xticks(yrs); ax.set_ylabel("2015年度＝100")
ax.set_title("中国の現地法人で働く人は9年で4割減。ASEAN10はほぼ横ばい")
save(fig, "a170_employees.png")

# 図3：構成比（法人数・従業者・売上高、2015 vs 2024）
fig, axs = plt.subplots(1, 3, figsize=(10.5, 4.6), sharey=True)
K = ["中国", "ASEAN10", "北米", "欧州", "その他アジア"]
for ax, (t, nm) in zip(axs, [(fs, "現地法人数"), (es, "常時従業者数"), (ss, "売上高")]):
    idx = range(len(K))
    ax.barh([i + 0.2 for i in idx], t.loc[K, a], height=0.4, color=LIGHT, label="2015年度")
    ax.barh([i - 0.2 for i in idx], t.loc[K, b], height=0.4, color=[C[k] for k in K], label="2024年度")
    for i, k in enumerate(K):
        ax.text(max(t.loc[k, a], t.loc[k, b]) + 0.8, i, f"{t.loc[k,a]:.0f}→{t.loc[k,b]:.0f}%", va="center", fontsize=8)
    ax.set_title(nm, fontsize=10); ax.set_xlim(0, 52)
axs[0].set_yticks(list(range(len(K)))); axs[0].set_yticklabels([LB[k] for k in K]); axs[0].invert_yaxis()
from matplotlib.patches import Patch
axs[0].legend(handles=[Patch(color=LIGHT, label="2015年度"), Patch(color=INK, label="2024年度（色付き）")], loc="lower right", frameon=False, fontsize=8)
fig.suptitle("全地域に占める割合（%）。中国はどの指標でも割合が下がり、ASEAN10はどれも上がった", fontsize=11)
save(fig, "a170_shares.png")
