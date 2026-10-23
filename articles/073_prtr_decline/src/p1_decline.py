"""P1：届け出された排出量はどれだけ減ったか。物質・業種別と、「届出をやめた事業所／新しく届け出た事業所／続けて届け出た事業所の削減」への分解"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

F, S = load()
# 24年すべてで届け出がある物質（名前で一致）＝物質リストの改正（FY2010・FY2023）の影響を除いた比較用
yrs = sorted(S.fy.unique())
cnt = S.groupby("sub").fy.nunique()
CONST = sorted(cnt[cnt == len(yrs)].index)
pd.Series(CONST, name="sub").to_csv(RES / "p1_constant_substances.csv", index=False, encoding="utf-8-sig")
S["const"] = S["sub"].isin(CONST)
S = S.merge(F[["fy", "rid", "fid", "ind", "pref", "emp"]], on=["fy", "rid"], how="left")
print("一定物質数", len(CONST))

tot = S.groupby("fy").agg(all_release=("release", "sum"), const_release=("release", "sum"))
tot["const_release"] = S[S.const].groupby("fy").release.sum()
tot["air"] = S[S.const].groupby("fy").air.sum(); tot["water"] = S[S.const].groupby("fy").water.sum()
tot["landfill"] = S[S.const].groupby("fy").landfill.sum(); tot["soil"] = S[S.const].groupby("fy").soil.sum()
tot["n_fac"] = F.groupby("fy").size()
tot = tot / np.r_[[1e6] * 7, [1]].reshape(1, -1) if False else tot
for c in ["all_release", "const_release", "air", "water", "landfill", "soil"]: tot[c] = tot[c] / 1e6  # 千トン
tot.to_csv(RES / "p1_totals.csv", encoding="utf-8-sig"); print(tot.round(1))

# 物質別（一定物質）
sub = S[S.const].groupby(["sub", "fy"]).release.sum().unstack() / 1e3  # トン
top = sub[2001].sort_values(ascending=False).head(10).index
sb = pd.DataFrame({"2001": sub.loc[top, 2001], "2003": sub.loc[top, 2003], "2024": sub.loc[top, 2024]})
sb["chg_01_24"] = (sb["2024"] / sb["2001"] - 1) * 100
sb.to_csv(RES / "p1_by_substance.csv", encoding="utf-8-sig"); print(sb.round(0))

# 業種別（一定物質、主たる業種）
ind = S[S.const].groupby(["ind", "fy"]).release.sum().unstack() / 1e3
topi = ind[2001].sort_values(ascending=False).head(10).index
ib = pd.DataFrame({"2001": ind.loc[topi, 2001], "2024": ind.loc[topi, 2024]}); ib["chg"] = (ib["2024"] / ib["2001"] - 1) * 100
ib.to_csv(RES / "p1_by_industry.csv", encoding="utf-8-sig"); print(ib.round(0))

# 分解：common.link() でつないだ通しの事業所番号 fid を使う
K = S[S.const].groupby(["fy", "fid"]).release.sum() / 1e6  # 千トン


def decomp(a, b):
    x = K.loc[a]; y = K.loc[b]
    common = x.index.intersection(y.index)
    return {"from": a, "to": b, "start": x.sum(), "end": y.sum(), "exit": -x.drop(common).sum(), "entry": y.drop(common).sum(),
            "continuing": y[common].sum() - x[common].sum(), "n_start": len(x), "n_common": len(common), "n_exit": len(x) - len(common), "n_entry": len(y) - len(common)}


D = pd.DataFrame([decomp(2001, 2024), decomp(2003, 2024)])
chain = pd.DataFrame([decomp(a, a + 1) for a in yrs[:-1]])
ch = chain[chain["from"] >= 2003][["exit", "entry", "continuing"]].sum()
D = pd.concat([D, pd.DataFrame([{"from": 2003, "to": 2024, "start": K.loc[2003].sum(), "end": K.loc[2024].sum(), "exit": ch.exit, "entry": ch.entry, "continuing": ch.continuing, "n_start": np.nan}])], ignore_index=True)
D["method"] = ["2時点", "2時点", "毎年つなぐ"]
D.to_csv(RES / "p1_decomposition.csv", index=False, encoding="utf-8-sig"); chain.to_csv(RES / "p1_decomp_chain.csv", index=False, encoding="utf-8-sig")
print(D.round(2).to_string())

# 図1：総量
fig, ax = plt.subplots(figsize=(8.4, 4.2))
ax.plot(tot.index, tot.all_release, "o-", color=GRAY, lw=1.6, ms=3.5, label="届け出られたすべての物質")
ax.plot(tot.index, tot.const_release, "o-", color=BLUE, lw=2.2, ms=4, label=f"24年続けて対象の{len(CONST)}物質")
for x in (2010, 2023): ax.axvline(x - .5, color=GRAY, ls=":", lw=1)
ax.text(2009.6, ax.get_ylim()[1] * .97 if False else 300, "対象物質の\n見直し", fontsize=8.5, color=GRAY, ha="right", va="top")
ax.text(2022.6, 300, "対象物質の\n見直し", fontsize=8.5, color=GRAY, ha="right", va="top")
for x in (2001, 2003, 2024):
    v = tot.const_release[x]; ax.text(x, v - 14, f"{v:.0f}", ha="center", fontsize=9, color=BLUE)
ax.set_ylim(0, None); ax.set_ylabel("排出量（千トン／年）"); ax.set_xlabel("年度"); ax.legend(frameon=False, loc="lower left")
ax.set_title("届け出られた化学物質の排出量（大気・水域・土壌・埋立の合計）", loc="left", fontsize=12)
note(ax, SOURCE + "\nダイオキシン類（単位が違う）は除く", -0.14); fig.savefig(FIG / "p1_totals.png"); plt.close(fig)

# 図2：物質別
fig, ax = plt.subplots(figsize=(8.4, 4.6))
o = sb.sort_values("2001")
y = np.arange(len(o))
ax.barh(y + .2, o["2001"] / 1e3, .38, color=LIGHT, label="2001年度"); ax.barh(y - .2, o["2024"] / 1e3, .38, color=BLUE, label="2024年度")
for i, (v, w, c) in enumerate(zip(o["2001"], o["2024"], o.chg_01_24)): ax.text(max(v, w) / 1e3 + 1, i, f"{c:+.0f}%", va="center", fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels(o.index, fontsize=9); ax.set_xlabel("排出量（千トン／年）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("2001年度に排出量が多かった10物質の変化", loc="left", fontsize=12); note(ax, SOURCE, -0.15)
fig.savefig(FIG / "p1_substances.png"); plt.close(fig)

# 図3：分解（2003→2024 2時点と毎年つなぐ）
fig, ax = plt.subplots(figsize=(8.4, 4))
labs = ["届出をやめた\n事業所の分", "新しく届け出た\n事業所の分", "続けて届け出た\n事業所の増減"]
for j, (row, col, nm) in enumerate([(D.iloc[1], BLUE, "2003→2024年度を直接比べる"), (D.iloc[2], ORANGE, "1年ずつつないで足し合わせる")]):
    v = [row.exit, row.entry, row.continuing]
    ax.bar(np.arange(3) + (j - .5) * .38, v, .36, color=col, label=nm)
    for i, vv in enumerate(v): ax.text(i + (j - .5) * .38, vv + (2 if vv >= 0 else -6), f"{vv:+.0f}", ha="center", fontsize=9)
ax.axhline(0, color=INK, lw=.6); ax.set_xticks(range(3)); ax.set_xticklabels(labs); ax.set_ylabel("排出量の変化（千トン）"); ax.legend(frameon=False, loc="lower left", fontsize=9)
ax.set_title(f"減った{D.iloc[1].start - D.iloc[1].end:.0f}千トンの内訳（{len(CONST)}物質、2003→2024年度）", loc="left", fontsize=12)
note(ax, SOURCE + "\n事業所は隣り合う年度で「所在地」か「事業所名＋市区町村」が同じならつないだ（移転と改名が同時だと別の事業所になる）", -0.2)
fig.savefig(FIG / "p1_decomposition.png"); plt.close(fig)
