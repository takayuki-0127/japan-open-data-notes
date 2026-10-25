"""F04 図（f01〜f05）"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from common import national, RES, GOTO, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

n = national()
bm = pd.read_csv(RES / "bsts_monthly.csv", parse_dates=["date"])
bc = pd.read_csv(RES / "bsts_cumulative.csv")
BASE = [v for v in bm.variant.unique() if v.startswith("基本")][0]
V21 = [v for v in bm.variant.unique() if "2021" in v][0]
GOTO_USED = 8781  # 万人泊：観光庁「Go To トラベル事業の利用実績」12月28日まで（参考）

# f01 実績と反実仮想
fig, ax = plt.subplots(figsize=(9.2, 4.8))
s = n.loc["2018-01":"2021-12", "japanese"] / 1e4
ax.plot(s.index, s.values, color=INK, lw=1.8, label="実績（日本人延べ宿泊者数）")
for v, c, lab in [(BASE, BLUE, "なかった場合①：2020年6月までで学習"), (V21, ORANGE, "なかった場合②：2021年も学習に加える")]:
    q = bm[bm.variant == v]
    ax.fill_between(q.date, q.cf_lo / 1e4, q.cf_hi / 1e4, color=c, alpha=.18, lw=0)
    ax.plot(q.date, q.cf_med / 1e4, color=c, lw=2, label=lab + "（95%信用区間）")
ax.axvspan(pd.Timestamp("2020-07-01"), pd.Timestamp("2020-12-31"), color=GRAY, alpha=.12, lw=0)
ax.text(pd.Timestamp("2020-07-10"), 5600, "Go To トラベル\n2020年7月22日〜12月28日", fontsize=8.5, color=INK, va="top")
ax.set_ylabel("万人泊／月"); ax.set_ylim(0, 5800); ax.legend(fontsize=8.5, loc="lower left", frameon=False)
ax.set_title("Go To の期間、実績は「なかった場合」を上回った。ただし差の大きさは学習のしかたで2倍以上ちがう", loc="left", fontsize=11.5)
save(fig, "f01_counterfactual.png")

# f02 累積の効果
cf = np.load(RES / "_base_cf.npy")
act = n.loc[GOTO, "japanese"].values
cum = np.cumsum(act[None, :] - cf, axis=1) / 1e4
fig, ax = plt.subplots(figsize=(8.4, 4.6))
x = np.arange(len(GOTO))
ax.fill_between(x, np.quantile(cum, .025, 0), np.quantile(cum, .975, 0), color=BLUE, alpha=.18, lw=0)
ax.plot(x, np.median(cum, 0), color=BLUE, lw=2.2, marker="o", label="①2020年6月までで学習（中央値と95%信用区間）")
r21 = bc[(bc.variant == V21) & (bc.period == "2020年7〜12月")].iloc[0]
ax.errorbar([5.15], [r21.eff_med / 1e4], yerr=[[(r21.eff_med - r21.eff_lo) / 1e4], [(r21.eff_hi - r21.eff_med) / 1e4]], color=ORANGE, fmt="s", capsize=4, lw=2, label="②2021年も学習に加える（12月までの合計）")
ax.axhline(GOTO_USED, color=GRAY, ls="--", lw=1.2)
ax.text(0, GOTO_USED + 250, f"参考：Go To の利用実績 約{GOTO_USED:,}万人泊（観光庁、12月28日まで）", fontsize=8.5, color=GRAY)
ax.set_xticks(x, [f"{d.month}月" for d in GOTO]); ax.set_ylabel("増えた延べ宿泊者数の累計（万人泊）")
ax.set_ylim(0, 12500); ax.legend(fontsize=8.5, frameon=False, loc="upper left", bbox_to_anchor=(0, 0.93))
ax.set_title("①の効果の合計は利用実績とほぼ同じ。「全部が上乗せ」はありえないので、①は大きめに出ている", loc="left", fontsize=11)
save(fig, "f02_cumulative.png")

# f03 県別の地図
pe = pd.read_csv(RES / "pref_effect.csv"); pe = pe[pe.pref != "全国"]
TILE = {"北海道": (12, 0), "青森": (12, 1), "秋田": (11, 2), "岩手": (12, 2), "福井": (6, 3), "石川": (7, 3), "富山": (8, 3), "新潟": (9, 3), "山形": (11, 3), "宮城": (12, 3),
        "島根": (2, 4), "鳥取": (3, 4), "兵庫": (4, 4), "京都": (5, 4), "滋賀": (6, 4), "岐阜": (7, 4), "長野": (8, 4), "群馬": (9, 4), "栃木": (10, 4), "福島": (11, 4),
        "山口": (1, 5), "広島": (2, 5), "岡山": (3, 5), "大阪": (4, 5), "奈良": (5, 5), "三重": (6, 5), "愛知": (7, 5), "山梨": (8, 5), "埼玉": (9, 5), "茨城": (10, 5),
        "佐賀": (0, 6), "福岡": (1, 6), "愛媛": (2, 6), "香川": (3, 6), "徳島": (4, 6), "和歌山": (5, 6), "静岡": (7, 6), "神奈川": (8, 6), "東京": (9, 6), "千葉": (10, 6),
        "長崎": (0, 7), "熊本": (1, 7), "大分": (2, 7), "高知": (3, 7), "鹿児島": (0, 8), "宮崎": (1, 8), "沖縄": (0, 9)}
cmap = LinearSegmentedColormap.from_list("seq", ["#f4f4f2", LIGHT, BLUE, "#123e75"])
norm = Normalize(vmin=0, vmax=200)
fig, ax = plt.subplots(figsize=(8.6, 6.4))
for _, r in pe.iterrows():
    x0, y0 = TILE[r.pref]
    ax.add_patch(plt.Rectangle((x0, -y0), 0.94, 0.94, color=cmap(norm(min(r.eff_pct_med, 200))), ec="white", lw=1.5))
    tc = "white" if r.eff_pct_med > 120 else INK
    ax.text(x0 + 0.47, -y0 + 0.62, r.pref + ("†" if r.pref == "東京" else ""), ha="center", va="center", fontsize=7.5, color=tc)
    ax.text(x0 + 0.47, -y0 + 0.28, f"+{r.eff_pct_med:.0f}", ha="center", va="center", fontsize=7.5, color=tc)
ax.set_xlim(-0.2, 13.2); ax.set_ylim(-9.2, 1.1); ax.axis("off")
sm_ = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
cb = fig.colorbar(sm_, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, shrink=0.5)
cb.set_label("2020年8〜11月：実績が「なかった場合」を何%上回ったか（①と同じ前提の簡易版）　†東京は10〜11月\n水準は前提に強く左右されるので、県どうしの大小の比較として見る", fontsize=8.5)
ax.set_title("県別：千葉・京都・奈良・北海道・東京で上乗せが大きく、茨城・福島・岡山で小さめ", loc="left", fontsize=12)
save(fig, "f03_pref_map.png")

# f04 東京の途中参加
es = pd.read_csv(RES / "did_event_study.csv")
sp = pd.read_csv(RES / "synth_tokyo_path.csv", parse_dates=["date"]).set_index("date").loc["2020"]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ax.fill_between(es.month, es.placebo_lo * 100, es.placebo_hi * 100, color=GRAY, alpha=.2, lw=0, label="他の46道府県で同じ計算をした95%の範囲")
ax.plot(es.month, es.tokyo_minus_others * 100, color=BLUE, lw=2.2, marker="o", label="東京 − 他46道府県の平均（2019年同月比の差）")
ax.plot(sp.index.month, sp.gap * 100, color=ORANGE, lw=1.8, marker="s", ms=4, label="東京 − 合成東京（合成コントロール）")
ax.axhline(0, color=INK, lw=.8)
ax.axvspan(6.5, 9.5, color=ORANGE, alpha=.08, lw=0); ax.axvspan(9.5, 11.5, color=BLUE, alpha=.08, lw=0)
ax.text(7, 52, "東京だけ対象外", fontsize=9, color=ORANGE); ax.text(9.7, 52, "東京も対象", fontsize=9, color=BLUE)
ax.set_xticks(range(1, 13), [f"{m}月" for m in range(1, 13)]); ax.set_ylabel("差（%ポイント相当、log×100）"); ax.set_ylim(-60, 80)
ax.legend(fontsize=8.5, frameon=False, loc="upper right")
ax.set_title("東京は対象外の7〜9月に他県より落ち込み、加わった10月以降に差が縮んだ", loc="left", fontsize=12)
save(fig, "f04_tokyo_did.png")

# f05 手法別の比較
dd = pd.read_csv(RES / "did_tokyo.csv").iloc[0]
ss = pd.read_csv(RES / "synth_summary.csv", index_col=0)["value"]
rows = []
lab = {BASE: "①基本（2015年〜20年6月で学習）", "学習を2011年1月から": "①' 学習を2011年から", "学習を2017年1月から": "①' 学習を2017年から",
       "共変量を陽性者数だけに": "①' 共変量を陽性者数だけ", V21: "② 2021年も学習に加える"}
for v, l in lab.items():
    r = bc[(bc.variant == v) & (bc.period == "2020年8〜11月")].iloc[0]
    rows.append((l, r.pct_med, r.pct_lo, r.pct_hi, BLUE if v != V21 else ORANGE))
rows.append(("差の差：東京の途中参加（10〜11月）", dd.pct, (np.exp(dd.delta + dd.placebo_lo) - 1) * 100 if False else None, None, GREEN))
rows.append(("合成コントロール：東京の途中参加", ss.change_pct, None, None, GREEN))
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for i, (l, m, lo, hi, c) in enumerate(rows[::-1]):
    if lo is not None:
        ax.plot([lo, hi], [i, i], color=c, lw=2.2)
    ax.plot(m, i, "o", color=c, ms=8)
    ax.text(m + 6, i + 0.18, f"{m:+.0f}%", fontsize=8.5, color=c)
# 差の差・合成コントロールはプラセボの範囲を矢印なしの帯で
for i, (val, lo, hi) in enumerate([((np.exp(ss.change) - 1) * 100, (np.exp(ss.placebo_lo) - 1) * 100, (np.exp(ss.placebo_hi) - 1) * 100),
                                   (dd.pct, (np.exp(dd.placebo_lo) - 1) * 100, (np.exp(dd.placebo_hi) - 1) * 100)]):
    ax.plot([lo, hi], [i, i], color=GREEN, lw=6, alpha=.25, solid_capstyle="butt")
ax.axvline(0, color=INK, lw=.8)
ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]], fontsize=9)
ax.set_xlabel("実績が「なかった場合」を何%上回ったか（線：95%信用区間、薄い帯：他県で同じ計算をした95%の範囲）", fontsize=8.5)
ax.set_title("全国の時系列では+35〜+210%、東京の途中参加の比較では+13〜15%", loc="left", fontsize=12)
save(fig, "f05_methods.png")
print("ok")
