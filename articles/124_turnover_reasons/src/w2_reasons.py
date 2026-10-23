"""W2：離職理由の構成は男女でどう変わったか。仕事の見つけ方（入職経路）はどう変わったか"""
from common import *

t = read_table("hyo13.xls", header_row=2)
cats = ["契約期間の満了", "事業所側の理由", "定年", "本人の責による", "個人的理由", "死亡・傷病"]
sub = ["結婚", "出産・育児", "介護・看護"]
rows = []
for sx in ["計", "男", "女"]:
    for c in cats:
        rows.append(t.loc[f"{sx}|{c}"].rename((sx, c)))
    for c in sub:
        rows.append(t.loc[f"{sx}|個人的理由|{c}"].rename((sx, "個人的理由のうち" + c)))
    rows.append(t.loc[f"{sx}|事業所側の理由|経営上の都合4)"].rename((sx, "事業所側の理由のうち経営上の都合")))
    other = t.loc[f"{sx}|個人的理由"] - t.loc[[f"{sx}|個人的理由|{c}" for c in sub]].fillna(0).sum()
    rows.append(other.rename((sx, "個人的理由のうちその他")))
    rest = 100 - t.loc[[f"{sx}|{c}" for c in cats]].sum()
    rows.append(rest.rename((sx, "その他・不詳（100−計）")))
comp = pd.DataFrame(rows).T.round(1)
comp.index.name = "年"
comp.to_csv(RES / "w2_reason_share.csv", encoding="utf-8-sig")

# 期間平均の比較
per = {"1991〜95年": range(1991, 1996), "2009〜11年": range(2009, 2012), "2017〜19年": range(2017, 2020),
       "2023〜25年": range(2023, 2026)}
pm = pd.DataFrame({k: comp.loc[list(v)].mean() for k, v in per.items()}).round(1)
pm.to_csv(RES / "w2_reason_period.csv", encoding="utf-8-sig")

# 入職経路（千人→構成比）
r7 = read_table("hyo07.xls", label_cols=(0, 1, 2))
r7.index = [i.split("|")[-1] for i in r7.index]
tot = r7.loc["入職者計"]
route = (r7.drop(index=["入職者計"]).div(tot) * 100).T
route["出向・出向先からの復帰"] = route["出向"] + route["出向先からの復帰"]
route["縁故（前の会社を除く）"] = route["縁故"] - route["うち前の会社"]
route = route.rename(columns={"うち前の会社": "前の会社"})
keep = ["広告", "縁故（前の会社を除く）", "前の会社", "職業安定所", "ハローワークインターネットサービス", "民営職業紹介所", "学校",
        "その他", "出向・出向先からの復帰"]
route = route[keep].round(1)
route.index.name = "年"
chk = (r7.drop(index=["入職者計", "うち前の会社"]).sum() - tot).abs().max()
route.to_csv(RES / "w2_route_share.csv", encoding="utf-8-sig")
r7.T.rename_axis("年").to_csv(DATA / "route_counts.csv", encoding="utf-8-sig")
comp.to_csv(DATA / "reason_share.csv", encoding="utf-8-sig")

# ---- 図 ----
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6), sharey=True)
col = {"契約期間の満了": BLUE, "事業所側の理由": ORANGE, "定年": GREEN, "本人の責による": PURPLE, "死亡・傷病": GRAY}
for ax, sx in zip(axs, ["男", "女"]):
    for c, cc in col.items():
        ax.plot(comp.index, comp[(sx, c)], color=cc, lw=1.8, label=c)
    ax.set_title(f"{sx}性：個人的理由以外の離職理由", loc="left", fontsize=12)
    ax.set_ylim(0, 20)
axs[0].set_ylabel("離職者に占める割合（％）")
axs[1].legend(frameon=False, fontsize=8.5, loc="upper right")
note(fig); fig.savefig(FIG / "w2_reasons.png"); plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6))
ax = axs[0]
for sx, cc in [("男", BLUE), ("女", ORANGE), ("計", INK)]:
    ax.plot(comp.index, comp[(sx, "個人的理由")], color=cc, lw=1.8 if sx != "計" else 1, label=sx if sx != "計" else "男女計")
ax.set_ylim(50, 90); ax.set_title("個人的理由の割合", loc="left", fontsize=12); ax.set_ylabel("％"); ax.legend(frameon=False)
ax = axs[1]
for c, cc in [("個人的理由のうち結婚", PURPLE), ("個人的理由のうち出産・育児", ORANGE), ("個人的理由のうち介護・看護", GREEN)]:
    ax.plot(comp.index, comp[("女", c)], color=cc, lw=1.8, label=c.replace("個人的理由のうち", ""))
ax.set_ylim(0, 10); ax.set_title("女性：結婚・出産育児・介護看護の割合", loc="left", fontsize=12); ax.legend(frameon=False)
note(fig); fig.savefig(FIG / "w2_personal.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.8, 4.8))
rc = {"広告": BLUE, "縁故（前の会社を除く）": PURPLE, "前の会社": LIGHT, "職業安定所": GREEN,
      "ハローワークインターネットサービス": "#8fd1b4", "民営職業紹介所": ORANGE, "学校": GRAY, "その他": INK}
for c, cc in rc.items():
    ax.plot(route.index, route[c], color=cc, lw=1.8, label=c)
ax.set_ylabel("入職者に占める割合（％）"); ax.set_ylim(0, 46)
ax.set_title("入職者が仕事を見つけた経路", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
note(fig); fig.savefig(FIG / "w2_route.png"); plt.close(fig)

print(pm.to_string())
print(comp.loc[[1991, 2005, 2009, 2019, 2020, 2024, 2025]].T.to_string())
print("経路の合計との差（千人）", chk)
print(route.loc[[1991, 2000, 2007, 2009, 2015, 2019, 2024, 2025]].T.to_string())
