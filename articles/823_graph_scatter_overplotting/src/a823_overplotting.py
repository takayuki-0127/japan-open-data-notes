"""823 散布図の点が多すぎると、関係は見えなくなるのか？（架空のデータ）

架空の会社の顧客。x＝1年の来店回数、y＝1年の購入額（どちらも標準化した架空の値）。
顧客の7割は x と y に関係がある（相関0.6）、3割は関係のない散らばり（x・yとも標準偏差1.5の正規分布、互いに無関係）と置く。
散布図を「画素の並び」として作者が描き（点は半径2画素の円）、図の濃さから読める相関を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 823
SRC = "架空の会社の顧客（作成者が乱数で作成、seed 823）"
W, H = 360, 240          # 図の画素（横×縦）
LIM = 4.0                # 軸の範囲（-4〜4）
BG_SD = 1.5             # 関係のない客の散らばり（標準偏差）
NS = [100, 1_000, 10_000, 100_000, 1_000_000]
REPS = 10


def make(rng, n, rho=0.6, bg=0.3):
    """関係のある客（1-bg）と、関係のない散らばり（bg）の混ざり"""
    k = rng.binomial(n, bg)
    z = rng.normal(size=(n - k, 2))
    x1 = z[:, 0]
    y1 = rho * z[:, 0] + np.sqrt(1 - rho ** 2) * z[:, 1]
    xb, yb = rng.normal(0, BG_SD, k), rng.normal(0, BG_SD, k)
    x, y = np.concatenate([x1, xb]), np.concatenate([y1, yb])
    return x, y


def counts(x, y):
    c, _, _ = np.histogram2d(y, x, bins=[H, W], range=[[-LIM, LIM], [-LIM, LIM]])
    return c


def disk_conv(c, r):
    """点を半径 r 画素の円として描いたとき、各画素に重なる点の数（FFTでたたみ込み）"""
    if r == 0:
        return c
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = ((xx ** 2 + yy ** 2) <= r * r + 0.5).astype(float)
    ph, pw = H + 2 * r, W + 2 * r
    K = np.zeros((ph, pw)); K[:2 * r + 1, :2 * r + 1] = k
    C = np.zeros((ph, pw)); C[:H, :W] = c
    out = np.real(np.fft.ifft2(np.fft.fft2(C) * np.fft.fft2(K)))[r:r + H, r:r + W]
    return np.round(out, 6)


def render(c, mode, r=2, alpha=0.05):
    """図の濃さ（0〜1）。mode: opaque（塗りつぶしの点）/ alpha（透ける点）/ density（画素ごとの数を対数で濃さに）"""
    if mode == "density":
        cc = disk_conv(c, 1)
        return np.log1p(cc) / np.log1p(cc.max())
    o = disk_conv(c, r)
    if mode == "opaque":
        return (o > 0.5).astype(float)
    return 1 - (1 - alpha) ** o


def ink_corr(img):
    """図の濃さを重みにした、画素の位置どうしの相関（＝図から読める相関の目安）"""
    yy, xx = np.mgrid[0:H, 0:W]
    w = img.ravel()
    if w.sum() == 0:
        return np.nan
    mx, my = np.average(xx.ravel(), weights=w), np.average(yy.ravel(), weights=w)
    cov = np.average((xx.ravel() - mx) * (yy.ravel() - my), weights=w)
    vx = np.average((xx.ravel() - mx) ** 2, weights=w)
    vy = np.average((yy.ravel() - my) ** 2, weights=w)
    return float(cov / np.sqrt(vx * vy))


def run(rng, n, rho=0.6, bg=0.3, r=2, alpha=0.05):
    x, y = make(rng, n, rho, bg)
    c = counts(x, y)
    res = {"n": n, "data_corr": float(np.corrcoef(x, y)[0, 1])}
    for mode in ["opaque", "alpha", "density"]:
        img = render(c, mode, r, alpha)
        res[f"{mode}_corr"] = ink_corr(img)
        if mode == "opaque":
            res["opaque_cover"] = float(img.mean())
    return res, c


def main():
    rng = np.random.default_rng(SEED)
    # 1回分のデータ（1万人）を data に
    x, y = make(np.random.default_rng(SEED), 10_000)
    pd.DataFrame({"customer_id": np.arange(1, len(x) + 1), "x_visits_std": x.round(4),
                  "y_spend_std": y.round(4)}).to_csv(DATA / "customers_10000.csv", index=False)

    # 1) 人数ごと（各10回）
    rows = []
    for n in NS:
        for rep in range(REPS):
            r, _ = run(np.random.default_rng(SEED * 1000 + n % 997 + rep * 7919), n)
            r["rep"] = rep
            rows.append(r)
    sim = pd.DataFrame(rows)
    by_n = sim.groupby("n").mean(numeric_only=True).drop(columns="rep").round(3).reset_index()
    by_n.to_csv(RES / "by_n.csv", index=False)

    # 2) 関係あり（7割の客の相関0.6）と関係なし（全員無関係）の図の見分け（塗りつぶしの点）
    diff = []
    for n in NS:
        ra = [run(np.random.default_rng(SEED * 31 + n % 991 + rep), n, rho=0.6)[0] for rep in range(REPS)]
        rb = [run(np.random.default_rng(SEED * 37 + n % 983 + rep), n, rho=0.0)[0] for rep in range(REPS)]
        a, b = pd.DataFrame(ra).mean(numeric_only=True), pd.DataFrame(rb).mean(numeric_only=True)
        diff.append({"n": n, "related_data_corr": round(a.data_corr, 3), "related_opaque_corr": round(a.opaque_corr, 3),
                     "unrelated_data_corr": round(b.data_corr, 3), "unrelated_opaque_corr": round(b.opaque_corr, 3),
                     "related_cover": round(a.opaque_cover, 3), "unrelated_cover": round(b.opaque_cover, 3)})
    pd.DataFrame(diff).to_csv(RES / "related_vs_unrelated.csv", index=False)

    # 3) 確かめ：点の大きさ、関係のない散らばりの割合、透ける度合い、関係の強さ（10万人、各5回）
    sens = []
    variants = [("基本（点の半径2画素・散らばり3割・透け0.05・相関0.6）", {}),
                ("点の半径1画素", {"r": 1}), ("点の半径4画素", {"r": 4}),
                ("関係のない散らばり1割", {"bg": 0.1}), ("関係のない散らばり5割", {"bg": 0.5}),
                ("散らばりなし（全員に関係あり）", {"bg": 0.0}),
                ("透け0.2（濃い）", {"alpha": 0.2}), ("透け0.01（薄い）", {"alpha": 0.01}),
                ("関係の強さ0.3", {"rho": 0.3}), ("関係の強さ0.9", {"rho": 0.9})]
    for j, (name, kw) in enumerate(variants):
        for n in [1_000, 100_000]:
            rr = [run(np.random.default_rng(SEED * 100 + j * 10 + rep + n % 13), n, **kw)[0] for rep in range(5)]
            m = pd.DataFrame(rr).mean(numeric_only=True)
            sens.append({"variant": name, "n": n, "data_corr": round(m.data_corr, 3), "opaque_corr": round(m.opaque_corr, 3),
                         "alpha_corr": round(m.alpha_corr, 3), "density_corr": round(m.density_corr, 3),
                         "opaque_cover": round(m.opaque_cover, 3)})
    pd.DataFrame(sens).to_csv(RES / "sensitivity.csv", index=False)

    out = {"by_n_mean_of_10": by_n.to_dict("records"), "related_vs_unrelated": diff, "sensitivity": sens,
           "settings": {"pixels": [W, H], "axis_range": [-LIM, LIM], "marker_radius_px": 2, "alpha": 0.05,
                        "rho_core": 0.6, "background_share": 0.3, "background_sd": BG_SD, "reps": REPS}}
    json.dump(out, open(RES / "a823_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じデータを3つの描き方で（人数を変えて）
    show_n = [1_000, 100_000, 1_000_000]
    fig, axs = plt.subplots(3, 3, figsize=(9.6, 7.0))
    panels = []
    for j, n in enumerate(show_n):
        c = counts(*make(np.random.default_rng(SEED + j), n))
        for i, (mode, lab) in enumerate([("opaque", "塗りつぶしの点"), ("alpha", "透ける点（0.05）"), ("density", "画素ごとの数（対数）")]):
            ax = axs[i, j]
            img = render(c, mode)
            ax.imshow(img, cmap="Greys", vmin=0, vmax=1, origin="lower", aspect="auto")
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(True); s.set_color(GRAY); s.set_linewidth(.6)
            panels.append({"n": n, "mode": mode, "ink_corr": round(ink_corr(img), 3), "cover": round(float((img > 0).mean()), 3)})
            ax.text(.02, .97, f"図の相関 {ink_corr(img):.2f}", transform=ax.transAxes, fontsize=8.5, va="top",
                    color=ORANGE, bbox=dict(fc="white", ec="none", alpha=.8, pad=1))
            if i == 0:
                ax.set_title(f"{n:,}人", fontsize=11)
            if j == 0:
                ax.set_ylabel(lab, fontsize=10)
    fig.suptitle(f"同じ置き方のデータ（データの相関は約{by_n.data_corr.iloc[-1]:.2f}）を、人数と描き方を変えて描く", fontsize=12)
    fig.tight_layout()
    save(fig, "a823_panels.png", SRC)
    out["figure_panels_one_draw"] = panels
    json.dump(out, open(RES / "a823_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図2：人数と図から読める相関
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(by_n.n, by_n.data_corr, color=INK, lw=1.4, ls="--", marker="o", ms=3, label="データの相関")
    ax.plot(by_n.n, by_n.opaque_corr, color=ORANGE, lw=1.8, marker="o", ms=4, label="塗りつぶしの点")
    ax.plot(by_n.n, by_n.alpha_corr, color=BLUE, lw=1.8, marker="o", ms=4, label="透ける点（0.05）")
    ax.plot(by_n.n, by_n.density_corr, color=GREEN, lw=1.8, marker="o", ms=4, label="画素ごとの数（対数）")
    ax.set_xscale("log"); ax.set_ylim(0, .7)
    ax.set_xlabel("点の数（人、対数の目盛り）"); ax.set_ylabel("図の濃さから読める相関")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("塗りつぶしの点は、人数が増えるほど図から関係が消える（各10回の平均）")
    save(fig, "a823_corr_by_n.png", SRC)

    # 図3：関係あり／なしの図から読める相関（塗りつぶしの点）
    dd = pd.DataFrame(diff)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xs = np.arange(len(dd))
    ax.bar(xs - .18, dd.related_opaque_corr, width=.36, color=ORANGE, label="関係あり（7割の客が相関0.6）")
    ax.bar(xs + .18, dd.unrelated_opaque_corr, width=.36, color=GRAY, label="関係なし（全員が無関係）")
    for i, (u, v) in enumerate(zip(dd.related_opaque_corr, dd.unrelated_opaque_corr)):
        ax.text(i - .18, u + .01, f"{u:.2f}", ha="center", fontsize=8.5)
        ax.text(i + .18, max(v, 0) + .01, f"{(0.0 if abs(v) < 0.005 else v):.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"{n:,}" for n in dd.n])
    ax.axhline(0, color=INK, lw=.6)
    ax.set_ylim(-.05, .45)
    ax.set_xlabel("点の数（人）"); ax.set_ylabel("図の濃さから読める相関")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("塗りつぶしの点では、100万人で関係あり・なしの図がほぼ同じになる", fontsize=11.5)
    save(fig, "a823_related_vs_not.png", SRC, y=-0.05)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
