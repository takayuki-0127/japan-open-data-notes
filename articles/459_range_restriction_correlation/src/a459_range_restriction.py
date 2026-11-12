"""459 選ばれた人や店だけで相関を見ると、相関はどれだけ小さく見えるか
2つの数字 x（選ぶ前に分かる点数）と y（あとの成績）を、決めた相関で作る。
選び方を変えて、選ばれた側だけの相関を測る。範囲の制限の補正式も試す。seed 459"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 459
RHOS = [0.3, 0.5, 0.8]
KEEPS = [0.9, 0.7, 0.5, 0.3, 0.2, 0.1, 0.05]
N_POP = 1000                                 # 選ぶ前の人数
REP = 4000
SRC = "架空のデータ（作成者が乱数で作成、seed 459）"
SEL = {"top_x": "x の上位だけ", "drop_low": "x の下位を除く", "total": "x と y の合計の上位だけ", "third": "x と似た別の点数 z の上位だけ", "middle_out": "x の上位と下位だけ（中を除く）"}


def draw(rng, rho, rep=REP, n=N_POP):
    x = rng.standard_normal((rep, n)); y = rho * x + np.sqrt(1 - rho**2) * rng.standard_normal((rep, n))
    return x, y


def select(rng, x, y, kind, keep):
    """選ばれた行の印（True）を返す"""
    if kind in ("top_x", "drop_low"): s = x                       # 同じ決まり（上から keep の割合を残す）
    elif kind == "total": s = x + y
    elif kind == "third": s = 0.7 * x + np.sqrt(1 - 0.49) * rng.standard_normal(x.shape)   # z と x の相関0.7、y とは x を通じてだけ
    elif kind == "middle_out": s = np.abs(x - np.median(x, axis=1, keepdims=True))
    thr = np.quantile(s, 1 - keep, axis=1, keepdims=True)
    return s >= thr


def corr_rows(x, y, m):
    """行ごとに、印のついた点だけの相関と x の標準偏差"""
    w = m.astype(float); n = w.sum(1)
    mx = (x * w).sum(1) / n; my = (y * w).sum(1) / n
    dx = (x - mx[:, None]) * w; dy = (y - my[:, None]) * w
    sxx = (dx**2).sum(1); syy = (dy**2).sum(1); sxy = (dx * dy).sum(1)
    return sxy / np.sqrt(sxx * syy), np.sqrt(sxx / (n - 1)), n


def thorndike(r, u):
    """範囲の制限の補正（x で直接選んだときの式）。u＝選ぶ前の x の標準偏差÷選んだあとの標準偏差"""
    return r * u / np.sqrt(1 + r**2 * (u**2 - 1))


def theory_top(rho, keep):
    """x の上位 keep を残したときの相関（正規分布の式）"""
    a = stats.norm.ppf(1 - keep); lam = stats.norm.pdf(a) / keep
    v = 1 + a * lam - lam**2                                        # 選んだあとの x の分散
    return rho * np.sqrt(v) / np.sqrt(1 - rho**2 + rho**2 * v), np.sqrt(v)


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for rho in RHOS:
        x, y = draw(rng, rho)
        r_all, sd_all, _ = corr_rows(x, y, np.ones_like(x, bool))
        for kind, kn in SEL.items():
            if kind == "drop_low": continue                         # top_x と同じ決まり。割合の読み替えだけ
            for keep in KEEPS:
                m = select(rng, x, y, kind, keep)
                r, sd, n = corr_rows(x, y, m)
                u = sd_all / sd; rc = thorndike(r, u)
                th = theory_top(rho, keep)[0] if kind == "top_x" else np.nan
                rows.append(dict(rho=rho, selection=kn, keep=keep, n_selected=int(n.mean()), r_selected=r.mean(), r_sd=r.std(ddof=1), r_p05=np.percentile(r, 5), r_p95=np.percentile(r, 95),
                                 sign_flip_pct=(r < 0).mean() * 100, theory_r=th, sd_ratio=(sd / sd_all).mean(),
                                 r_corrected=rc.mean(), corrected_err=rc.mean() - rho, corrected_sd=rc.std(ddof=1), r_all=r_all.mean()))
    df = pd.DataFrame(rows); df.round(5).to_csv(RES / "selected_correlation.csv", index=False)

    # 人数を変える（x の上位2割だけ。本当の相関0.3）：符号が逆に出る割合
    rows = []
    for npop in (100, 250, 500, 1000, 5000):
        x, y = draw(rng, 0.3, rep=4000 if npop <= 1000 else 1500, n=npop)
        for keep in (0.5, 0.2, 0.1):
            r, _, n = corr_rows(x, y, select(rng, x, y, "top_x", keep))
            rows.append(dict(rho=0.3, n_before=npop, keep=keep, n_selected=int(n.mean()), r_mean=r.mean(), sign_flip_pct=(r < 0).mean() * 100,
                             not_sig_pct=(np.abs(r) * np.sqrt((n - 2) / (1 - r**2)) < stats.t.ppf(0.975, n - 2)).mean() * 100))
    small = pd.DataFrame(rows); small.round(4).to_csv(RES / "sign_flip_by_size.csv", index=False)

    # 式の前提と違うとき：y の散らばりが x で変わる／関係が曲がっている
    rows = []
    for name in ("前提どおり（直線・散らばり一定）", "x が高いほど y の散らばりが大きい", "x が高いと頭打ち（曲がった関係）"):
        x = rng.standard_normal((REP, N_POP)); e = rng.standard_normal((REP, N_POP))
        if name.startswith("前提"): y = 0.5 * x + np.sqrt(0.75) * e
        elif name.startswith("x が高いほど"): y = 0.5 * x + np.sqrt(0.75) * e * np.exp(0.5 * x) / np.exp(0.125 * 2) ** 0.5
        else: y = np.where(x < 0.5, x, 0.5 + 0.1 * (x - 0.5)) + 0.9 * e
        r_all, sd_all, _ = corr_rows(x, y, np.ones_like(x, bool))
        for keep in (0.5, 0.2):
            r, sd, _ = corr_rows(x, y, select(rng, x, y, "top_x", keep)); rc = thorndike(r, sd_all / sd)
            rows.append(dict(case=name, keep=keep, r_all=r_all.mean(), r_selected=r.mean(), r_corrected=rc.mean(), corrected_minus_all=rc.mean() - r_all.mean()))
    viol = pd.DataFrame(rows); viol.round(4).to_csv(RES / "correction_assumption_violations.csv", index=False)

    # 例のデータ（1回分）
    r2 = np.random.default_rng(SEED); x1, y1 = draw(r2, 0.5, rep=1)
    ex = pd.DataFrame({"x": x1[0].round(4), "y": y1[0].round(4)})
    ex["top20_x"] = select(r2, x1, y1, "top_x", 0.2)[0]; ex["top20_total"] = select(r2, x1, y1, "total", 0.2)[0]
    ex.to_csv(DATA / "example_one_draw.csv", index=False)

    def v(rho, sel, keep, col="r_selected"): return float(df[(df.rho == rho) & (df.selection == sel) & (df.keep == keep)][col].iloc[0])
    main_js = dict(
        top_x={str(rho): {str(k): round(v(rho, SEL["top_x"], k), 3) for k in KEEPS} for rho in RHOS},
        top_x_theory={str(rho): {str(k): round(theory_top(rho, k)[0], 3) for k in KEEPS} for rho in RHOS},
        total={str(rho): {str(k): round(v(rho, SEL["total"], k), 3) for k in KEEPS} for rho in RHOS},
        third={str(rho): {str(k): round(v(rho, SEL["third"], k), 3) for k in KEEPS} for rho in RHOS},
        middle_out={str(rho): {str(k): round(v(rho, SEL["middle_out"], k), 3) for k in KEEPS} for rho in RHOS},
        sign_flip={sel: {str(rho): {str(k): round(v(rho, sel, k, "sign_flip_pct"), 1) for k in KEEPS} for rho in RHOS} for sel in (SEL["top_x"], SEL["total"])},
        corrected={sel: {str(rho): {str(k): round(v(rho, sel, k, "r_corrected"), 3) for k in (0.5, 0.2, 0.1)} for rho in RHOS} for sel in (SEL["top_x"], SEL["total"], SEL["third"], SEL["middle_out"])},
        corrected_sd_top={str(rho): {str(k): round(v(rho, SEL["top_x"], k, "corrected_sd"), 3) for k in (0.5, 0.2, 0.1)} for rho in RHOS},
        max_gap_sim_vs_theory=float((df.r_selected - df.theory_r).abs().max()),
        small=small.round(3).to_dict("records"), viol=viol.round(3).to_dict("records"))
    json.dump(main_js, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：1回分の例（本当の相関0.5）
    fig, ax = plt.subplots(1, 3, figsize=(12.5, 4.2), sharex=True, sharey=True)
    r2 = np.random.default_rng(SEED); x1, y1 = draw(r2, 0.5, rep=1)
    for a, (kind, ttl) in zip(ax, (("top_x", "x の上位2割だけ"), ("total", "x と y の合計の上位2割だけ"), ("third", "x と似た別の点数の上位2割だけ"))):
        m = select(r2, x1, y1, kind, 0.2)[0]
        a.scatter(x1[0][~m], y1[0][~m], s=6, color=LIGHT, alpha=0.7, label="選ばれなかった")
        a.scatter(x1[0][m], y1[0][m], s=8, color=ORANGE, label="選ばれた")
        ra = np.corrcoef(x1[0], y1[0])[0, 1]; rs = np.corrcoef(x1[0][m], y1[0][m])[0, 1]
        a.set_title(f"{ttl}\n全体の相関 {ra:.2f} → 選ばれた側 {rs:+.2f}", loc="left", fontsize=10.5); a.set_xlabel("x（選ぶ前に分かる点数）")
    ax[0].set_ylabel("y（あとの成績）"); ax[0].legend(fontsize=8, frameon=False, loc="upper left")
    fig.tight_layout(); save(fig, "a459_example_scatter.png", SRC)

    # 図2：残す割合と、選ばれた側の相関
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    for a, (sel, ttl) in zip(ax, ((SEL["top_x"], "x の上位だけ"), (SEL["third"], "x と似た別の点数の上位だけ"), (SEL["total"], "x と y の合計の上位だけ"))):
        for rho, col in zip(RHOS, (LIGHT, BLUE, INK)):
            s = df[(df.rho == rho) & (df.selection == sel)]
            a.plot(range(len(KEEPS)), s.r_selected, "-o", color=col, lw=1.8, ms=4, label=f"本当の相関 {rho}")
            a.fill_between(range(len(KEEPS)), s.r_p05, s.r_p95, color=col, alpha=0.10)
            a.axhline(rho, color=col, lw=0.7, ls=":")
        a.axhline(0, color=GRAY, lw=0.8); a.set_xticks(range(len(KEEPS))); a.set_xticklabels([f"{k*100:g}%" for k in KEEPS]); a.set_xlabel("残す割合"); a.set_title(ttl, loc="left", fontsize=11)
    ax[0].set_ylabel("選ばれた側だけの相関（帯は5〜95%の範囲）"); ax[0].legend(fontsize=8.5, frameon=False, loc="lower left")
    fig.tight_layout(); save(fig, "a459_selected_r_by_keep.png", SRC)

    # 図3：補正式でどこまで戻るか（残す割合2割）
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    sels = [SEL["top_x"], SEL["third"], SEL["total"], SEL["middle_out"]]; xx = np.arange(len(sels)); w = 0.26
    for k, (rho, col) in enumerate(zip(RHOS, (LIGHT, BLUE, INK))):
        vv = [v(rho, s_, 0.2, "r_corrected") for s_ in sels]
        ax[0].bar(xx + (k - 1) * w, vv, w, color=col, label=f"本当の相関 {rho}")
        for xi, vi in zip(xx + (k - 1) * w, vv): ax[0].text(xi, vi + (0.02 if vi >= 0 else -0.02), f"{vi:.2f}", ha="center", va="bottom" if vi >= 0 else "top", fontsize=7.5)
        ax[0].hlines(rho, -0.5, len(sels) - 0.5, color=col, lw=0.8, ls=":")
    ax[0].axhline(0, color=GRAY, lw=0.8); ax[0].set_xticks(xx); ax[0].set_xticklabels(["x の上位", "似た別の点数\nの上位", "x と y の\n合計の上位", "x の上位と\n下位だけ"], fontsize=8.5)
    ax[0].set_ylabel("補正したあとの相関（残す割合2割）"); ax[0].set_title("補正式で戻した相関（点線が本当の相関）", loc="left", fontsize=11); ax[0].legend(fontsize=8, frameon=False, loc="lower left")
    for keep, col in ((0.5, LIGHT), (0.2, BLUE), (0.1, ORANGE)):
        s = small[small.keep == keep]; ax[1].plot(range(len(s)), s.sign_flip_pct, "-o", color=col, lw=1.8, ms=4, label=f"上位{keep*100:.0f}%を残す")
    ax[1].set_xticks(range(5)); ax[1].set_xticklabels(["100", "250", "500", "1,000", "5,000"]); ax[1].set_xlabel("選ぶ前の人数")
    ax[1].set_ylabel("選ばれた側の相関がマイナスに出た割合（%）"); ax[1].set_title("本当の相関0.3で、符号が逆に出た割合", loc="left", fontsize=11); ax[1].legend(fontsize=8.5, frameon=False)
    fig.tight_layout(); save(fig, "a459_correction_and_sign_flip.png", SRC)

    for sel in SEL.values():
        s = df[df.selection == sel]
        if len(s): print(sel); print(s.pivot(index="rho", columns="keep", values="r_selected")[KEEPS].round(3).to_string()); print(s.pivot(index="rho", columns="keep", values="sign_flip_pct")[KEEPS].round(1).to_string()); print(s.pivot(index="rho", columns="keep", values="r_corrected")[KEEPS].round(3).to_string())
    print(pd.DataFrame(main_js["top_x_theory"]).T.to_string()); print(main_js["max_gap_sim_vs_theory"])
    print(df[df.selection == SEL["top_x"]].pivot(index="rho", columns="keep", values="corrected_sd")[KEEPS].round(3).to_string())
    print(df[df.selection == SEL["top_x"]].pivot(index="rho", columns="keep", values="r_sd")[KEEPS].round(3).to_string())
    print(small.round(2).to_string()); print(viol.round(3).to_string())


if __name__ == "__main__":
    main()
