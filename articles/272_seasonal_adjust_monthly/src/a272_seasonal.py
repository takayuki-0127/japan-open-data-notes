"""272 季節調整を、業務の月次データにどう当てるか
① 本物の月次（商業動態統計の6業態）で、前月比・前年同月比・季節調整後の前月比（STL）の読み方の違いと、最新月の季節調整値がどれだけ書き換わるかを測る
② 正解の分かる架空の月次（ある月から売上が5%上がる）で、3つの見方がその変化をいつ・どれだけ見つけるかを比べる"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save, SOURCE


def sa(y, robust=True, seasonal=7):
    """STL（周期12。既定は外れ値に強い設定、季節の窓7年）で季節成分を除いた値。y は対数"""
    return y - STL(y, period=12, robust=robust, seasonal=seasonal).fit().seasonal


# ===== ① 本物の月次
d = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"])
real = {}
rev_rows = []
for g, s in d.groupby("gyotai"):
    y = np.log(s.set_index("ym").sales.astype(float))
    full = sa(y.values)
    mom_raw = np.diff(y.values) * 100
    mom_sa = np.diff(full) * 100
    yoy = (y.values[12:] - y.values[:-12]) * 100
    sign_diff = float((np.sign(mom_raw) != np.sign(mom_sa)).mean())
    share_season = float(np.mean(np.abs(mom_raw - mom_sa) > np.abs(mom_sa)))   # 季節の分が、季節を除いた動きより大きい月
    # 最新月の改訂：2019年1月〜2025年8月の各月 t で、t までのデータで STL → t の季節調整後前月比（その時点の値）と、全期間で推定した値（いまの値）
    idx = y.index
    for t in range(np.where(idx == "2019-01-01")[0][0], len(y) - 12):
        part = sa(y.values[: t + 1])
        rev_rows.append(dict(gyotai=g, ym=idx[t], first=(part[t] - part[t - 1]) * 100, final=mom_sa[t - 1],
                             raw=mom_raw[t - 1]))
    real[g] = dict(months=len(y), sign_diff_raw_vs_sa=sign_diff, season_bigger=share_season,
                   sd_mom_raw=float(np.std(mom_raw)), sd_mom_sa=float(np.std(mom_sa)), sd_yoy=float(np.std(yoy)))
rev = pd.DataFrame(rev_rows)
rev["abs_rev"] = (rev["first"] - rev["final"]).abs()
rev["flip"] = np.sign(rev["first"]) != np.sign(rev["final"])
rev.to_csv(RES / "revisions.csv", index=False, float_format="%.5g")
rv = rev.groupby("gyotai").agg(mean_abs_rev=("abs_rev", "mean"), sd_final=("final", "std"), flip=("flip", "mean"))
rv["rev_over_sd"] = rv.mean_abs_rev / rv.sd_final
for g in real:
    real[g].update({k: float(v) for k, v in rv.loc[g].items()})

# ===== ② 正解の分かる架空の月次
rng = np.random.default_rng(272)
T, SHIFT_AT, SHIFT, NSIM = 84, 60, np.log(1.05), 1000          # 7年分。61か月目（0始まりで60）から5%上がる
season = np.log(np.array([0.92, 0.88, 1.02, 0.98, 1.00, 0.96, 1.04, 1.06, 0.97, 1.00, 1.01, 1.16]))
season -= season.mean()


def make(shift, r=None):
    r = rng if r is None else r
    tr = np.cumsum(r.normal(0.002, 0.004, T))                 # ゆっくり動く基調（月0.2%増が平均）
    noise = r.normal(0, 0.012, T)                              # 月ごとのぶれ 1.2%
    step = np.where(np.arange(T) >= SHIFT_AT, shift, 0.0)      # 61か月目から5%上がる（変化なしの系列は0）
    return 4.6 + tr + np.tile(season, T // 12) + noise + step


def z_at(y, t):
    """t 月の時点で見られる3つの数字が、その系列の直前36か月のふだんの値から何標準偏差ずれているか
    前月比・前年同月比はそのまま、季節調整後の前月比は t までのデータで STL をかけ直したもの"""
    mom = np.diff(y[: t + 1]) * 100
    yoy = (y[12: t + 1] - y[: t + 1 - 12]) * 100
    yoyd = np.diff(yoy)                                        # 前年同月比の、前の月からの変化
    p = sa(y[: t + 1]); sam = np.diff(p) * 100
    sa3 = (p[3:] - p[:-3]) * 100                               # 季節調整後の3か月の変化
    pn = sa(y[: t + 1], robust=False); samn = np.diff(pn) * 100
    out = {}
    for k, v in (("mom", mom), ("yoy", yoy), ("yoyd", yoyd), ("sa", sam), ("sa3", sa3), ("sa_nr", samn)):
        hist = v[-37:-1]
        out[k] = (v[-1] - np.median(hist)) / np.std(hist)
        out[k + "_val"] = v[-1]
    return out


def shown(y, t, seasonal):
    """季節調整値に、上がった分がどれだけ出ているか：直近3か月の平均 − その前3か月の平均（%）"""
    p = sa(y[: t + 1], seasonal=seasonal)
    return (p[t - 2: t + 1].mean() - p[t - 5: t - 2].mean()) * 100


rows, shw = [], []
for k in range(NSIM):
    for lab, sh in (("shift", SHIFT), ("none", 0.0)):
        y = make(sh)
        for t in (SHIFT_AT, SHIFT_AT + 2, SHIFT_AT + 12):
            rows.append(dict(sim=k, kind=lab, t=t + 1, **z_at(y, t)))
        if k < 300:   # 上がった分の見え方（3か月後にその時点で見る／2年後に全期間で見直す）。季節の窓7年と13年
            for w in (7, 13):
                pf = sa(y, seasonal=w)   # 全84か月で推定し直した季節調整値
                shw.append(dict(sim=k, kind=lab, window=w, realtime=shown(y, SHIFT_AT + 2, w),
                                final=(pf[SHIFT_AT: SHIFT_AT + 3].mean() - pf[SHIFT_AT - 3: SHIFT_AT].mean()) * 100))
sim = pd.DataFrame(rows)
sim.to_csv(RES / "sim.csv", index=False, float_format="%.5g")
res2 = {}
for col in ("mom", "yoy", "yoyd", "sa", "sa3", "sa_nr"):
    for t in (SHIFT_AT + 1, SHIFT_AT + 3, SHIFT_AT + 13):
        for kind in ("shift", "none"):
            z = sim[(sim.kind == kind) & (sim.t == t)][col]
            res2[f"{col}_m{t}_{kind}"] = dict(up=float((z > 2).mean()), down=float((z < -2).mean()), median_z=float(z.median()))
sh = pd.DataFrame(shw); sh.to_csv(RES / "shown.csv", index=False, float_format="%.5g")
shown_res = {}
for w in (7, 13):
    a = sh[sh.window == w]
    for c in ("realtime", "final"):
        shown_res[f"w{w}_{c}"] = float((a[a.kind == "shift"][c].median() - a[a.kind == "none"][c].median()) / (SHIFT * 100))
res2["shown_share"] = shown_res
out = dict(real=real, sim=res2, sim_setup=dict(T=T, shift_month=SHIFT_AT + 1, shift_pct=5, nsim=NSIM,
                                                noise_sd_pct=1.2, trend_sd_pct=0.4))
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))


# ===== 図1：スーパーの直近3年。前月比（原数値）・季節調整後の前月比・前年同月比
g = "スーパー"
y = np.log(d[d.gyotai == g].set_index("ym").sales.astype(float))
p = sa(y.values)
df = pd.DataFrame(dict(raw=np.r_[np.nan, np.diff(y.values) * 100], sa=np.r_[np.nan, np.diff(p) * 100],
                       yoy=np.r_[[np.nan] * 12, (y.values[12:] - y.values[:-12]) * 100]), index=y.index).iloc[-36:]
fig, ax = plt.subplots(figsize=(10, 3.8))
x = np.arange(len(df))
diff = np.sign(df.raw) != np.sign(df.sa)
ax.bar(x, df.raw, color=[ORANGE if v else LIGHT for v in diff], width=0.75, label="前月比（原数値）。橙は季節調整後と向きが逆の月")
ax.plot(x, df.sa, color=BLUE, lw=2, marker="o", ms=3, label="季節調整後の前月比（STL）")
ax.plot(x, df.yoy, color=INK, lw=1.4, ls="--", label="前年同月比")
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xticks(x[::3]); ax.set_xticklabels([f"{t:%Y-%m}" for t in df.index[::3]], fontsize=8, rotation=0)
ax.set_ylabel("%"); ax.legend(frameon=False, fontsize=8, loc="lower left", ncol=1)
ax.set_title(f"スーパーの販売額（直近36か月）：前月比の向きが季節調整後と逆の月は {diff.mean():.0%}", loc="left")
save(fig, "a272_reading.png")

# ===== 図2：6業態の「向きが逆」と「最新月の改訂」
R = pd.DataFrame(real).T
order = R.sort_values("flip").index
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
for ax, col, ttl, c in [(axs[0], "sign_diff_raw_vs_sa", "前月比の向きが、原数値と季節調整後で逆の月\n（2014年2月〜2026年8月）", ORANGE),
                        (axs[1], "flip", "最新月の季節調整後の前月比の向きが、\nあとで推定し直すと逆になった月（2019〜2025年）", BLUE)]:
    v = R.loc[order, col].astype(float)
    ax.barh(range(len(v)), v, color=c); ax.set_yticks(range(len(v))); ax.set_yticklabels(order)
    for i, vv in enumerate(v): ax.text(vv, i, f" {vv:.0%}", va="center", fontsize=9)
    ax.set_title(ttl, loc="left", fontsize=10); ax.set_xticks([]); ax.set_xlim(0, 0.7)
fig.suptitle("6業態の月次で測る：原数値の前月比の読み違いと、季節調整値の書き換わり", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(top=0.72, wspace=0.1)
save(fig, "a272_real.png")

# ===== 図3：架空の月次（61か月目から5%上がる）で、3つの見方は何を言うか
S = res2
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw=dict(width_ratios=[1.25, 1]))
y = make(SHIFT, np.random.default_rng(7))
t3 = SHIFT_AT + 2
rt = sa(y[: t3 + 1]); fin = sa(y)
xx = np.arange(1, T + 1)
ax = axs[0]
ax.plot(xx, np.exp(y), color=GRAY, lw=1, label="原数値")
ax.plot(xx, np.exp(fin), color=BLUE, lw=1.8, label="季節調整値（84か月で推定し直した）")
ax.plot(xx[: t3 + 1], np.exp(rt), color=ORANGE, lw=1.8, label="季節調整値（63か月目の時点）")
ax.axvline(SHIFT_AT + 1, color=INK, lw=0.8, ls=":"); ax.text(SHIFT_AT + 1.5, ax.get_ylim()[1] * 0.995, "61か月目から\n5%上がる", fontsize=8, va="top")
ax.set_xlim(40, T); ax.legend(frameon=False, fontsize=8, loc="lower right"); ax.set_xlabel("か月目"); ax.set_title("架空の月次の1本（例）", loc="left", fontsize=11)
ax = axs[1]
items = [("前年同月比が\n前の月から跳ねた", S["yoyd_m61_shift"]["up"], S["yoyd_m73_shift"]["down"]),
         ("季節調整後の\n前月比（最新月）", S["sa_m61_shift"]["up"], S["sa_m73_shift"]["down"])]
xs = np.arange(len(items))
ax.bar(xs - 0.18, [a for _, a, _ in items], 0.34, color=BLUE, label="上がった月に「上」と読めた")
ax.bar(xs + 0.18, [b for _, _, b in items], 0.34, color=ORANGE, label="1年後に「下がった」と誤読")
for i, (_, a, b) in enumerate(items):
    ax.text(i - 0.18, a, f"{a:.0%}", ha="center", va="bottom", fontsize=9); ax.text(i + 0.18, b, f"{b:.0%}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(xs); ax.set_xticklabels([l for l, _, _ in items], fontsize=9); ax.set_yticks([]); ax.set_ylim(0, 0.7)
ax.legend(frameon=False, fontsize=8, loc="upper right")
ax.set_title("1,000本で数えた割合（直前36か月から2標準偏差）", loc="left", fontsize=10)
save(fig, "a272_sim.png", source="架空のデータ（作成者がシミュレーションで作成、seed 272）")
