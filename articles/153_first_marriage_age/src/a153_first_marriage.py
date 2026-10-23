"""A153 平均初婚年齢の上昇はいつ頭打ちになったか（人口動態統計 婚姻 上巻9-11表・9-12表）

手法：1970〜2025年の夫・妻の平均初婚年齢に、折れ線（区分線形、つながった線）を当てはめ、
折れ目（変化点）の年を総当たりで探す。折れ目の数（1〜3）は BIC で選ぶ。
"""
import itertools
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, save, RES, BLUE, ORANGE, GRAY, INK, LIGHT

nat = load("national_marriage_age.csv")
pref = load("pref_first_marriage_age.csv")

MIN_SEG = 5  # 折れ目どうし・端から5年以上離す


def hinge_fit(x, y, bps):
    X = [np.ones_like(x), x - x[0]] + [np.clip(x - b, 0, None) for b in bps]
    X = np.column_stack(X)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    fit = X @ beta
    return beta, fit, float(((y - fit) ** 2).sum())


def best_breaks(x, y, k):
    cand = [b for b in range(int(x[0]) + MIN_SEG, int(x[-1]) - MIN_SEG + 1)]
    best = None
    for bps in itertools.combinations(cand, k):
        if any(b2 - b1 < MIN_SEG for b1, b2 in zip(bps, bps[1:])):
            continue
        beta, fit, rss = hinge_fit(x, y, bps)
        if best is None or rss < best[2]:
            best = (bps, beta, rss, fit)
    return best


def slopes(beta):
    return np.cumsum(beta[1:])


d = nat[nat.year >= 1970].reset_index(drop=True)
x = d.year.to_numpy(float)
rows, fits = [], {}
for col, lab in [("first_h", "夫"), ("first_w", "妻")]:
    y = d[col].to_numpy(float)
    n = len(y)
    res = []
    for k in (1, 2, 3):
        bps, beta, rss, fit = best_breaks(x, y, k)
        p = 2 + k + k  # 係数 + 折れ目の位置
        bic = n * np.log(rss / n) + p * np.log(n)
        res.append((bic, k, bps, beta, rss, fit))
        rows.append({"sex": lab, "k": k, "breaks": "・".join(map(str, bps)), "bic": round(bic, 1),
                     "rss": round(rss, 3), "slopes_per10y": "/".join(f"{s*10:.2f}" for s in slopes(beta))})
    bic, k, bps, beta, rss, fit = min(res, key=lambda r: r[0])
    fits[lab] = (bps, beta, fit, k)

tab = pd.DataFrame(rows)
tab.to_csv(RES / "a153_breaks.csv", index=False)

# 期間ごとの10年あたりの上昇幅（実測値で）
def change(col, a, b):
    s = nat.set_index("year")[col]
    return s[b] - s[a]

per = [(1975, 1985), (1985, 1995), (1995, 2005), (2005, 2015), (2015, 2025)]
chg = pd.DataFrame([{"period": f"{a}→{b}", "夫": round(change("first_h", a, b), 1), "妻": round(change("first_w", a, b), 1)} for a, b in per])
chg.to_csv(RES / "a153_decade_change.csv", index=False)

# 都道府県：2003-05→2013-15 と 2013-15→2023-25 の変化（妻・夫、3年平均。2003・2004年は表にないため2005年単年）
yrs = [c for c in pref.columns if c.isdigit()]
pf = pref.copy()
for c in yrs:
    pf[c] = pd.to_numeric(pf[c], errors="coerce")
pf["a05"] = pf["2005"]
pf["a15"] = pf[["2013", "2014", "2015"]].mean(axis=1)
pf["a25"] = pf[["2023", "2024", "2025"]].mean(axis=1)
pf["d1"] = pf.a15 - pf.a05
pf["d2"] = pf.a25 - pf.a15
pr = pf[pf.pref != "全国"][["sex", "pref", "a05", "a15", "a25", "d1", "d2", "2025"]].round(2)
pr.to_csv(RES / "a153_pref_change.csv", index=False)

# ---- 図1：全国の推移と折れ線 ----
fig, ax = plt.subplots(figsize=(8.6, 5))
for col, lab, c in [("first_h", "夫", BLUE), ("first_w", "妻", ORANGE)]:
    ax.plot(nat.year, nat[col], color=c, lw=2, label=f"{lab}（実測）")
    bps, beta, fit, k = fits[lab]
    ax.plot(d.year, fit, color=c, lw=1.2, ls="--", alpha=.8)
    for b in bps:
        yv = np.interp(b, d.year, fit)
        ax.plot(b, yv, "o", color=c, ms=7, mfc="white", mew=2)
        ax.annotate(str(b), (b, yv), xytext=(0, 10 if lab == "夫" else -16), textcoords="offset points",
                    ha="center", fontsize=9, color=c)
ax.set_title("平均初婚年齢の推移と折れ目（点線は1970年以降の折れ線の当てはめ）")
ax.set_ylabel("歳"); ax.set_xlim(1945, 2027); ax.legend(frameon=False, loc="upper left")
ax.grid(axis="y", color="#eee")
save(fig, "a153_trend.png")

# ---- 図2：10年ごとの上昇幅 ----
fig, ax = plt.subplots(figsize=(8.2, 4.6))
xx = np.arange(len(chg))
ax.bar(xx - .2, chg["夫"], .4, color=BLUE, label="夫")
ax.bar(xx + .2, chg["妻"], .4, color=ORANGE, label="妻")
for i, r in chg.iterrows():
    ax.text(i - .2, r["夫"] + .03, f"{r['夫']:+.1f}", ha="center", fontsize=9)
    ax.text(i + .2, r["妻"] + .03, f"{r['妻']:+.1f}", ha="center", fontsize=9)
ax.set_xticks(xx, chg.period); ax.set_ylabel("10年間の上昇幅（歳）")
ax.axhline(0, color=INK, lw=.8)
ax.set_title("平均初婚年齢の10年ごとの上昇幅")
ax.legend(frameon=False)
save(fig, "a153_decade.png")

# ---- 図3：都道府県（妻）の前の10年と後の10年 ----
w = pr[pr.sex == "妻"].sort_values("d1")
fig, ax = plt.subplots(figsize=(7.6, 6))
ax.scatter(w.d1, w.d2, color=ORANGE, s=28, alpha=.85)
for _, r in w.iterrows():
    if r.pref in ("東京都", "北海道", "富山県", "石川県", "島根県", "沖縄県", "高知県", "奈良県", "秋田県", "福島県", "埼玉県"):
        ax.annotate(r.pref, (r.d1, r.d2), xytext=(4, 2), textcoords="offset points", fontsize=8.5)
nw = pf[(pf.pref == "全国") & (pf.sex == "妻")].iloc[0]
ax.scatter([nw.d1], [nw.d2], color=INK, s=50, marker="D", zorder=3)
ax.annotate("全国", (nw.d1, nw.d2), xytext=(5, -10), textcoords="offset points", fontsize=9)
ax.axhline(0, color=GRAY, lw=.8)
ax.set_xlabel("2005年 → 2013〜15年平均 の上昇（歳）")
ax.set_ylabel("2013〜15年平均 → 2023〜25年平均 の上昇（歳）")
ax.set_title("都道府県別 妻の平均初婚年齢：前の10年と後の10年")
save(fig, "a153_pref.png")

# ---- まとめ ----
lines = []
for lab in ("夫", "妻"):
    bps, beta, fit, k = fits[lab]
    sl = slopes(beta) * 10
    lines.append(f"{lab}: 折れ目 {bps}（BICで{k}個） 10年あたりの傾き " + " / ".join(f"{s:.2f}" for s in sl))
lines.append(chg.to_string(index=False))
for lab in ("夫", "妻"):
    t = pr[pr.sex == lab]
    lines.append(f"{lab} 都道府県 d1 中央値 {t.d1.median():.2f} 範囲 {t.d1.min():.2f}〜{t.d1.max():.2f}; d2 中央値 {t.d2.median():.2f} 範囲 {t.d2.min():.2f}〜{t.d2.max():.2f}; d2<=0.1 の県 {int((t.d2<=0.1).sum())}")
    lines.append("  d2 上位: " + ", ".join(f"{r.pref} {r.d2:+.2f}" for _, r in t.nlargest(5, 'd2').iterrows()))
    lines.append("  d2 下位: " + ", ".join(f"{r.pref} {r.d2:+.2f}" for _, r in t.nsmallest(5, 'd2').iterrows()))
    lines.append("  2025 最高: " + ", ".join(f"{r.pref} {r['2025']}" for _, r in t.nlargest(3, '2025').iterrows())
                 + " 最低: " + ", ".join(f"{r.pref} {r['2025']}" for _, r in t.nsmallest(3, '2025').iterrows()))
(RES / "a153_summary.txt").write_text("\n".join(lines) + "\n\n" + tab.to_string(index=False) + "\n", encoding="utf-8")
print("\n".join(lines)); print(tab)
