"""F1：家計の金融資産の増加は「買った分（フロー）」と「値上がりなど（調整）」のどちらによるか。
残高の変化 ＝ フロー（取引）＋ 調整（時価の変動など）という資金循環統計の恒等式で分ける"""
from common import *

st, fl, adj = load()
main = ["A100", "A400", "A330", "A318", "A300"]
rows = []
for a, b, lab in [("1998Q1", "2026Q2", "1998〜2026年"), ("2014Q1", "2023Q4", "2014〜2023年（旧NISA期）"), ("2024Q1", "2026Q2", "2024年〜（新NISA）")]:
    for it in main + ["A331", "A332", "A900"]:
        rows.append(dict(period=lab, item=ITEMS[it], stock_start=st[it].loc[pd.Period(a, "Q") - 1], stock_end=st[it].loc[b],
                         flow=fl[it].loc[a:b].sum(), adj=adj[it].loc[a:b].sum()))
d = pd.DataFrame(rows); d["change"] = d.stock_end - d.stock_start
d.round(2).to_csv(RES / "f1_decomposition.csv", index=False, encoding="utf-8-sig"); print(d.round(1).to_string())
share = st[main].div(st["A900"], axis=0) * 100
share.columns = [ITEMS[c] for c in share.columns]; share.round(2).to_csv(RES / "f1_shares.csv", encoding="utf-8-sig")
risk = (st["A330"] + st["A318"]) / st["A900"] * 100

s = {"total_1997": st.A900.iloc[0], "total_2026": st.A900.iloc[-1], "deposit_2026": st.A100.iloc[-1], "deposit_share_1997": share["現金・預金"].iloc[0], "deposit_share_2026": share["現金・預金"].iloc[-1],
     "risk_share_1997": risk.iloc[0], "risk_share_2026": risk.iloc[-1], "risk_share_min_q": str(risk.idxmin()), "risk_share_min": risk.min()}
pd.Series(s).to_csv(RES / "f1_summary.csv", header=["value"]); print(pd.Series(s))

note = "\n（家計。残高の前期差 ＝ フロー（取引）＋ 調整（時価の変動など）。四半期、兆円）"
fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
for ax, (lab, sub) in zip(axes, d.groupby("period", sort=False)):
    sub = sub[sub.item.isin([ITEMS[i] for i in main])].set_index("item")
    y = np.arange(len(sub))
    ax.barh(y - 0.2, sub.flow, height=0.38, color=BLUE, label="フロー（買い越し・預け入れ）")
    ax.barh(y + 0.2, sub.adj, height=0.38, color=ORANGE, label="調整（値上がりなど）")
    ax.set_yticks(y); ax.set_yticklabels(sub.index, fontsize=9); ax.axvline(0, color=GRAY, lw=0.8)
    ax.set_title(lab, fontsize=11); ax.set_xlabel("兆円")
axes[0].invert_yaxis(); axes[0].legend(frameon=False, fontsize=8.5, loc="lower right")
fig.suptitle("株式は「売り越し」でも、値上がりで残高が増えた", y=1.03)
fig.text(0.01, -0.07, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "f1_decompose.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.6))
t = st.index.to_timestamp()
for it, c in [("A330", BLUE), ("A318", GREEN)]:
    ax.plot(t, fl[it].loc[:].cumsum(), color=c, lw=1.4, ls="--", label=f"{ITEMS[it]}：フローの累計")
    ax.plot(t, adj[it].cumsum(), color=c, lw=2, label=f"{ITEMS[it]}：調整の累計")
ax.axhline(0, color=GRAY, lw=0.8); ax.set_ylabel("1998年1〜3月からの累計（兆円）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("株式等は売り越しが続き、投資信託は2024年から買いが急増")
fig.text(0.01, -0.06, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "f1_cumulative.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.4))
cols = {"現金・預金": GRAY, "保険・年金・定型保証": PURPLE, "株式等": BLUE, "投資信託": GREEN, "債務証券": ORANGE}
ax.stackplot(t, [share[k] for k in cols], colors=list(cols.values()), labels=list(cols), alpha=0.85)
ax.set_ylim(0, 100); ax.set_ylabel("金融資産に占める割合（%）"); ax.legend(frameon=False, fontsize=8.5, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.08))
ax.set_title(f"株式等＋投資信託の割合は{s['risk_share_1997']:.0f}%→{s['risk_share_2026']:.0f}%、現金・預金は{s['deposit_share_1997']:.0f}%→{s['deposit_share_2026']:.0f}%")
fig.text(0.01, -0.14, SOURCE + "\n（残りはその他の資産。1997年末〜2026年6月末）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "f1_shares.png"); plt.close(fig)
