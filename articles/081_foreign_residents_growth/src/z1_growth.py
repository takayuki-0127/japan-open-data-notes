"""全国の在留外国人：2012年末→2025年末の増え方（国籍・在留資格・都道府県）とシフトシェア分解"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

A = load_pref_nat()
A = A[~A.nat.isin(REGIONS)].copy(); A["nat"] = A.nat.map(nat_group)
T = load_table()
T["nat"] = T.nat.map(nat_group); T["sg"] = T.status.map(status_group)
Tp = T[T.pref.isin(PREFS)]

# 1) 総数の推移（都道府県の合計。未定・不詳を除く）
s1 = A.groupby("period").n.sum(); s2 = Tp.groupby("period").n.sum()
tot = pd.concat([s1, s2]).rename("n").reset_index(); tot.to_csv(RES / "z1_total.csv", index=False, encoding="utf-8-sig"); print(tot)
print("全国（未定・不詳を含む）2025-12:", T[T.period == "2025-12"].n.sum())

# 2) 国籍別 2012-12 → 2025-12
n12 = A[A.period == "2012-12"].groupby("nat").n.sum(); n25 = Tp[Tp.period == "2025-12"].groupby("nat").n.sum()
nat = pd.DataFrame({"2012-12": n12, "2025-12": n25}).fillna(0)
nat["増加"] = nat["2025-12"] - nat["2012-12"]; nat["倍率"] = nat["2025-12"] / nat["2012-12"]
nat = nat.sort_values("2025-12", ascending=False); nat.to_csv(RES / "z1_nationality.csv", encoding="utf-8-sig")
print(nat.head(15).round(2)); print("増加の合計", nat["増加"].sum())

# 3) 在留資格 2023-12 → 2025-12
st = Tp.groupby(["period", "sg"]).n.sum().unstack("period")
st["増加"] = st["2025-12"] - st["2023-12"]; st["増加率%"] = (st["2025-12"] / st["2023-12"] - 1) * 100
st["増加への寄与%"] = st["増加"] / st["増加"].sum() * 100
st = st.sort_values("2025-12", ascending=False); st.to_csv(RES / "z1_status.csv", encoding="utf-8-sig"); print(st.round(1))

# 4) 特定技能・技能実習の国籍
sk = Tp[Tp.sg.isin(["特定技能", "技能実習"])].groupby(["sg", "period", "nat"]).n.sum().unstack("period").fillna(0)
sk.to_csv(RES / "z1_skill_nat.csv", encoding="utf-8-sig")
for g in ["特定技能", "技能実習"]:
    x = sk.loc[g].sort_values("2025-12", ascending=False); print(g, x[["2023-12", "2025-12"]].head(8))

# 5) 都道府県：人口あたりと伸び、シフトシェア（国籍を「業種」とみなす）
p12 = pref_pop(2012); p24 = pref_pop(2024)
f12 = A[A.period == "2012-12"].groupby("pref").n.sum(); f25 = Tp[Tp.period == "2025-12"].groupby("pref").n.sum()
pr = pd.DataFrame({"外国人2012": f12, "外国人2025": f25, "人口2012": p12, "人口2024": p24}).loc[PREFS]
pr["割合2012%"] = pr["外国人2012"] / pr["人口2012"] * 100; pr["割合2025%"] = pr["外国人2025"] / pr["人口2024"] * 100
pr["倍率"] = pr["外国人2025"] / pr["外国人2012"]
# シフトシェア：主要国籍＋その他
top = list(nat.index[:12])
def g(x): return x if x in top else "その他"
a12 = A[A.period == "2012-12"].assign(k=lambda d: d.nat.map(g)).groupby(["pref", "k"]).n.sum().unstack(fill_value=0)
a25 = Tp[Tp.period == "2025-12"].assign(k=lambda d: d.nat.map(g)).groupby(["pref", "k"]).n.sum().unstack(fill_value=0)
a12, a25 = a12.reindex(index=PREFS, columns=top + ["その他"], fill_value=0), a25.reindex(index=PREFS, columns=top + ["その他"], fill_value=0)
G = a25.sum().sum() / a12.sum().sum() - 1
gk = a25.sum() / a12.sum() - 1
pr["全国の伸び分"] = a12.sum(axis=1) * G
pr["国籍構成分"] = (a12 * (gk - G)).sum(axis=1)
pr["地域固有分"] = (a25 - a12 * (1 + gk)).sum(axis=1)
pr["増加"] = a25.sum(axis=1) - a12.sum(axis=1)
pr.to_csv(RES / "z1_prefecture.csv", encoding="utf-8-sig")
print(pr.sort_values("倍率", ascending=False)[["外国人2012", "外国人2025", "倍率", "割合2012%", "割合2025%"]].round(2).head(12))
print(pr.sort_values("倍率")[["外国人2012", "外国人2025", "倍率", "割合2012%", "割合2025%"]].round(2).head(6))
print("全国の伸び G=", round(G, 3)); print((pr[["国籍構成分", "地域固有分"]].div(pr["外国人2012"], axis=0) * 100).round(1).sort_values("地域固有分").to_string())
print("相関 倍率 vs 割合2012:", np.corrcoef(np.log(pr["倍率"]), np.log(pr["割合2012%"]))[0, 1])

# --- 図1：総数と国籍
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.1))
ax = axes[0]
x1 = pd.to_datetime(s1.index + "-28"); x2 = pd.to_datetime(s2.index + "-28")
ax.plot(x1, s1 / 1e4, "o-", color=BLUE, ms=3.5, lw=2); ax.plot(x2, s2 / 1e4, "o-", color=BLUE, ms=3.5, lw=2)
ax.text(pd.Timestamp("2021-06-30"), (s1.iloc[-1] + s2.iloc[0]) / 2e4, "2020年12月〜\n2023年6月は\nデータなし", fontsize=8, color=GRAY, ha="center")
ax.set_ylabel("万人（都道府県の合計）"); ax.set_title("在留外国人の数（半年ごと）", loc="left", fontsize=11.5); ax.set_ylim(0, None)
ax = axes[1]
show = nat.head(10).iloc[::-1]
y = np.arange(len(show))
ax.barh(y - .2, show["2012-12"] / 1e4, .4, color=LIGHT, label="2012年末")
ax.barh(y + .2, show["2025-12"] / 1e4, .4, color=BLUE, label="2025年末")
for i, (a_, b_) in enumerate(zip(show["2012-12"], show["2025-12"])): ax.text(b_ / 1e4 + .5, i + .2, f"{b_ / a_:.1f}倍", va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels(show.index, fontsize=9); ax.set_xlabel("万人"); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("国籍・地域別（2025年末の多い順）", loc="left", fontsize=11.5)
note(axes[0], SOURCE, -0.14)
fig.savefig(FIG / "z1_total_nat.png"); plt.close(fig)

# --- 図2：在留資格の増加
fig, ax = plt.subplots(figsize=(8.4, 4.2))
s_ = st.sort_values("増加")
cols = [ORANGE if v > 0 else GRAY for v in s_["増加"]]
ax.barh(s_.index, s_["増加"] / 1e4, color=cols)
for i, (v, r) in enumerate(zip(s_["増加"], s_["増加率%"])): ax.text(max(v, 0) / 1e4 + .3, i, f"{v / 1e4:+.1f}万人（{r:+.0f}%）", va="center", ha="left", fontsize=8.5)
ax.axvline(0, color=INK, lw=.6); ax.set_xlabel("2023年末→2025年末の増減（万人）"); ax.set_xlim(s_["増加"].min() / 1e4 - 4, s_["増加"].max() / 1e4 + 9)
ax.set_title("この2年で、どの在留資格が増えたか", loc="left", fontsize=12)
note(ax, SOURCE + "\n技能実習は1〜3号、特定技能は1・2号の合計。身分＝日本人の配偶者等・永住者の配偶者等・定住者", -0.17)
fig.savefig(FIG / "z1_status.png"); plt.close(fig)

# --- 図3：都道府県の倍率と人口に占める割合
fig, ax = plt.subplots(figsize=(8.2, 5.2))
ax.scatter(pr["割合2012%"], pr["割合2025%"], s=np.sqrt(pr["外国人2025"]) / 2, color=BLUE, alpha=.6, edgecolor="white")
for pname, r in pr.iterrows():
    if pname in ("東京", "群馬", "愛知", "沖縄", "熊本", "北海道", "秋田", "千葉", "福岡", "静岡", "長野"):
        ax.annotate(pname, (r["割合2012%"], r["割合2025%"]), fontsize=8.5, xytext=(4, 2), textcoords="offset points")
m = max(pr["割合2025%"].max(), pr["割合2012%"].max()) * 1.05
xm = pr["割合2012%"].max() * 1.15
for k in (1, 2, 3):
    ax.plot([0, m / k], [0, m], ":", color=GRAY, lw=.8)
    xe = min(m / k, xm) * .96; ax.text(xe, xe * k, f"{k}倍", color=GRAY, fontsize=8.5, ha="right", va="bottom")
ax.set_xlim(0, xm); ax.set_ylim(0, m)
ax.set_xlabel("2012年末：人口に占める在留外国人の割合（%）"); ax.set_ylabel("2025年末：同じ割合（%）")
ax.set_title("都道府県ごとの在留外国人の割合（円の大きさ＝2025年末の人数）", loc="left", fontsize=11)
note(ax, SOURCE + "\n人口は統計センター SSDSE（2012年は SSDSE-B、2025年は2024年の人口で代用）", -0.12)
fig.savefig(FIG / "z1_pref.png"); plt.close(fig)
