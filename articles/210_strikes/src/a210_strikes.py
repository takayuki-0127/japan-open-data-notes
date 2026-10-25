"""A210 ストライキは、いつ日本からほぼ消えたのか：半日以上の同盟罷業・作業所閉鎖の件数と労働損失日数（対数）に、折れ線（区分ごとの直線）を当てはめて変化点を探す"""
from itertools import combinations
from common import *

d = load()
y_all = d.index.values.astype(float)


def fit(y, x, k, minseg=8):
    """x（年）に対するy（対数）を、k個の変化点で区切った区分ごとの直線で当てはめる（各区間は別々の直線）。SSE最小の組を総当たりで探す"""
    n = len(x); best = (np.inf, None)
    cand = range(minseg, n - minseg + 1)
    for bps in combinations(cand, k):
        if any(b - a < minseg for a, b in zip((0,) + bps, bps + (n,))):
            continue
        sse = 0.0
        for a, b in zip((0,) + bps, bps + (n,)):
            X = np.c_[np.ones(b - a), x[a:b]]
            beta, res, *_ = np.linalg.lstsq(X, y[a:b], rcond=None)
            sse += float(((y[a:b] - X @ beta) ** 2).sum())
        if sse < best[0]:
            best = (sse, bps)
    sse, bps = best
    bic = n * np.log(sse / n) + (3 * k + 2) * np.log(n)   # 区間ごとに切片・傾き、変化点の位置
    return sse, bps, bic


def choose(fits):
    """BICが2以上下がるときだけ変化点を増やす"""
    k = 1
    for kk in (2, 3):
        if fits[kk][2] < fits[k][2] - 2:
            k = kk
    return k


def segments(y, x, bps):
    out = []
    for a, b in zip((0,) + bps, bps + (len(x),)):
        X = np.c_[np.ones(b - a), x[a:b]]
        beta = np.linalg.lstsq(X, y[a:b], rcond=None)[0]
        out.append((int(x[a]), int(x[b - 1]), beta[1], X @ beta))
    return out


out = []
def p(s): out.append(s); print(s)
S = d.strike_lockout_halfday_plus_disputes
L = d.strike_lockout_halfday_plus_lost_days
A = d.action_disputes
T = d.total_disputes
p(f"半日以上の同盟罷業・作業所閉鎖 件数: 最大{S.idxmax()}年{S.max():,} 2025年{S[2025]:,} 2024年{S[2024]:,} (最大比{S[2024]/S.max()*100:.2f}%)")
p(f"労働損失日数: 最大{L.idxmax()}年{L.max():,} 1974年{L[1974]:,} 2024年{L[2024]:,} 2025年{L[2025]:,}")
p(f"行為参加人員(半日以上): 最大{d.strike_lockout_halfday_plus_participants.idxmax()}年{d.strike_lockout_halfday_plus_participants.max():,} 2024年{d.strike_lockout_halfday_plus_participants[2024]:,}")
p(f"総争議: 最大{T.idxmax()}年{T.max():,} 2024年{T[2024]:,}  争議行為を伴う争議: 最大{A.idxmax()}年{A.max():,} 2024年{A[2024]:,}")
Sp, Lp = S.loc[1974:], L.loc[1974:]
for th in [1000, 500, 100, 50]:
    p(f"1974年以降、件数が{th}件を下回った最初の年 {Sp[Sp < th].index.min()}、以後ずっと下回るのは {Sp[Sp >= th].index.max() + 1}年から")
for th in [1e6, 1e5, 1e4]:
    p(f"1974年以降、損失日数が{th:,.0f}日を下回った最初の年 {Lp[Lp < th].index.min()}、以後ずっと下回るのは {Lp[Lp >= th].index.max() + 1}年から")
for a_, b_ in [(1974, 1980), (1980, 1990), (1990, 2000), (2000, 2010), (2010, 2020)]:
    p(f"{a_}->{b_}: 件数 {S[a_]:,}→{S[b_]:,} ({(S[b_]/S[a_]-1)*100:+.0f}%)  損失日数 {L[a_]:,}→{L[b_]:,}")
decade = d.assign(dec=(d.index // 10) * 10).groupby("dec")[["strike_lockout_halfday_plus_disputes", "strike_lockout_halfday_plus_lost_days"]].mean().round(0)
decade.to_csv(RES / "decade_means.csv")
p("10年平均（件数, 損失日数）: " + " ".join(f"{k}s:{v.iloc[0]:,.0f}/{v.iloc[1]:,.0f}" for k, v in decade.iterrows()))

res = []
for name, s in [("件数", S), ("労働損失日数", L)]:
    y = np.log10(s.values.astype(float)); x = y_all
    fits = {k: fit(y, x, k) for k in (1, 2, 3)}
    kbest = choose(fits)
    for k, (sse, bps, bic) in fits.items():
        segs = segments(y, x, bps)
        desc = " | ".join(f"{a}〜{b}年 年{(10**sl-1)*100:+.1f}%" for a, b, sl, _ in segs)
        p(f"{name} 変化点{k}個: BIC{bic:.1f} 区切り {[int(x[b]) for b in bps]} :: {desc}")
        res.append({"series": name, "k": k, "bic": round(bic, 2), "breaks": " ".join(str(int(x[b])) for b in bps), "segments": desc, "selected": k == kbest})
    p(f"{name}: BICで選んだ変化点の数 {kbest}（BICが2以上下がるときだけ増やす）")
pd.DataFrame(res).to_csv(RES / "changepoints.csv", index=False)
(RES / "summary.txt").write_text("\n".join(out), encoding="utf-8")

# 図1 件数（対数）と折れ線
def plot_seg(s, name, fname, title, ylabel):
    y = np.log10(s.values.astype(float))
    fits = {k: fit(y, y_all, k) for k in (1, 2, 3)}
    kbest = choose(fits)
    segs = segments(y, y_all, fits[kbest][1])
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(s.index, s.values, "o-", color=BLUE, ms=3, lw=1.2, label=name)
    for i, (a, b, sl, fv) in enumerate(segs):
        xs = np.arange(a, b + 1)
        ax.plot(xs, 10 ** fv, color=ORANGE, lw=2.4, label="区間ごとの直線（対数）" if i == 0 else None)
        if i > 0:
            ax.axvline(a - 0.5, color=GRAY, ls="--", lw=1)
            ax.text(a + 0.5, 0.97, f"{a}年〜", fontsize=9, color=INK, transform=ax.get_xaxis_transform(), va="top")
    ax.set_yscale("log"); ax.set_ylabel(ylabel); ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.set_ylim(top=s.max() * 4)
    ax.set_title(title)
    save(fig, fname)
    return segs

plot_seg(S, "半日以上の同盟罷業・作業所閉鎖の件数", "a210_count.png", f"ストライキ（半日以上）は1974年の{S[1974]:,}件から{S[2024]}件に", "件（対数目盛）")
plot_seg(L, "労働損失日数", "a210_lostdays.png", f"労働損失日数は1974年の{L[1974]/1e4:,.0f}万日から{L[2024]:,}日に", "日（対数目盛）")

fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.plot(d.index, T, color=INK, lw=1.8, label="総争議（話し合いだけの争議も含む）")
ax.plot(d.index, A, color=BLUE, lw=1.8, label="争議行為を伴う争議")
ax.plot(d.index, S, color=ORANGE, lw=1.8, label="半日以上の同盟罷業・作業所閉鎖")
ax.plot(d.index, d.strike_under_halfday_disputes, color=GREEN, lw=1.4, label="半日未満の同盟罷業（1963年〜）")
ax.set_ylabel("件"); ax.set_ylim(0); ax.legend(frameon=False, fontsize=9)
ax.set_title("争議行為は1974年と1981年に山があり、1986年に急減した")
save(fig, "a210_types.png")
