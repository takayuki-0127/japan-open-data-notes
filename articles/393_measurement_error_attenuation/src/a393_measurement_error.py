"""A393 説明する側の数字に測り間違いがあると、回帰の係数はどれだけ小さく出るのか。真の係数が分かっている架空のデータで数える。
python a393_measurement_error.py      # 全部を計算し直す（約1〜2分）
"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import *
SEED = 393
SRC = "出典：架空のデータ（作成者が乱数で作成、seed 393）"
BETA = 1.0


def ols(X, y):
    """切片つきの回帰。係数・標準誤差・p値を返す（X は列ごとの説明変数）"""
    X = np.column_stack([np.ones(len(y)), X]); XtX = np.linalg.inv(X.T @ X); b = XtX @ X.T @ y
    r = y - X @ b; s2 = r @ r / (len(y) - X.shape[1]); se = np.sqrt(np.diag(XtX) * s2)
    return b[1:], se[1:], 2 * stats.t.sf(np.abs(b[1:] / se[1:]), len(y) - X.shape[1])


def make(rng, n, lam, rho, gamma):
    x = rng.normal(0, 1, n); z = rho * x + np.sqrt(1 - rho ** 2) * rng.normal(0, 1, n)
    su = np.sqrt((1 - lam) / lam) if lam < 1 else 0.0          # 信頼性 lam = var(x)/(var(x)+var(u))
    w1, w2 = x + rng.normal(0, su, n), x + rng.normal(0, su, n)  # 同じものを2回測った値
    y = BETA * x + gamma * z + rng.normal(0, 1, n)
    return x, z, w1, w2, y


def plim(lam, rho, gamma):
    """理屈の値：測り間違いのある w と z で回帰したときの係数"""
    k = (1 - rho ** 2) / ((1 - rho ** 2) + (1 - lam) / lam)
    return BETA * k, gamma + BETA * rho * (1 - k)


def attenuation(rng, reps=2000, n=1000, gamma=0.5):
    rec = []
    for rho in (0.0, 0.3, 0.6, 0.8):
        for lam in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
            B = np.array([ols(np.column_stack([w1, z]), y)[0] for x, z, w1, w2, y in (make(rng, n, lam, rho, gamma) for _ in range(reps))])
            bw, bz = plim(lam, rho, gamma)
            rec.append(dict(rho=rho, reliability=lam, b_w=B[:, 0].mean(), b_w_theory=bw, b_z=B[:, 1].mean(), b_z_theory=bz, true_b_z=gamma))
    return pd.DataFrame(rec)


def spurious(rng, reps=2000, rho=0.6):
    """z の本当の係数は0。それでも「z が効いている」（p<0.05）と出た割合"""
    rec = []
    for lam in (1.0, 0.9, 0.7, 0.5):
        for n in (100, 300, 1000, 3000):
            P = np.array([ols(np.column_stack([w1, z]), y) for x, z, w1, w2, y in (make(rng, n, lam, rho, 0.0) for _ in range(reps))])
            rec.append(dict(reliability=lam, n=n, rho=rho, z_significant_pct=100 * (P[:, 2, 1] < 0.05).mean(), b_z_mean=P[:, 0, 1].mean(), b_z_theory=plim(lam, rho, 0.0)[1]))
    return pd.DataFrame(rec)


def correction(rng, reps=2000):
    """z なしの回帰で、直し方を比べる：そのまま／2回の平均／信頼性で割る／2回目を道具に使う"""
    rec = []
    for lam in (0.7, 0.5):
        for n in (200, 1000):
            out = {k: [] for k in ("そのまま（1回の測定）", "2回の測定の平均", "信頼性で割る", "2回目の測定を道具に使う")}; cover = []
            for _ in range(reps):
                x, z, w1, w2, y = make(rng, n, lam, 0.0, 0.0)
                b, se, _p = ols(w1[:, None], y); out["そのまま（1回の測定）"].append(b[0]); cover.append(abs(b[0] - BETA) < 1.96 * se[0])
                out["2回の測定の平均"].append(ols(((w1 + w2) / 2)[:, None], y)[0][0])
                out["信頼性で割る"].append(b[0] / np.corrcoef(w1, w2)[0, 1])        # 2回の測定の相関が信頼性の見積もり
                out["2回目の測定を道具に使う"].append(np.cov(y, w2)[0, 1] / np.cov(w1, w2)[0, 1])
            for k, v in out.items():
                v = np.array(v); rec.append(dict(reliability=lam, n=n, method=k, mean=v.mean(), bias_pct=100 * (v.mean() - BETA) / BETA, sd=v.std(), rmse=np.sqrt(((v - BETA) ** 2).mean())))
            rec[-4]["naive_ci_cover_pct"] = 100 * np.mean(cover)
    return pd.DataFrame(rec)


def error_in_y(rng, reps=2000, n=1000):
    """測り間違いが y の側にあるとき：係数は薄まらず、幅だけ広がる"""
    rec = []
    for sv in (0.0, 1.0, 2.0):
        B = []
        for _ in range(reps):
            x, z, w1, w2, y = make(rng, n, 1.0, 0.0, 0.0); b, se, _p = ols(x[:, None], y + rng.normal(0, sv, n)); B.append((b[0], se[0]))
        B = np.array(B); rec.append(dict(y_error_sd=sv, b_mean=B[:, 0].mean(), se_mean=B[:, 1].mean()))
    return pd.DataFrame(rec)


def figures(at, sp, co):
    C = [BLUE, GREEN, ORANGE, "#8a4fbf"]
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.3))
    for c, (rho, g) in zip(C, at.groupby("rho")):
        ax[0].plot(g.reliability, g.b_w_theory, "-", color=c, lw=1.2); ax[0].plot(g.reliability, g.b_w, "o", color=c, label=f"もう1つの変数との相関 {rho:g}")
        ax[1].plot(g.reliability, g.b_z_theory, "-", color=c, lw=1.2); ax[1].plot(g.reliability, g.b_z, "o", color=c)
    ax[0].axhline(1, color=INK, lw=0.6, ls=":"); ax[0].set_title("測り間違いのある変数の係数（本当は1.0）"); ax[0].set_xlabel("信頼性（1.0＝測り間違いなし）"); ax[0].set_ylabel("係数（2,000回の平均）"); ax[0].invert_xaxis(); ax[0].legend(frameon=False, fontsize=9)
    ax[1].axhline(0.5, color=INK, lw=0.6, ls=":"); ax[1].set_title("正しく測ったもう1つの変数の係数（本当は0.5）"); ax[1].set_xlabel("信頼性"); ax[1].invert_xaxis()
    fig.suptitle("測り間違いが大きいほど係数は小さく出て、薄まった分はもう1つの変数に移る（点＝試した結果、線＝理屈の式）", y=1.02, fontsize=12)
    save(fig, "a393_attenuation_and_spillover.png", SRC)
    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    for c, (lam, g) in zip([GRAY, BLUE, GREEN, ORANGE], sp.groupby("reliability", sort=False)):
        ax.plot(range(4), g.z_significant_pct, "o-", color=c, label=f"信頼性 {lam:g}" + ("（測り間違いなし）" if lam == 1 else ""))
        for j, v in enumerate(g.z_significant_pct): ax.text(j, v + 2.5, f"{v:.0f}", ha="center", fontsize=9, color=c)
    ax.axhline(5, color=INK, lw=0.6, ls=":"); ax.set_xticks(range(4)); ax.set_xticklabels(["100件", "300件", "1,000件", "3,000件"]); ax.set_ylim(0, 110)
    ax.set_ylabel("「効いている」（p<0.05）と出た割合（%）"); ax.legend(frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1.0, 0.08))
    ax.set_title("本当は効いていない変数が「効いている」と出た割合（相関0.6）")
    save(fig, "a393_spurious_significance.png", SRC)
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.3), sharey=True)
    for a, n in zip(ax, (200, 1000)):
        g = co[(co.reliability == 0.7) & (co.n == n)]; x = np.arange(len(g))
        a.bar(x, g["mean"], color=[GRAY, LIGHT, BLUE, ORANGE]); a.errorbar(x, g["mean"], yerr=g.sd, fmt="none", ecolor=INK, capsize=4, lw=1)
        for i, (m, s) in enumerate(zip(g["mean"], g.sd)): a.text(i, m + s + 0.02, f"{m:.2f}", ha="center", fontsize=10)
        a.axhline(1, color=INK, lw=0.6, ls=":"); a.set_xticks(x); a.set_xticklabels([s.replace("（", "\n（").replace("の測定を", "の測定を\n") for s in g.method], fontsize=8.5); a.set_title(f"{n:,}件"); a.set_ylim(0, 1.3)
    ax[0].set_ylabel("係数（本当は1.0。棒＝平均、ひげ＝ばらつき）")
    fig.suptitle("直し方の比べ（信頼性0.7）：同じものを2回測ってあれば、薄まりは戻せる", y=1.02)
    save(fig, "a393_correction_methods.png", SRC)


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    at = attenuation(rng); sp = spurious(rng); co = correction(rng); ey = error_in_y(rng)
    at.round(4).to_csv(RES / "attenuation.csv", index=False); sp.round(3).to_csv(RES / "spurious_significance.csv", index=False)
    co.round(4).to_csv(RES / "correction.csv", index=False); ey.round(4).to_csv(RES / "error_in_y.csv", index=False)
    x, z, w1, w2, y = make(np.random.default_rng(SEED + 1), 300, 0.7, 0.6, 0.5)
    pd.DataFrame({"x_true": x, "z": z, "w_measured_1": w1, "w_measured_2": w2, "y": y}).round(4).to_csv(DATA / "example_300.csv", index=False)
    figures(at, sp, co)
    main = {"seed": SEED, "attenuation": at.round(3).to_dict("records"), "spurious": sp.round(2).to_dict("records"),
            "correction": co.round(3).to_dict("records"), "error_in_y": ey.round(4).to_dict("records")}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(at.round(3).to_string()); print(sp.round(2).to_string()); print(co.round(3).to_string()); print(ey.round(4).to_string())
