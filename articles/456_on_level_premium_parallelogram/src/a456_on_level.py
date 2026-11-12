"""456 料率を改定したあと、過去の保険料を「いまの料率」に直す近似はどれだけずれるか
架空の1年契約。契約ごとにいまの料率で計算し直した値（正解）と、
暦年の保険料に係数を掛ける近似（始期が1年に均等に散らばると置く方法）を比べる。seed 456"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 456
Y0, Y1 = 2021, 2025                      # 始期の年の範囲（2022〜2025年の暦年を見る）
N_BASE = 60000                           # 2021年に始まる契約の数
SRC = "架空の契約（作成者が乱数で作成、seed 456）"


def inception(rng, pattern, growth, n_base=N_BASE):
    """始期（年を単位にした連続の時刻）を作る。growth は年あたりの契約の増え方"""
    out = []
    for y in range(Y0, Y1 + 1):
        n = int(round(n_base * (1 + growth) ** (y - Y0)))
        if pattern == "uniform":
            u = rng.random(n)
        elif pattern == "month_start":            # 毎月1日に集まる
            u = rng.integers(0, 12, n) / 12
        elif pattern == "april":                  # 4割が4月1日、残りは均等
            u = np.where(rng.random(n) < 0.4, 3 / 12, rng.random(n))
        elif pattern == "year_end":               # 4割が10〜12月に集まる
            u = np.where(rng.random(n) < 0.4, 0.75 + 0.25 * rng.random(n), rng.random(n))
        if growth != 0:                           # 年の中でも同じ率で増える（指数）
            g = np.log(1 + growth)
            w = np.exp(g * u); keep = rng.random(n) < w / w.max()
            extra = u[keep]
            while extra.size < n:
                uu = rng.random(n) if pattern == "uniform" else u[rng.integers(0, n, n)]
                ww = np.exp(g * uu); extra = np.concatenate([extra, uu[rng.random(n) < ww / ww.max()]])
            u = extra[:n]
        out.append(y + u)
    return np.concatenate(out)


def level_at(t, changes):
    """始期 t の契約に当たる料率の水準（改定前を1とする）"""
    lv = np.ones_like(t)
    for c, r in changes:
        lv = np.where(t >= c, lv * (1 + r), lv)
    return lv


def earned_share(t, year):
    """始期 t の1年契約のうち、暦年 year に入る割合"""
    return np.clip(np.minimum(t + 1, year + 1) - np.maximum(t, year), 0, 1)


def parallelogram_factor(year, changes, grid=20001):
    """始期が均等と置いたときの、暦年 year の平均の料率水準といまの水準の比（係数）"""
    s = np.linspace(year, year + 1, grid)                 # 経過する時点
    avg = 0.0
    cur = np.prod([1 + r for _, r in changes])
    cs = [(-np.inf, 1.0)] + [(c, np.prod([1 + r for _, r in changes[:k + 1]])) for k, (c, _) in enumerate(changes)]
    for k, (c, lv) in enumerate(cs):
        c_next = cs[k + 1][0] if k + 1 < len(cs) else np.inf
        # 時点 s に経過中の契約（始期 s-1〜s）のうち、始期が [c, c_next) に入る割合
        sh = np.clip(np.minimum(s, c_next) - np.maximum(s - 1, c), 0, 1)
        avg += lv * np.trapezoid(sh, s)
    return cur / avg, avg


def monthly_factor(t, base, changes, year):
    """直し方：始期の月ごとの保険料の実績を使って、暦年 year の係数を出す（月の中は均等と置く）"""
    cur = np.prod([1 + r for _, r in changes])
    m = np.floor((t - Y0) * 12 + 1e-6).astype(int)         # 始期の月の通し番号
    wp = np.bincount(m, weights=base * level_at(t, changes))   # 月ごとの収入保険料（当時の料率）
    k = np.arange(wp.size); m0 = Y0 + k / 12               # 月の始まり
    sub = np.linspace(0, 1 / 12, 31)[None, :] + m0[:, None]   # 月の中を均等に
    lv = level_at(sub, changes); es = earned_share(sub, year)
    ep = (wp[:, None] * es).mean(axis=1)                   # その月に始まった契約の、暦年の経過保険料
    onl = (wp[:, None] / lv * cur * es).mean(axis=1)
    return onl.sum() / ep.sum()


def run(rng, pattern, growth, changes, years, n_base=N_BASE):
    t = inception(rng, pattern, growth, n_base)
    base = rng.lognormal(np.log(50000), 0.5, t.size)       # 改定前の料率での年間保険料
    lv = level_at(t, changes); cur = np.prod([1 + r for _, r in changes])
    rows = []
    for y in years:
        es = earned_share(t, y)
        ep = (base * lv * es).sum()                        # 暦年の経過保険料（当時の料率）
        true = (base * cur * es).sum()                     # 契約ごとにいまの料率で計算し直した値
        f, _ = parallelogram_factor(y, changes)
        fm = monthly_factor(t, base, changes, y)
        rows.append(dict(year=y, earned=ep, true_onlevel=true, true_factor=true / ep, approx_factor=f,
                         err_pct=(ep * f / true - 1) * 100, monthly_factor=fm, err_monthly_pct=(ep * fm / true - 1) * 100))
    return rows


def main():
    rng = np.random.default_rng(SEED)
    base_change = [(2023.5, 0.10)]                         # 2023年7月1日の始期から+10%
    pats = {"uniform": "均等", "month_start": "毎月1日に集中", "april": "4割が4月1日", "year_end": "4割が10〜12月"}
    out = []
    # A. 始期の散らばり方 × 契約の増え方
    for pat, pn in pats.items():
        for g in (-0.2, 0.0, 0.2):
            for r in run(rng, pat, g, base_change, (2022, 2023, 2024, 2025)):
                out.append(dict(block="A", pattern=pn, growth=g, change="+10%（2023年7月1日）", **r))
    # B. 改定の日
    for mth, lab in [(0, "1月1日"), (3, "4月1日"), (6, "7月1日"), (9, "10月1日")]:
        ch = [(2023 + mth / 12, 0.10)]
        for pat in ("uniform", "april"):
            for r in run(rng, pat, 0.0, ch, (2023, 2024)):
                out.append(dict(block="B", pattern=pats[pat], growth=0.0, change=f"+10%（2023年{lab}）", **r))
    # C. 改定の幅
    for rr in (0.03, 0.05, 0.10, 0.20, -0.10):
        for pat, g in (("april", 0.0), ("uniform", 0.2)):
            for r in run(rng, pat, g, [(2023.5, rr)], (2023, 2024)):
                out.append(dict(block="C", pattern=pats[pat], growth=g, change=f"{rr*100:+.0f}%（2023年7月1日）", **r))
    # D. 年2回の改定
    two = [(2023.25, 0.05), (2023.75, 0.05)]
    for pat, g in (("uniform", 0.0), ("april", 0.0), ("uniform", 0.2), ("april", 0.2), ("year_end", -0.2)):
        for r in run(rng, pat, g, two, (2023, 2024)):
            out.append(dict(block="D", pattern=pats[pat], growth=g, change="+5%を2回（2023年4月1日・10月1日）", **r))
    # E. 3年続けて改定（毎年4月1日に+5%）
    three = [(2022.25, 0.05), (2023.25, 0.05), (2024.25, 0.05)]
    for pat, g in (("uniform", 0.0), ("april", 0.0), ("uniform", 0.2), ("april", 0.2)):
        for r in run(rng, pat, g, three, (2022, 2023, 2024, 2025)):
            out.append(dict(block="E", pattern=pats[pat], growth=g, change="+5%を3年続けて（毎年4月1日）", **r))
    df = pd.DataFrame(out)
    df["lr_shift_pt"] = 65.0 / (1 + df.err_pct / 100) - 65.0          # 本当は65%の損害率がどう見えるか
    df.round(6).to_csv(RES / "onlevel_errors.csv", index=False)

    # F. 小さな契約の集まりでの振れ（始期が均等、増減なし。近似の前提どおりでも残る振れ）
    rows = []
    for n in (500, 2000, 10000, 60000):
        e = [run(rng, "uniform", 0.0, base_change, (2023,), n_base=n)[0]["err_pct"] for _ in range(200)]
        rows.append(dict(n_per_year=n, mean_err_pct=np.mean(e), sd_err_pct=np.std(e, ddof=1), p05=np.percentile(e, 5), p95=np.percentile(e, 95)))
    small = pd.DataFrame(rows); small.round(4).to_csv(RES / "small_book_noise.csv", index=False)

    # 例のデータ（1回分の一部）
    t = inception(np.random.default_rng(SEED), "april", 0.0, 2000)
    ex = pd.DataFrame({"inception": t.round(4), "base_premium": np.random.default_rng(SEED + 1).lognormal(np.log(50000), 0.5, t.size).round(0)})
    ex["rate_level"] = level_at(ex.inception.values, base_change)
    ex.head(3000).to_csv(DATA / "example_policies.csv", index=False)

    A = df[df.block == "A"]
    def g(pat, gr, y, col="err_pct"): return float(A[(A.pattern == pat) & (A.growth == gr) & (A.year == y)][col].iloc[0])
    main_js = dict(
        factor_uniform_2023=parallelogram_factor(2023, base_change)[0], factor_uniform_2024=parallelogram_factor(2024, base_change)[0],
        A_2023={f"{p}|{gr:+.1f}": round(g(p, gr, 2023), 3) for p in pats.values() for gr in (-0.2, 0.0, 0.2)},
        A_2024={f"{p}|{gr:+.1f}": round(g(p, gr, 2024), 3) for p in pats.values() for gr in (-0.2, 0.0, 0.2)},
        A_2023_monthly={f"{p}|{gr:+.1f}": round(g(p, gr, 2023, "err_monthly_pct"), 3) for p in pats.values() for gr in (-0.2, 0.0, 0.2)},
        max_abs_err_all=float(df.err_pct.abs().max()), max_abs_err_monthly=float(df.err_monthly_pct.abs().max()),
        worst=df.loc[df.err_pct.abs().idxmax(), ["block", "pattern", "growth", "change", "year", "err_pct", "lr_shift_pt"]].to_dict(),
        small=small.round(3).to_dict("records"))
    json.dump(main_js, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：始期の散らばり方と、2023年に経過する保険料のうち新しい料率の割合
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    rg = np.random.default_rng(SEED)
    s = np.linspace(2023, 2025, 241)
    for (pat, pn), col in zip(pats.items(), (BLUE, ORANGE, GREEN, GRAY)):
        t = inception(rg, pat, 0.0, 200000)
        t23 = t[(t >= 2023) & (t < 2024)]
        cnt = np.bincount(np.floor((t23 - 2023) * 12 + 1e-6).astype(int), minlength=12)[:12] * 100 / t23.size
        ax[0].step(np.arange(13), np.r_[cnt, cnt[-1]], where="post", lw=1.8, color=col, label=pn)
        sh = [((t <= x) & (t > x - 1) & (t >= 2023.5)).sum() / max(((t <= x) & (t > x - 1)).sum(), 1) * 100 for x in s]
        ax[1].plot(s, sh, color=col, lw=1.8, label=pn)
    ax[1].plot(s, np.clip(s - 2023.5, 0, 1) * 100, color=INK, lw=1, ls=":", label="近似の前提（均等）")
    ax[0].set_xticks(np.arange(0.5, 12, 1)); ax[0].set_xticklabels([f"{m}月" for m in range(1, 13)], fontsize=8)
    ax[0].set_ylabel("その月に始まる契約の割合（%）"); ax[0].set_title("始期の散らばり方（4通り）", loc="left"); ax[0].legend(fontsize=8, frameon=False)
    ax[1].axvline(2023.5, color=GRAY, lw=0.8); ax[1].text(2023.47, 50, "改定（7月1日）", fontsize=8, color=GRAY, ha="right")
    ax[1].set_xticks([2023, 2023.5, 2024, 2024.5, 2025]); ax[1].set_xticklabels(["2023年1月", "7月", "2024年1月", "7月", "2025年1月"], fontsize=8)
    ax[1].set_ylabel("その時点で有効な契約のうち、新しい料率の割合（%）"); ax[1].set_title("新しい料率への入れ替わり方", loc="left"); ax[1].legend(fontsize=8, frameon=False)
    fig.tight_layout(); save(fig, "a456_inception_patterns.png", SRC)

    # 図2：近似のずれ（2023年・2024年）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    x = np.arange(4); w = 0.26
    for j, y in enumerate((2023, 2024)):
        for k, (gr, col, lab) in enumerate(((-0.2, GRAY, "契約が年20%減る"), (0.0, BLUE, "増減なし"), (0.2, ORANGE, "契約が年20%増える"))):
            v = [g(p, gr, y) for p in pats.values()]
            b = ax[j].bar(x + (k - 1) * w, v, w, color=col, label=lab)
            for xi, vi in zip(x + (k - 1) * w, v): ax[j].text(xi, vi + (0.06 if vi >= 0 else -0.06), f"{vi:+.1f}", ha="center", va="bottom" if vi >= 0 else "top", fontsize=7.5)
        ax[j].axhline(0, color=INK, lw=0.8); ax[j].set_xticks(x); ax[j].set_xticklabels(list(pats.values()), fontsize=8.5)
        ax[j].set_title(f"{y}年の経過保険料", loc="left")
    ax[0].set_ylabel("近似のずれ（%、正解＝契約ごとの計算）"); ax[0].legend(fontsize=8, frameon=False)
    fig.suptitle("+10%の改定（2023年7月1日）のあと、係数を掛ける近似はどれだけずれたか", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(); save(fig, "a456_error_by_pattern.png", SRC)

    # 図3：改定の幅・年2回・月ごとの実績を使う直し方
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
    C = df[(df.block == "C") & (df.year == 2023)]
    labs = ["+3%", "+5%", "+10%", "+20%", "-10%"]
    for k, ((pn, gr), col, lab) in enumerate(((("4割が4月1日", 0.0), BLUE, "4割が4月1日"), (("均等", 0.2), ORANGE, "均等・年20%増"))):
        v = [float(C[(C.pattern == pn) & (C.growth == gr) & (C.change.str.startswith(l))].err_pct.iloc[0]) for l in labs]
        ax[0].bar(np.arange(5) + (k - 0.5) * 0.38, v, 0.38, color=col, label=lab)
        for xi, vi in zip(np.arange(5) + (k - 0.5) * 0.38, v): ax[0].text(xi, vi + (0.05 if vi >= 0 else -0.05), f"{vi:+.1f}", ha="center", va="bottom" if vi >= 0 else "top", fontsize=7.5)
    ax[0].axhline(0, color=INK, lw=0.8); ax[0].set_xticks(np.arange(5)); ax[0].set_xticklabels(labs); ax[0].set_xlabel("改定の幅（2023年7月1日）")
    ax[0].set_ylabel("2023年のずれ（%）"); ax[0].set_title("改定の幅とずれ", loc="left"); ax[0].legend(fontsize=8, frameon=False)
    Dd = df[df.block.isin(["D", "E"])].copy(); Dd["lab"] = Dd.pattern + np.where(Dd.growth == 0, "", Dd.growth.map(lambda v: f"・年{abs(v)*100:.0f}%{'増' if v>0 else '減'}"))
    d23 = Dd[(Dd.block == "D")]
    lab2 = d23.lab.unique()
    for k, (y, col) in enumerate(((2023, BLUE), (2024, LIGHT))):
        v = [float(d23[(d23.lab == l) & (d23.year == y)].err_pct.iloc[0]) for l in lab2]
        ax[1].barh(np.arange(len(lab2)) + (k - 0.5) * 0.38, v, 0.38, color=col, label=f"{y}年")
        for yi, vi in zip(np.arange(len(lab2)) + (k - 0.5) * 0.38, v): ax[1].text(vi + (0.03 if vi >= 0 else -0.03), yi, f"{vi:+.1f}", va="center", ha="left" if vi >= 0 else "right", fontsize=7.5)
    ax[1].axvline(0, color=INK, lw=0.8); ax[1].set_yticks(np.arange(len(lab2))); ax[1].set_yticklabels(lab2, fontsize=8); ax[1].invert_yaxis()
    ax[1].set_xlabel("ずれ（%）"); ax[1].set_title("年2回（+5%ずつ）の改定", loc="left"); ax[1].legend(fontsize=8, frameon=False)
    a23 = A[A.year == 2023]
    ax[2].scatter(a23.err_pct, a23.err_monthly_pct, color=ORANGE, s=36, zorder=3)
    lim = max(a23.err_pct.abs().max(), 0.5) * 1.1
    ax[2].axhline(0, color=INK, lw=0.8); ax[2].axvline(0, color=INK, lw=0.8); ax[2].plot([-lim, lim], [-lim, lim], color=GRAY, lw=0.8, ls=":")
    ax[2].set_xlim(-lim, lim); ax[2].set_ylim(-lim, lim)
    ax[2].set_xlabel("始期が均等と置いた近似のずれ（%）"); ax[2].set_ylabel("月ごとの収入保険料を使った係数のずれ（%）")
    ax[2].set_title("月ごとの実績を使う直し方", loc="left")
    fig.tight_layout(); save(fig, "a456_size_twice_and_fix.png", SRC)
    print(json.dumps(main_js, ensure_ascii=False, indent=1, default=float)[:3000])
    print(df[df.block.isin(["B", "D", "E"])][["block", "pattern", "growth", "change", "year", "err_pct", "err_monthly_pct", "lr_shift_pt"]].round(2).to_string())
    print(df[df.block == "C"][["pattern", "growth", "change", "year", "err_pct"]].round(2).to_string())


if __name__ == "__main__":
    main()
