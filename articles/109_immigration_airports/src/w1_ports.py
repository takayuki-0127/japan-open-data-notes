"""W1：外国人はどの空港・港から入ってくるようになったか（2013→2019→2025）"""
from common import *

port, nat = load()
pn = load_port_nat()
full = port[port.year <= 2025]
G = MAIN + ["その他の空港", "海港"]
LAB = {g: g.replace("(空港)", "") for g in G}


def group(p):
    return p if p in MAIN else ("その他の空港" if is_air(p) else "海港")


x = full[full.port != "総数"].assign(g=lambda d: d.port.map(group))
yr = x.groupby(["year", "g"]).n.sum().unstack()[G]
tot = yr.sum(1)
share = yr.div(tot, axis=0) * 100
out = pd.concat([yr.add_suffix("_人"), share.round(2).add_suffix("_%")], axis=1)
out.insert(0, "総数", tot)
out.to_csv(RES / "w1_port_group_year.csv", encoding="utf-8-sig")

# 港ごとの 2013・2019・2025 年
py = full[full.port != "総数"].groupby(["port", "year"]).n.sum().unstack().fillna(0)
t = py[[2013, 2019, 2023, 2024, 2025]].copy()
t["2025/2019"] = (t[2025] / t[2019]).round(3)
t["2019/2013"] = (t[2019] / t[2013]).round(3)
t["share2013_%"] = (t[2013] / t[2013].sum() * 100).round(2)
t["share2019_%"] = (t[2019] / t[2019].sum() * 100).round(2)
t["share2025_%"] = (t[2025] / t[2025].sum() * 100).round(2)
t = t.sort_values(2025, ascending=False)
t.to_csv(RES / "w1_port_year.csv", encoding="utf-8-sig")

# 2019年の同じ月と比べた回復（主な空港・海港、2023年1月〜最新月）
m = port[port.port != "総数"].assign(g=lambda d: d.port.map(group)).groupby(["year", "month", "g"]).n.sum().unstack()[G]
m["総数"] = m.sum(1)
base = m.loc[2019]
rec = []
for (y, mo), r in m.loc[2023:].iterrows():
    rec.append(dict(year=y, month=mo, **{k: round(r[k] / base.loc[mo, k], 3) for k in m.columns}))
rec = pd.DataFrame(rec)
rec.to_csv(RES / "w1_recovery_vs2019.csv", index=False, encoding="utf-8-sig")

# 羽田・関西・成田などの増減を国籍で分ける（2019→2025）
TOPN = ["韓国", "中国", "台湾", "中国（香港）", "米国", "タイ", "フィリピン", "ベトナム", "オーストラリア", "シンガポール"]
pn2 = pn[pn.year.isin([2019, 2025]) & ~pn.nat.isin(REGIONS)]
dec = []
for g in G:
    d = pn2[pn2.group == g].pivot_table(index="nat", columns="year", values="n", aggfunc="sum").fillna(0)
    d["diff"] = d[2025] - d[2019]
    for k in TOPN: dec.append(dict(group=g, nat=k, n2019=d.loc[k, 2019] if k in d.index else 0, n2025=d.loc[k, 2025] if k in d.index else 0))
    rest = d.drop([k for k in TOPN if k in d.index])
    dec.append(dict(group=g, nat="その他", n2019=rest[2019].sum(), n2025=rest[2025].sum()))
dec = pd.DataFrame(dec); dec["diff"] = dec.n2025 - dec.n2019
dec.to_csv(RES / "w1_change_by_nat.csv", index=False, encoding="utf-8-sig")

print("総数", tot.loc[[2013, 2019, 2025]].to_dict())
print(share.loc[[2013, 2019, 2023, 2024, 2025]].round(1).to_string())
print(yr.loc[[2013, 2019, 2025]].astype(int).to_string())
print((yr.loc[2025] / yr.loc[2019]).round(2).to_string())
print(t.head(20)[[2013, 2019, 2025, "2025/2019", "share2025_%"]].to_string())
print(rec.tail(8).to_string())
print(dec.pivot(index="nat", columns="group", values="diff").astype(int).to_string())

# 図1：入国者に占める割合（年）
fig, ax = plt.subplots(figsize=(9, 5.2))
col = {"成田(空港)": BLUE, "羽田(空港)": ORANGE, "関西(空港)": GREEN, "中部(空港)": PURPLE, "福岡(空港)": RED,
       "新千歳(空港)": "#d6a52a", "那覇(空港)": "#2ab3c6", "その他の空港": GRAY, "海港": INK}
yy = [y for y in share.index if y not in (2020, 2021, 2022)]
lab_y = spread([share.loc[2025, g] for g in G], 1.6)
for g, ly in zip(G, lab_y):
    s = share[g]
    for seg in ([y for y in yy if y <= 2019], [y for y in yy if y >= 2023]):
        ax.plot(seg, s.loc[seg].values, color=col[g], lw=2.2 if g in MAIN[:3] else 1.4, marker="o", ms=3)
    ax.text(2025.3, ly, f"{LAB[g]} {s.loc[2025]:.1f}%", color=col[g], va="center", fontsize=9)
ax.axvspan(2019.5, 2022.5, color="#eeeeee", zorder=0)
ax.text(2021, 39, "2020〜22年は\n入国がごく少ないので\n省略", ha="center", va="top", fontsize=8, color=GRAY)
ax.set_xlim(2012.5, 2027.6); ax.set_ylabel("外国人入国者に占める割合（%）")
ax.set_title("外国人入国者がどの空港・港から入ったか（2013〜2025年）", loc="left")
note(ax, SOURCE + "。海港には船舶観光上陸許可で上陸したクルーズ客は含まない", y=-0.1)
fig.savefig(FIG / "w1_share.png"); plt.close(fig)

# 図2：2019年→2025年の増減（港のグループ×国籍）
fig, ax = plt.subplots(figsize=(9, 5.2))
order = G
cols = dict(zip(TOPN + ["その他"], ["#2a78d6", "#c8423b", "#3aa07a", "#eb6834", "#7a5bd6", "#d6a52a", "#2ab3c6", "#8c6d46", "#e58fb8", "#5b7fa3", GRAY]))
piv = dec.pivot(index="group", columns="nat", values="diff").loc[order][TOPN + ["その他"]] / 1e4
posb = np.zeros(len(order)); negb = np.zeros(len(order))
yv = np.arange(len(order))[::-1]
for k in TOPN + ["その他"]:
    v = piv[k].values
    ax.barh(yv, np.where(v > 0, v, 0), left=posb, color=cols[k], label=k, height=0.7)
    ax.barh(yv, np.where(v < 0, v, 0), left=negb, color=cols[k], height=0.7)
    posb += np.where(v > 0, v, 0); negb += np.where(v < 0, v, 0)
net = piv.sum(1).values
for i, g in enumerate(order):
    ax.text(max(posb[i], 0) + 8, yv[i], f"計 {net[i]:+,.0f}万人", va="center", fontsize=9)
ax.set_yticks(yv); ax.set_yticklabels([LAB[g] for g in order]); ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("2019年→2025年の増減（万人）"); ax.legend(ncol=4, fontsize=8, frameon=False, loc="lower right")
ax.set_title("2019年から2025年に、どの空港・港で誰が増えたか", loc="left")
ax.set_xlim(negb.min() - 10, posb.max() + 60)
note(ax, y=-0.13)
fig.savefig(FIG / "w1_change.png"); plt.close(fig)

# 図3：2019年の同じ月を100とした回復
fig, ax = plt.subplots(figsize=(9, 5.2))
dt = pd.to_datetime(dict(year=rec.year, month=rec.month, day=1))
sm = rec.set_index(dt).drop(columns=["year", "month"]).rolling(3).mean().iloc[2:] * 100
gs = ["羽田(空港)", "福岡(空港)", "成田(空港)", "関西(空港)", "新千歳(空港)", "中部(空港)"]
ly = spread([sm[g].iloc[-1] for g in gs] + [sm["総数"].iloc[-1]], 7)
for g, y0 in zip(gs, ly):
    ax.plot(sm.index, sm[g], color=col[g], lw=2 if g in MAIN[:3] else 1.4)
    ax.text(sm.index[-1] + pd.Timedelta(days=20), y0, f"{LAB[g]} {sm[g].iloc[-1]:.0f}", color=col[g], va="center", fontsize=9)
ax.plot(sm.index, sm["総数"], color=INK, lw=1, ls="--")
ax.text(sm.index[-1] + pd.Timedelta(days=20), ly[-1], f"全体 {sm['総数'].iloc[-1]:.0f}", fontsize=9, va="center")
ax.axhline(100, color=GRAY, lw=0.8)
ax.set_ylabel("2019年の同じ月＝100（3か月平均）"); ax.set_xlim(sm.index[0], sm.index[-1] + pd.Timedelta(days=150))
ax.set_title("コロナ前（2019年の同じ月）と比べた入国者数（空港別）", loc="left")
note(ax, y=-0.1)
fig.savefig(FIG / "w1_recovery.png"); plt.close(fig)
