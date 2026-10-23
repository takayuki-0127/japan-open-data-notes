"""S3：スマホ・ゲーム機のゲーム、スマホなどでの音楽、テレビ・パソコンでの映画鑑賞…。県ごとの「する人の割合」は、年齢構成でどこまで説明できるか（社会生活基本調査 2021年）"""
from common import *
import statsmodels.formula.api as smf

d, lab = read("SSDSE-D-2023")
d = d.rename(columns={d.columns[0]: "sex", d.columns[1]: "code", d.columns[2]: "pref"})
e, _ = read("SSDSE-E-2026")
e = e.rename(columns={e.columns[0]: "code", e.columns[1]: "pref"})
e = e[e.code.str.startswith("R")].copy()
for c in ["A1101", "A1303"]: e[c] = pd.to_numeric(e[c])
e["old"] = e.A1303 / e.A1101 * 100                        # 65歳以上の割合（2024年）
ITEMS = {"MD31": "スマホ・ゲーム機などでのゲーム", "MD08": "CD・スマホなどでの音楽鑑賞", "MD05": "テレビ・DVD・パソコンなどでの映画鑑賞",
         "MD272": "マンガを読む", "MD271": "趣味としての読書", "MD12": "カラオケ", "MD21": "園芸・ガーデニング", "MD14": "洋舞・社交ダンス"}
tot = d[(d.sex == "0_総数") & (d.code != "R00000")].merge(e[["code", "old"]], on="code")
rows = []
for c, name in ITEMS.items():
    r = smf.ols(f"{c} ~ old", tot).fit(cov_type="HC3")
    rows.append({"item": name, "code": c, "national": float(d[(d.sex == "0_総数") & (d.code == "R00000")][c].iloc[0]), "min": tot[c].min(), "max": tot[c].max(),
                 "corr_old": np.corrcoef(tot[c], tot.old)[0, 1], "slope_per_1pt_old": r.params["old"], "r2": r.rsquared})
t = pd.DataFrame(rows).sort_values("corr_old"); t.round(3).to_csv(RES / "s3_items.csv", index=False, encoding="utf-8-sig"); print(t.round(3))
# ゲーム：年齢構成から予想される値より高い・低い県
r = smf.ols("MD31 ~ old", tot).fit(); tot["game_resid"] = r.resid
tot[["pref", "MD31", "old", "game_resid"]].sort_values("game_resid").round(2).to_csv(RES / "s3_game_resid.csv", index=False, encoding="utf-8-sig")
# 男女の差（全国）
nat = d[d.code == "R00000"].set_index("sex")
gap = pd.DataFrame({"男": nat.loc["1_男", list(ITEMS)].astype(float).values, "女": nat.loc["2_女", list(ITEMS)].astype(float).values}, index=list(ITEMS.values()))
gap["差（男−女）"] = gap["男"] - gap["女"]; gap.round(1).to_csv(RES / "s3_gender.csv", encoding="utf-8-sig"); print(gap)
s = {"n_pref": len(tot), "game_national": t.set_index("code").loc["MD31", "national"], "game_corr_old": t.set_index("code").loc["MD31", "corr_old"],
     "game_r2": t.set_index("code").loc["MD31", "r2"], "game_slope": t.set_index("code").loc["MD31", "slope_per_1pt_old"],
     "game_top_resid": tot.loc[tot.game_resid.idxmax(), "pref"], "game_bottom_resid": tot.loc[tot.game_resid.idxmin(), "pref"],
     "game_max_pref": tot.loc[tot.MD31.idxmax(), "pref"], "game_max": tot.MD31.max(), "game_min_pref": tot.loc[tot.MD31.idxmin(), "pref"], "game_min": tot.MD31.min()}
pd.Series(s).to_csv(RES / "s3_summary.csv", header=["value"]); print(pd.Series(s))
SRC = "出典：独立行政法人統計センター「SSDSE-社会生活（SSDSE-D-2023）」「SSDSE-基本素材（SSDSE-E-2026）」（https://www.nstac.go.jp/use/literacy/ssdse/）をもとに作成者が加工して作成"

# 図1：ゲームと高齢化
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(tot.old, tot.MD31, color=BLUE, s=22)
for _, q in tot.iterrows():
    if q.pref in ["東京都", "沖縄県", "秋田県", "神奈川県", "愛知県", "高知県", "北海道", "滋賀県"]:
        ax.annotate(q.pref, (q.old, q.MD31), xytext=(4, 2), textcoords="offset points", fontsize=8, color="#52514e")
xs = np.linspace(tot.old.min(), tot.old.max(), 10); ax.plot(xs, r.params.Intercept + r.params.old * xs, color=GRAY, lw=1)
ax.set_xlabel("65歳以上の割合（%、2024年）"); ax.set_ylabel("1年間にゲームをした人の割合（%、10歳以上）")
ax.set_title(f"スマホ・ゲーム機のゲームをする人の割合は、高齢化と強く結びつく（相関 {s['game_corr_old']:.2f}）", loc="left")
fig.text(0.01, -0.03, SRC, fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "s3_game_old.png"); plt.close(fig)

# 図2：項目ごとの、高齢化との相関
fig, ax = plt.subplots(figsize=(8, 4)); y = np.arange(len(t))
ax.barh(y, t.corr_old, color=[ORANGE if v < 0 else BLUE for v in t.corr_old], height=0.6)
for yi, v, n in zip(y, t.corr_old, t.national):
    ax.text(max(v, 0) + 0.03, yi, f"{v:+.2f}（全国 {n:.1f}%）", va="center", ha="left", fontsize=8.5)
ax.set_yticks(y, t["item"]); ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-1.0, 1.0); ax.set_xlabel("県ごとの「した人の割合」と65歳以上の割合の相関")
ax.set_title("スマホや画面で楽しむ趣味ほど、高齢化と強く逆に動く", loc="left")
fig.text(0.01, -0.06, SRC, fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "s3_corr.png"); plt.close(fig)

# 図3：男女の差
g = gap.sort_values("差（男−女）")
fig, ax = plt.subplots(figsize=(8, 4)); y = np.arange(len(g))
ax.scatter(g["男"], y, color=BLUE, label="男", zorder=3); ax.scatter(g["女"], y, color=ORANGE, label="女", zorder=3)
ax.hlines(y, g[["男", "女"]].min(1), g[["男", "女"]].max(1), color=GRAY, lw=1.5)
ax.set_yticks(y, g.index); ax.set_xlabel("1年間にした人の割合（%、全国・10歳以上）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("ゲームとマンガは男性、園芸と読書は女性のほうが多い", loc="left")
fig.text(0.01, -0.06, SRC, fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "s3_gender.png"); plt.close(fig)
