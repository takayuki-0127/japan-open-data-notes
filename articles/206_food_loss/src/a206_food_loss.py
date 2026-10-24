"""A206 食品ロスは、家庭と事業者のどちらが減ったか（寄与度分解）"""
from common import *

d, g = load()
rows = []
for a, b in ((2012, 2024), (2019, 2024), (2015, 2024)):
    tot = d.total[b] - d.total[a]
    for c in ["business", "household"] + list(COMP):
        ch = d[c][b] - d[c][a]
        rows.append({"from": a, "to": b, "item": c, "label": COMP.get(c, {"business": "事業系", "household": "家庭系"}[c] if c in ("business", "household") else c),
                     "v_from": d[c][a], "v_to": d[c][b], "change": ch, "pct": ch / d[c][a] * 100, "contrib_pct_of_total_change": ch / tot * 100})
dc = pd.DataFrame(rows); dc.round(2).to_csv(RES / "decomposition.csv", index=False)
prog = pd.DataFrame({k: {"base2000": g.base[k], "fy2024": d[k][2024], "target2030": g.target[k],
                         "reduction_vs2000_pct": (1 - d[k][2024] / g.base[k]) * 100,
                         "target_reduction_pct": (1 - g.target[k] / g.base[k]) * 100,
                         "remaining_to_target": d[k][2024] - g.target[k]} for k in ("business", "household")}).T
prog.round(2).to_csv(RES / "targets_progress.csv")
with open(RES / "summary.txt", "w") as f:
    f.write(dc.round(1).to_string() + "\n\n" + prog.round(1).to_string() + "\n")
    f.write(f"restaurant share of business 2012 {d.b_restaurant[2012]/d.business[2012]*100:.1f}% 2019 {d.b_restaurant[2019]/d.business[2019]*100:.1f}% 2024 {d.b_restaurant[2024]/d.business[2024]*100:.1f}%\n")
    f.write(f"business share of total 2012 {d.business[2012]/d.total[2012]*100:.1f}% 2024 {d.business[2024]/d.total[2024]*100:.1f}%\n")

# fig1 trend with targets
fig, ax = plt.subplots(figsize=(8, 4.8))
for k, col, lab in (("business", BLUE, "事業系"), ("household", ORANGE, "家庭系")):
    ax.plot(d.index, d[k], color=col, marker="o", label=lab)
    ax.axhline(g.target[k], color=col, ls=":", lw=1)
    ax.text(2012, d[k][2012] + (6 if k == "business" else -14), f"{d[k][2012]}", color=col, fontsize=9, ha="center")
    ax.text(2024, d[k][2024] + (6 if k == "business" else -14), f"{d[k][2024]}", color=col, fontsize=9, ha="center")
ax.text(2011.8, g.target["business"] + 2, f"事業系の2030年度目標 {g.target['business']}", color=BLUE, fontsize=8.5, ha="left", va="bottom")
ax.text(2011.8, g.target["household"] - 2, f"家庭系の2030年度目標 {g.target['household']}", color=ORANGE, fontsize=8.5, ha="left", va="top")
ax.set_ylim(150, 400); ax.set_ylabel("食品ロス量（万トン）"); ax.set_xticks(range(2012, 2025, 2))
ax.legend(frameon=False, loc="upper right"); ax.set_title("事業系と家庭系の食品ロス量（2012〜2024年度）と2030年度目標", loc="left", fontsize=12)
save(fig, "a206_trend.png")

# fig2 decomposition 2012->2024
x = dc[(dc["from"] == 2012) & dc.item.isin(list(COMP))].set_index("label")
fig, ax = plt.subplots(figsize=(8, 4.6))
cols = [BLUE if i.startswith("b_") else ORANGE for i in x.item]
ax.barh(x.index[::-1], x.change[::-1], color=cols[::-1])
for i, (k, v) in enumerate(x.change[::-1].items()):
    ax.text(v - 1, i, f"{v:+.0f}", va="center", ha="right", fontsize=9)
ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-70, 5)
ax.set_xlabel("2012→2024年度の増減（万トン）")
ax.set_title(f"何が減ったか：事業系{d.business[2024]-d.business[2012]:+d}万トン、家庭系{d.household[2024]-d.household[2012]:+d}万トン", loc="left")
ax.text(-69, 6.3, "■ 事業系", color=BLUE, fontsize=9); ax.text(-69, 5.7, "■ 家庭系", color=ORANGE, fontsize=9)
save(fig, "a206_decomp.png")

# fig3 components over time
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, keys, ttl in ((axs[0], ["b_manufacturing", "b_restaurant", "b_retail", "b_wholesale"], "事業系（業種別）"),
                      (axs[1], ["h_leftover", "h_direct", "h_overpeel"], "家庭系（発生要因別）")):
    pal = [BLUE, ORANGE, GREEN, GRAY]
    for k, col in zip(keys, pal):
        ax.plot(d.index, d[k], color=col, marker="o", ms=3.5, label=COMP[k])
        ax.text(2024.3, d[k][2024] + {"h_direct": 3, "h_leftover": -3}.get(k, 0), f"{d[k][2024]}", fontsize=8.5, va="center", color=col)
    ax.set_title(ttl, loc="left"); ax.set_xticks(range(2012, 2025, 4)); ax.legend(frameon=False, fontsize=8.5, loc="upper right")
axs[0].set_ylabel("食品ロス量（万トン）"); axs[0].set_ylim(0, 170)
save(fig, "a206_components.png")
print(open(RES / "summary.txt").read())
