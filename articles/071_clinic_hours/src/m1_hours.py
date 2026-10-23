"""診療所はいつ開いているか：土曜・日曜・祝日・夜（19時以降）・朝（8時半まで）の診療の割合を、診療科・地域・都道府県で比べる"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x, h = facilities("clinic")
WD = ["月", "火", "水", "木", "金"]


def flags(g):
    """行（診療科×時間帯）を施設（または施設×診療科）ごとにまとめる"""
    o = pd.DataFrame(index=g.index)
    for d in DAYS: o[d] = g[f"{d}_s"].notna() & g[f"{d}_e"].notna()
    o["eve"] = pd.concat([(g[f"{d}_e"] >= 19 * 60) & o[d] for d in WD], axis=1).any(axis=1)
    o["morn"] = pd.concat([(g[f"{d}_s"] <= 8 * 60 + 30) & o[d] for d in WD], axis=1).any(axis=1)
    o["any"] = o[DAYS].any(axis=1)
    return o


F = flags(h); F["ID"] = h.ID; F["sp"] = h["診療科目名"]
C = F.groupby("ID")[DAYS + ["eve", "morn", "any"]].max()
C["wdays"] = C[WD].sum(axis=1)
C = x.set_index("ID").join(C, how="inner")
C = C[C["any"]]
sp_n = h.groupby("ID")["診療科目名"].nunique()
C["n_sp"] = sp_n.reindex(C.index).fillna(0)
print("診療所", len(x), "時間データあり", len(C))
tot = C[["土", "日", "祝", "eve", "morn"]].mean() * 100
tot.to_csv(RES / "m1_overall.csv", encoding="utf-8-sig"); print(tot.round(1))

# 診療科別（その診療科の診療時間で判定）
SPS = ["内科", "小児科", "皮膚科", "眼科", "耳鼻いんこう科", "整形外科", "消化器内科", "循環器内科", "精神科", "心療内科", "泌尿器科", "産婦人科", "婦人科", "美容皮膚科"]
S = F[F.sp.isin(SPS)].groupby(["ID", "sp"])[["土", "日", "祝", "eve", "morn", "any"]].max().reset_index()
S = S[S["any"]]
bysp = S.groupby("sp").agg(n=("ID", "size"), 土=("土", "mean"), 日=("日", "mean"), 祝=("祝", "mean"), eve=("eve", "mean"), morn=("morn", "mean"))
bysp[["土", "日", "祝", "eve", "morn"]] *= 100
bysp = bysp.loc[SPS]; bysp.to_csv(RES / "m1_by_specialty.csv", encoding="utf-8-sig"); print(bysp.round(1))

bym = C.groupby("mtype")[["土", "日", "祝", "eve", "morn"]].mean() * 100; bym["n"] = C.groupby("mtype").size()
bym.to_csv(RES / "m1_by_area.csv", encoding="utf-8-sig"); print(bym.round(1))
byp = C.groupby("pref")[["土", "日", "eve"]].mean() * 100; byp["n"] = C.groupby("pref").size()
byp.to_csv(RES / "m1_by_pref.csv", encoding="utf-8-sig"); print(byp.sort_values("日").round(1).iloc[[0, 1, 2, -3, -2, -1]])

# ロジスティック回帰：日曜診療・夜診療 ~ 診療科（その科を掲げているか）+ 地域 + 有床 + 診療科の数
has = h[h["診療科目名"].isin(SPS)].groupby(["ID", "診療科目名"]).size().unstack(fill_value=0).gt(0).astype(float).reindex(C.index, fill_value=0)
X = pd.concat([has.add_prefix("科_"), pd.get_dummies(C.mtype, prefix="地域", dtype=float).drop(columns="地域_市"),
               (C.beds.fillna(0) > 0).astype(float).rename("有床"), np.log1p(C.n_sp).rename("log診療科数")], axis=1)
X = sm.add_constant(X)
ors = []
for y in ["日", "eve"]:
    m = sm.Logit(C[y].astype(float), X).fit(disp=0, cov_type="HC1")
    ci = m.conf_int()
    ors.append(pd.DataFrame({"y": y, "var": m.params.index, "or": np.exp(m.params.values), "lo": np.exp(ci[0].values), "hi": np.exp(ci[1].values), "p": m.pvalues.values}))
OR = pd.concat(ors); OR.to_csv(RES / "m1_logit_or.csv", index=False, encoding="utf-8-sig"); print(OR[OR["var"] != "const"].round(3).to_string())

# 図1：診療科別
lab = {"耳鼻いんこう科": "耳鼻咽喉科"}
fig, axes = plt.subplots(1, 3, figsize=(11.5, 5.2), sharey=True)
order = bysp.sort_values("土").index
yy = np.arange(len(order))
for ax, (col, t, c) in zip(axes, [("土", "土曜日に診療", BLUE), ("日", "日曜日に診療", ORANGE), ("eve", "平日19時以降も診療", PURPLE)]):
    v = bysp.loc[order, col]
    ax.barh(yy, v, color=c)
    for i, val in enumerate(v): ax.text(val + 1, i, f"{val:.0f}%", va="center", fontsize=8.5)
    ax.set_title(t, loc="left", fontsize=11.5); ax.set_xlim(0, 100); ax.axvline(tot[col], color=INK, lw=.8, ls=":")
axes[0].set_yticks(yy); axes[0].set_yticklabels([f"{lab.get(s, s)}（{bysp.loc[s, 'n']:,}）" for s in order], fontsize=9.5)
fig.suptitle("診療科ごとの「開いている」割合（その科を掲げる診療所のうち、点線は診療所全体）", x=.02, y=1.02, ha="left", fontsize=12.5)
note(axes[0], SOURCE + "\nかっこ内は診療所数。毎週かどうかは問わず、その曜日の診療時間が登録されていれば「診療」とした", -0.1)
fig.savefig(FIG / "m1_specialty.png"); plt.close(fig)

# 図2：地域の種類別
fig, ax = plt.subplots(figsize=(8.4, 3.8))
cols = [("土", "土曜"), ("日", "日曜"), ("祝", "祝日"), ("eve", "平日19時以降"), ("morn", "平日8時半まで")]
mt = ["特別区・政令市", "市", "町村"]; mc = {"特別区・政令市": BLUE, "市": GREEN, "町村": ORANGE}
for j, m_ in enumerate(mt):
    xs = np.arange(len(cols)) + (j - 1) * .26
    v = [bym.loc[m_, c] for c, _ in cols]
    ax.bar(xs, v, .25, color=mc[m_], label=f"{m_}（{bym.loc[m_, 'n']:,}）")
    for xx, vv in zip(xs, v): ax.text(xx, vv + 1, f"{vv:.0f}", ha="center", fontsize=8)
ax.set_xticks(range(len(cols))); ax.set_xticklabels([t for _, t in cols]); ax.set_ylabel("診療所の割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("所在地の種類別：その時間に診療している診療所の割合", loc="left", fontsize=12)
note(ax, SOURCE, -0.13); fig.savefig(FIG / "m1_area.png"); plt.close(fig)

# 図3：都道府県別の日曜・夜
fig, axes = plt.subplots(1, 2, figsize=(10.5, 8.6), sharey=False)
for ax, (col, t, c) in zip(axes, [("日", "日曜日に診療（%）", ORANGE), ("eve", "平日19時以降も診療（%）", PURPLE)]):
    s = byp[col].sort_values()
    ax.barh(range(47), s, color=[c if p != "東京都" else INK for p in s.index], height=.75)
    ax.set_yticks(range(47)); ax.set_yticklabels(s.index, fontsize=7.5); ax.axvline(tot[col], color=GRAY, ls=":", lw=1)
    ax.set_title(t, loc="left", fontsize=11.5)
fig.suptitle("都道府県別：日曜・夜に開いている診療所の割合（点線は全国）", x=.02, y=1.0, ha="left", fontsize=12.5)
note(axes[0], SOURCE, -0.05); fig.savefig(FIG / "m1_pref.png"); plt.close(fig)

# 夜の線の引き方を変えた場合（平日のどれかの日の終了時刻の最遅で判定）
last = pd.concat([h[f"{d}_e"].where(h[f"{d}_s"].notna()) for d in WD], axis=1).max(axis=1).groupby(h.ID).max()
Z = C.join(last.rename("last_end"))
th = pd.DataFrame({f"{t:g}時以降": Z.groupby("pref").last_end.apply(lambda s: (s >= t * 60).mean() * 100) for t in (18, 18.5, 19, 19.5, 20)})
th.loc["全国"] = [(Z.last_end >= t * 60).mean() * 100 for t in (18, 18.5, 19, 19.5, 20)]
th.to_csv(RES / "m1_evening_thresholds.csv", encoding="utf-8-sig"); print(th.loc[["京都府", "大阪府", "東京都", "全国"]].round(1))
