"""グーテンベルグ・リヒター則：検知できる下限（Mc）の推移、b値（宇津・Akiの最尤法、ブートストラップ信頼区間）、M5・M6以上の年間回数"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(0)
d = load()
d = d[d.lat.between(24, 46) & d.lon.between(122, 150) & d.mag.notna()].copy()
d["mag"] = d.mag.round(1)
DM = 0.1


def mc_maxc(m):
    """最大曲率法＋0.2"""
    v, c = np.unique(np.round(m, 1), return_counts=True)
    return round(v[np.argmax(c)] + 0.2, 1)


def bval(m, mc):
    x = m[m >= mc - 1e-9]
    return np.log10(np.e) / (x.mean() - (mc - DM / 2)), len(x)


def boot(m, mc, B=1000):
    x = m[m >= mc - 1e-9]
    bs = [np.log10(np.e) / (rng.choice(x, len(x)).mean() - (mc - DM / 2)) for _ in range(B)]
    return np.percentile(bs, [2.5, 97.5])


# 1) 年ごとの Mc（1980〜2024年）
mcy = pd.DataFrame([{"year": y, "mc": mc_maxc(g.mag.values), "n": len(g)} for y, g in d[d.y >= 1980].groupby("y")])
mcy.to_csv(RES / "e1_mc_by_year.csv", index=False, encoding="utf-8-sig"); print(mcy.to_string())

def mbs(m, start=0.5, stop=6.0, win=0.5):
    """b値の安定性で Mc を決める（Woessner & Wiemer 2005）：
    Mc から Mc+0.5 までの b の平均と、Mc での b の差が不確かさ δb 以内になる最小の Mc"""
    for mc in np.round(np.arange(start, stop, DM), 1):
        x = m[m >= mc - 1e-9]
        if len(x) < 200: break
        b, n = bval(m, mc)
        db = 2.3 * b ** 2 * np.sqrt(((x - x.mean()) ** 2).sum() / (n * (n - 1)))
        bave = np.mean([bval(m, mc + k * DM)[0] for k in range(int(win / DM) + 1)])
        if abs(bave - b) <= db: return mc
    return np.nan


# 2) Mc を変えると b値がどう変わるか（b(Mc) の曲線）
per = {"2001〜2010年": d[d.y.between(2001, 2010)], "2012〜2024年": d[d.y.between(2012, 2024)]}
curve = []
for k, g in per.items():
    m = g.mag.values
    for mc in np.round(np.arange(0.5, 6.01, 0.1), 1):
        b, n = bval(m, mc)
        if n >= 100: curve.append({"group": k, "mc": mc, "b": b, "n": n})
C = pd.DataFrame(curve); C.to_csv(RES / "e1_b_vs_mc.csv", index=False, encoding="utf-8-sig")

rows = []
def add(kind, lab, m):
    mc0 = mc_maxc(m); b0, n0 = bval(m, mc0)
    mc = mbs(m); b, n = bval(m, mc); lo, hi = boot(m, mc)
    rows.append({"kind": kind, "group": lab, "mc_maxc": mc0, "b_maxc": b0, "mc": mc, "n": n, "b": b, "lo": lo, "hi": hi})
for k, g in per.items(): add("期間", k, g.mag.values)
g0 = per["2012〜2024年"]
for lab, (a_, z) in {"0〜30km": (0, 30), "30〜70km": (30, 70), "70〜300km": (70, 300), "300km以上": (300, 800)}.items():
    add("深さ（2012〜2024年）", lab, g0[(g0.depth >= a_) & (g0.depth < z)].mag.values)
B = pd.DataFrame(rows); B.to_csv(RES / "e1_bvalues.csv", index=False, encoding="utf-8-sig"); print(B.round(3).to_string())

# 5) M5・M6以上の年間回数（1960〜2024年）
cnt = d[d.y >= 1960].groupby("y").mag.agg(m5=lambda s: (s >= 5).sum(), m6=lambda s: (s >= 6).sum(), m7=lambda s: (s >= 7).sum()).reset_index()
cnt.to_csv(RES / "e1_counts.csv", index=False, encoding="utf-8-sig")
ex = cnt[cnt.y != 2011]
print("M5 mean excl2011", ex.m5.mean(), "median", ex.m5.median(), "2011", cnt[cnt.y == 2011].m5.iloc[0], "M6 mean", ex.m6.mean(), "2011", cnt[cnt.y == 2011].m6.iloc[0])
# 10倍則：M5以上とM6以上の比
r = cnt[cnt.y != 2011][["m5", "m6"]].sum(); print("ratio m5/m6 excl2011", r.m5 / r.m6)

# 図1：Mc の推移
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(mcy.year, mcy.mc, "o-", color=BLUE, lw=2, ms=4)
ax2 = ax.twinx(); ax2.bar(mcy.year, mcy.n / 1e4, color=LIGHT, alpha=.5, zorder=0); ax2.set_ylabel("登録された地震の数（万件）", color=GRAY)
ax2.spines["top"].set_visible(False); ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
ax.set_ylabel("検知の下限 Mc（最大曲率法＋0.2）"); ax.set_title("小さな地震をどこまで数えられているか（日本周辺、1980〜2024年）", loc="left", fontsize=12)
note(ax, SOURCE + "\n北緯24〜46度・東経122〜150度。線＝その年の Mc、棒＝登録された地震の数", -0.14)
fig.savefig(FIG / "e1_mc_year.png"); plt.close(fig)

# 図2：Mc を変えたときの b値
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
ax = axes[0]
g = per["2012〜2024年"]; m = g.mag.values; bins = np.round(np.arange(-1, 8.6, .1), 1)
cum = np.array([(m >= b_ - 1e-9).sum() for b_ in bins]) / 13
ax.semilogy(bins, cum, "o", ms=3, color=BLUE, label="実際の数")
for kk, col, ls in [("maxc", ORANGE, "--"), ("mbs", INK, "-")]:
    r_ = B[(B.kind == "期間") & (B.group == "2012〜2024年")].iloc[0]
    mc_, b_ = (r_.mc_maxc, r_.b_maxc) if kk == "maxc" else (r_.mc, r_.b)
    xx = np.arange(mc_, 8.0, .1); n0 = (m >= mc_ - 1e-9).sum() / 13
    ax.semilogy(xx, n0 * 10 ** (-b_ * (xx - mc_)), ls, color=col, lw=1.5, label=f"M{mc_}以上で当てはめ b={b_:.2f}")
ax.set_xlabel("マグニチュード M"); ax.set_ylabel("M以上の地震の数（1年あたり）"); ax.set_xlim(-1, 8.3); ax.set_ylim(.05, 5e5)
ax.legend(frameon=False, fontsize=8.5); ax.set_title("規模別の回数（2012〜2024年）", loc="left", fontsize=11.5)
ax = axes[1]
for k, col in [("2001〜2010年", GRAY), ("2012〜2024年", BLUE)]:
    c = C[C.group == k]; ax.plot(c.mc, c.b, "-", color=col, lw=2, label=k)
    r_ = B[(B.kind == "期間") & (B.group == k)].iloc[0]; ax.plot(r_.mc, r_.b, "o", color=col, ms=7)
ax.axhline(1, color=GRAY, ls=":", lw=1); ax.set_xlabel("下限 Mc（これ以上の地震だけを使う）"); ax.set_ylabel("b値")
ax.legend(frameon=False, fontsize=9); ax.set_title("下限を上げるとb値はどう変わるか（点＝安定した所）", loc="left", fontsize=11.5)
note(axes[0], SOURCE, -0.15)
fig.savefig(FIG / "e1_gr.png"); plt.close(fig)

# 図3：深さ別のb値
s = B[B.kind == "深さ（2012〜2024年）"]
fig, ax = plt.subplots(figsize=(7, 3.6))
x = np.arange(len(s))
ax.errorbar(x, s.b, yerr=[s.b - s.lo, s.hi - s.b], fmt="o", color=BLUE, capsize=4, ms=7)
for i, r_ in enumerate(s.itertuples()): ax.text(i + .08, r_.b, f"{r_.b:.2f}\n(M{r_.mc}以上, {r_.n:,}件)", fontsize=8.5, va="center")
ax.axhline(1, color=GRAY, ls=":", lw=1); ax.set_ylim(0.5, 1.4); ax.set_xticks(x); ax.set_xticklabels(s.group); ax.set_xlim(-.4, len(s) - .2)
ax.set_ylabel("b値"); ax.set_xlabel("震源の深さ"); ax.set_title("深さ別のb値（2012〜2024年、ひげは95%区間）", loc="left", fontsize=12)
note(ax, SOURCE, -0.2)
fig.savefig(FIG / "e1_b_depth.png"); plt.close(fig)

# 図4：M5・M6以上の年間回数
fig, ax = plt.subplots(figsize=(8.6, 3.8))
ax.bar(cnt.y, cnt.m5, color=LIGHT, label="M5以上")
ax.bar(cnt.y, cnt.m6, color=BLUE, label="M6以上")
ax.set_yscale("log"); ax.set_ylim(3, 3000); ax.set_ylabel("回数（対数目盛）")
ax.text(2011, cnt[cnt.y == 2011].m5.iloc[0] * 1.15, f"2011年\nM5以上 {cnt[cnt.y == 2011].m5.iloc[0]:,}回", ha="center", fontsize=8.5)
ax.legend(frameon=False, loc="upper left"); ax.set_title("日本周辺で起きたM5以上・M6以上の地震の回数（1960〜2024年）", loc="left", fontsize=12)
note(ax, SOURCE, -0.13)
fig.savefig(FIG / "e1_counts.png"); plt.close(fig)
