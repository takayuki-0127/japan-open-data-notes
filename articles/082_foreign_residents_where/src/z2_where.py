"""在留外国人はどこに住んでいるか：市区町村の集中（2025年末）、在留資格ごとの散らばり方、年齢"""
import numpy as np, pandas as pd, openpyxl
import matplotlib.pyplot as plt
from common import *

# 1) 市区町村（2025年末の総数）
wb = openpyxl.load_workbook(next(BIG.glob("2025-12_city_*.xlsx")), read_only=True)
rows = list(wb["PVT"].iter_rows(values_only=True))
hi = next(i for i, r in enumerate(rows) if r[0] == "市区町村コード")
C = pd.DataFrame([r[:5] for r in rows[hi + 1:] if r[0] and str(r[0])[:2].isdigit()], columns=["code", "pref", "seirei", "name", "n"])
C["pref"] = C.pref.map(pref_short); C["n"] = pd.to_numeric(C.n)
print("市区町村の行数", len(C), "合計", C.n.sum())
# 政令市は市全体にまとめる（人口が市単位のため）
C["unit"] = np.where(C.seirei.notna() & (C.seirei.astype(str) != "(空白)") & ~C.seirei.astype(str).str.contains("特別区"), C.seirei.astype(str).str.split("：").str[-1], C.name)
U = C.groupby(["pref", "unit"], as_index=False).n.sum()
P = muni_pop().rename(columns={"name": "unit"})
M = U.merge(P, on=["pref", "unit"], how="left")
print("人口と結べなかった数", M["pop"].isna().sum(), M[M["pop"].isna()].head(10).to_string())
M = M.dropna(subset=["pop"]); M = M[M["pop"] > 0]
M["share%"] = M.n / M["pop"] * 100
M = M.sort_values("share%", ascending=False); M.to_csv(RES / "z2_municipal_share.csv", index=False, encoding="utf-8-sig")
print(M.head(20).round(2).to_string())
bins = [0, 1, 2, 3, 5, 10, 100]
cnt = pd.cut(M["share%"], bins, right=False).value_counts().sort_index(); print(cnt)
cnt.rename("市区町村数").to_csv(RES / "z2_share_bins.csv", encoding="utf-8-sig")
print("市区町村数", len(M), "中央値%", M["share%"].median().round(2), "全体%", (M.n.sum() / M["pop"].sum() * 100).round(2))

def lorenz(v, w=None):
    o = np.argsort(v); v = np.asarray(v)[o]
    c = np.r_[0, np.cumsum(v)] / v.sum(); return np.linspace(0, 1, len(c)), c
def gini(v):
    v = np.sort(np.asarray(v, float)); n = len(v); i = np.arange(1, n + 1)
    return (2 * (i * v).sum() / (n * v.sum())) - (n + 1) / n
# 人口に対する集中：外国人の分布と人口の分布の非類似度
D = 0.5 * np.abs(M.n / M.n.sum() - M["pop"] / M["pop"].sum()).sum()
top = M.sort_values("n", ascending=False)
k10 = top.n.head(int(len(M) * .1)).sum() / M.n.sum()
p10 = M.sort_values("pop", ascending=False)["pop"].head(int(len(M) * .1)).sum() / M["pop"].sum()
print("非類似度D", round(D, 3), "上位10%市区町村の外国人シェア", round(k10, 3), "人口の上位10%シェア", round(p10, 3))

# 2) 在留資格ごとの都道府県の散らばり（人口との非類似度、東京の割合）
T = load_table(); T = T[(T.period == "2025-12") & T.pref.isin(PREFS)].copy(); T["sg"] = T.status.map(status_group)
pp = pref_pop(2024).reindex(PREFS)
G = T.groupby(["sg", "pref"]).n.sum().unstack(fill_value=0).reindex(columns=PREFS, fill_value=0)
G.loc["総数"] = G.sum()
rows_ = []
for sgn, v in G.iterrows():
    sh = v / v.sum()
    rows_.append({"在留資格": sgn, "人数": int(v.sum()), "人口との非類似度": 0.5 * np.abs(sh - pp / pp.sum()).sum(),
                  "東京の割合%": sh["東京"] * 100, "東京・大阪・愛知・神奈川の割合%": sh[["東京", "大阪", "愛知", "神奈川"]].sum() * 100,
                  "三大都市圏以外の割合%": sh.drop(["東京", "神奈川", "埼玉", "千葉", "愛知", "岐阜", "三重", "大阪", "京都", "兵庫", "奈良"]).sum() * 100})
ST = pd.DataFrame(rows_).sort_values("人口との非類似度"); ST.to_csv(RES / "z2_status_spread.csv", index=False, encoding="utf-8-sig"); print(ST.round(3).to_string())
print("日本の人口：東京の割合%", round(pp["東京"] / pp.sum() * 100, 2), "三大都市圏以外%", round(pp.drop(["東京", "神奈川", "埼玉", "千葉", "愛知", "岐阜", "三重", "大阪", "京都", "兵庫", "奈良"]).sum() / pp.sum() * 100, 1))

# 3) 年齢
T2 = T[T.sex.isin(["男", "女"])]
age = T2.groupby(["sg", "age5"]).n.sum().unstack(fill_value=0)
def med(row):
    c = row.cumsum() / row.sum(); return float(c.index[np.argmax(c.values >= .5)])
AG = pd.DataFrame({"人数": age.sum(axis=1), "年齢の中央値（5歳階級の下限）": age.apply(med, axis=1),
                   "20〜34歳の割合%": age[[20.0, 25.0, 30.0]].sum(axis=1) / age.sum(axis=1) * 100})
tot_age = T2.groupby("age5").n.sum()
AG.loc["総数"] = [tot_age.sum(), med(tot_age), tot_age[[20.0, 25.0, 30.0]].sum() / tot_age.sum() * 100]
AG.to_csv(RES / "z2_age.csv", encoding="utf-8-sig"); print(AG.round(1))
sexr = T2.groupby(["sg", "sex"]).n.sum().unstack(); sexr["女性の割合%"] = sexr["女"] / (sexr["男"] + sexr["女"]) * 100; print(sexr.round(1))
sexr.to_csv(RES / "z2_sex.csv", encoding="utf-8-sig")
pyr = T2.groupby(["age5", "sex"]).n.sum().unstack(); pyr.to_csv(RES / "z2_pyramid.csv", encoding="utf-8-sig")

# --- 図1：市区町村の割合の分布と上位
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6), gridspec_kw={"width_ratios": [1, 1.15]})
ax = axes[0]
ax.hist(M["share%"].clip(upper=20), bins=np.arange(0, 20.5, .5), color=BLUE)
ax.axvline(M.n.sum() / M["pop"].sum() * 100, color=ORANGE, lw=1.5, ls="--"); ax.text(M.n.sum() / M["pop"].sum() * 100 + .3, ax.get_ylim()[1] * .9, "全体の割合", color=ORANGE, fontsize=9)
ax.set_xlabel("人口に占める在留外国人の割合（%、20%以上は20に）"); ax.set_ylabel("市区町村の数"); ax.set_title("市区町村ごとの割合の分布", loc="left", fontsize=11.5)
ax = axes[1]
t15 = M.head(15).iloc[::-1]
ax.barh(range(15), t15["share%"], color=ORANGE)
ax.set_yticks(range(15)); ax.set_yticklabels([f"{u}（{p}）" for u, p in zip(t15.unit, t15.pref)], fontsize=8.5)
for i, (v, n_) in enumerate(zip(t15["share%"], t15.n)): ax.text(v + .3, i, f"{v:.1f}%（{n_:,}人）", va="center", fontsize=8)
ax.set_xlim(0, t15["share%"].max() * 1.35); ax.set_xlabel("%"); ax.set_title("割合が高い15市区町村", loc="left", fontsize=11.5)
note(axes[0], SOURCE + "\n分母は2020年国勢調査の総人口（統計センター SSDSE-A）。政令市は市全体で集計", -0.15)
fig.savefig(FIG / "z2_municipal.png"); plt.close(fig)

# --- 図2：在留資格ごとの散らばり
fig, ax = plt.subplots(figsize=(8.4, 4.3))
s_ = ST.set_index("在留資格")
ax.scatter(s_["東京の割合%"], s_["三大都市圏以外の割合%"], s=np.sqrt(s_["人数"]) / 2.5, color=[ORANGE if k == "総数" else BLUE for k in s_.index], alpha=.75, edgecolor="white")
for k, r in s_.iterrows(): ax.annotate(k, (r["東京の割合%"], r["三大都市圏以外の割合%"]), fontsize=8.5, xytext=(5, -16) if k == "総数" else (5, 3), textcoords="offset points")
jp_t = pp["東京"] / pp.sum() * 100; jp_o = pp.drop(["東京", "神奈川", "埼玉", "千葉", "愛知", "岐阜", "三重", "大阪", "京都", "兵庫", "奈良"]).sum() / pp.sum() * 100
ax.scatter([jp_t], [jp_o], marker="x", color=INK, s=50); ax.annotate("日本の総人口", (jp_t, jp_o), fontsize=8.5, xytext=(5, -10), textcoords="offset points")
ax.set_xlabel("東京都に住む割合（%）"); ax.set_ylabel("三大都市圏の外に住む割合（%）")
ax.set_title("在留資格ごとの住む場所（2025年末、円の大きさ＝人数）", loc="left", fontsize=11.5)
note(ax, SOURCE + "\n三大都市圏＝東京・神奈川・埼玉・千葉・愛知・岐阜・三重・大阪・京都・兵庫・奈良", -0.14)
fig.savefig(FIG / "z2_status_spread.png"); plt.close(fig)

# --- 図3：人口ピラミッド（男女）と在留資格別の年齢中央値
fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.4), gridspec_kw={"width_ratios": [1.1, 1], "wspace": .62})
ax = axes[0]
y = pyr.index.values
ax.barh(y, -pyr["男"] / 1e4, height=4.2, color=BLUE, label="男"); ax.barh(y, pyr["女"] / 1e4, height=4.2, color=ORANGE, label="女")
ax.set_yticks(range(0, 81, 10)); ax.set_yticklabels([f"{a}歳" if a < 80 else "80歳以上" for a in range(0, 81, 10)])
xt = ax.get_xticks(); ax.set_xticks(xt); ax.set_xticklabels([f"{abs(v):.0f}" for v in xt]); ax.set_xlabel("万人"); ax.legend(frameon=False)
ax.set_title("在留外国人の年齢と男女（2025年末）", loc="left", fontsize=11.5)
ax = axes[1]
a_ = AG.drop("総数").sort_values("20〜34歳の割合%")
ax.barh(range(len(a_)), a_["20〜34歳の割合%"], color=GREEN)
ax.set_yticks(range(len(a_))); ax.set_yticklabels(a_.index, fontsize=9)
for i, v in enumerate(a_["20〜34歳の割合%"]): ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8.5)
ax.set_xlim(0, 110); ax.set_xlabel("20〜34歳の割合（%）"); ax.set_title("在留資格ごとの20〜34歳の割合", loc="left", fontsize=11.5)
note(axes[0], SOURCE, -0.14)
fig.savefig(FIG / "z2_age.png"); plt.close(fig)
