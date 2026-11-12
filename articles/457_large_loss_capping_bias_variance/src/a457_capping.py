"""457 大きな損害に上限を置いてから料率のもとになる見込みを出すと、偏りと振れはどう入れ替わるか
架空の損害。自分の契約の集まりは、全体より事故が多い（少ない）かもしれない。
1年分の実績から「1契約あたりの損害の見込み」を出す。seed 457"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 457
LAM = 0.05                                   # 全体の事故の頻度（1契約・1年あたり）
MEAN = 1_000_000                             # 全体の1事故あたりの損害の平均（円）
QS = [0.50, 0.80, 0.90, 0.95, 0.98, 0.99, 0.995, 0.999, 1.0]     # 上限の高さ（損害額の何%点か。1.0は上限なし）
QL = ["50%点", "80%点", "90%点", "95%点", "98%点", "99%点", "99.5%点", "99.9%点", "上限なし"]
NS = [1000, 3000, 10000, 30000, 100000]
REP = 8000
SRC = "架空の損害（作成者が乱数で作成、seed 457）"


class LogN:
    def __init__(self, sigma):
        self.s = sigma; self.mu = np.log(MEAN) - sigma**2 / 2; self.name = f"対数正規（σ={sigma}）"
    def draw(self, rng, n): return rng.lognormal(self.mu, self.s, n)
    def q(self, p): return np.inf if p >= 1 else float(np.exp(self.mu + self.s * stats.norm.ppf(p)))
    def lev(self, m):                                   # E[min(X, m)]
        if np.isinf(m): return MEAN
        z = (np.log(m) - self.mu) / self.s
        return MEAN * stats.norm.cdf(z - self.s) + m * stats.norm.sf(z)
    def var_capped(self, m):                            # Var(min(X, m))
        if np.isinf(m): return MEAN**2 * (np.exp(self.s**2) - 1)
        z = (np.log(m) - self.mu) / self.s
        e2 = np.exp(2 * self.mu + 2 * self.s**2) * stats.norm.cdf(z - 2 * self.s) + m**2 * stats.norm.sf(z)
        return e2 - self.lev(m)**2
    def e2_capped(self, m): return self.var_capped(m) + self.lev(m)**2


class Pareto:                                           # ロマックス型（0から始まるパレート）
    def __init__(self, alpha):
        self.a = alpha; self.th = MEAN * (alpha - 1); self.name = f"パレート（α={alpha}）"
    def draw(self, rng, n): return self.th * (rng.random(n) ** (-1 / self.a) - 1)
    def q(self, p): return np.inf if p >= 1 else float(self.th * ((1 - p) ** (-1 / self.a) - 1))
    def lev(self, m):
        if np.isinf(m): return MEAN
        return self.th / (self.a - 1) * (1 - (self.th / (m + self.th)) ** (self.a - 1))
    def e2_capped(self, m):
        if np.isinf(m): return 2 * self.th**2 / ((self.a - 1) * (self.a - 2))
        x = np.linspace(0, m, 400001); return float(np.trapezoid(2 * x * (self.th / (x + self.th)) ** self.a, x))


DISTS = [LogN(1.2), LogN(2.0), Pareto(2.5)]


def simulate(rng, dist, n, cv, rep=REP, load_err=0.0):
    """自分の集まりの頻度は全体の θ 倍（θ は平均1・変動係数 cv の対数正規）。
    見込み＝上限までの実績（1契約あたり）＋全体の「上限を超えた分」の平均（1契約あたり）"""
    caps = np.array([dist.q(p) for p in QS])
    s2 = np.log(1 + cv**2); theta = np.exp(rng.normal(-s2 / 2, np.sqrt(s2), rep)) if cv > 0 else np.ones(rep)
    cnt = rng.poisson(n * LAM * theta)
    x = dist.draw(rng, cnt.sum()); idx = np.repeat(np.arange(rep), cnt)
    capped = np.stack([np.bincount(idx, weights=np.minimum(x, c), minlength=rep) for c in caps], axis=1) / n
    excess_pool = LAM * (MEAN - np.array([dist.lev(c) for c in caps])) * (1 + load_err)
    est = capped + excess_pool[None, :]
    truth = (LAM * MEAN * theta)[:, None]                 # 自分の集まりの本当の見込み
    err = (est - truth) / (LAM * MEAN)                    # 全体の見込みを1としたずれ
    return err, theta


def theory(dist, n, cv, p):
    """式で出した RMSE（全体の見込みを1とする）：振れ＝ポアソンの件数×上限までの損害、偏り＝θの違い×超過分"""
    c = dist.q(p); lev = dist.lev(c); e2 = dist.e2_capped(c)
    var_noise = LAM * e2 / n / (LAM * MEAN) ** 2        # θ の平均は1
    bias_sd = cv * (MEAN - lev) / MEAN
    return np.sqrt(var_noise + bias_sd**2), np.sqrt(var_noise), bias_sd


def main():
    rng = np.random.default_rng(SEED)
    rows, dec = [], []
    for dist in DISTS:
        for cv in (0.0, 0.1, 0.2, 0.4):
            for n in NS:
                err, theta = simulate(rng, dist, n, cv)
                for j, (p, lab) in enumerate(zip(QS, QL)):
                    e = err[:, j]; th_r, th_n, th_b = theory(dist, n, cv, p)
                    rows.append(dict(dist=dist.name, cv=cv, n=n, cap=lab, cap_q=p, cap_yen=dist.q(p), share_capped=dist.lev(dist.q(p)) / MEAN,
                                     rmse_pct=np.sqrt(np.mean(e**2)) * 100, mean_err_pct=e.mean() * 100,
                                     theory_rmse_pct=th_r * 100, theory_noise_pct=th_n * 100, theory_bias_pct=th_b * 100))
                if cv == 0.2:                               # 全体より2割悪い集まり（θ=1.2 前後）だけを取り出した偏り
                    hi = (theta > 1.1) & (theta < 1.3)
                    for j, lab in enumerate(QL):
                        dec.append(dict(dist=dist.name, n=n, cap=lab, mean_theta=theta[hi].mean(), bias_pct_when_20pct_worse=err[hi, j].mean() * 100,
                                        sd_pct_when_20pct_worse=err[hi, j].std(ddof=1) * 100, n_runs=int(hi.sum())))
    df = pd.DataFrame(rows); df.round(5).to_csv(RES / "rmse_by_cap.csv", index=False)
    pd.DataFrame(dec).round(4).to_csv(RES / "bias_when_20pct_worse.csv", index=False)
    best = df.loc[df.groupby(["dist", "cv", "n"]).rmse_pct.idxmin(), ["dist", "cv", "n", "cap", "rmse_pct"]].merge(
        df[df.cap == "上限なし"][["dist", "cv", "n", "rmse_pct"]].rename(columns={"rmse_pct": "rmse_nocap_pct"}), on=["dist", "cv", "n"])
    th = df.loc[df.groupby(["dist", "cv", "n"]).theory_rmse_pct.idxmin(), ["dist", "cv", "n", "cap", "theory_rmse_pct"]].rename(columns={"cap": "cap_theory"}).merge(
        df[df.cap == "上限なし"][["dist", "cv", "n", "theory_rmse_pct"]].rename(columns={"theory_rmse_pct": "theory_nocap_pct"}), on=["dist", "cv", "n"])
    best = best.merge(th, on=["dist", "cv", "n"])
    best["rmse_ratio"] = best.theory_rmse_pct / best.theory_nocap_pct          # 式で出した比（上限なしのシミュレーションは回ごとの振れが大きいため）
    best["rmse_ratio_sim"] = best.rmse_pct / best.rmse_nocap_pct
    best.round(4).to_csv(RES / "best_cap.csv", index=False)

    # 上乗せの見積もりを誤ったとき（全体の超過分を ±20% 読み違える）
    rows = []
    for dist in DISTS:
        for le in (-0.2, 0.0, 0.2):
            err, _ = simulate(rng, dist, 10000, 0.2, load_err=le)
            for j, lab in enumerate(QL):
                rows.append(dict(dist=dist.name, load_err=le, cap=lab, mean_err_pct=err[:, j].mean() * 100, rmse_pct=np.sqrt(np.mean(err[:, j] ** 2)) * 100))
    le_df = pd.DataFrame(rows); le_df.round(4).to_csv(RES / "load_misestimate.csv", index=False)

    # 例（1回分）：1万契約・対数正規σ=2.0 の事故の一覧
    r2 = np.random.default_rng(SEED); d = DISTS[1]; k = r2.poisson(10000 * LAM)
    pd.DataFrame({"claim_id": np.arange(1, k + 1), "loss_yen": d.draw(r2, k).round(0)}).to_csv(DATA / "example_claims_one_year.csv", index=False)

    def val(dist, cv, n, cap, col="rmse_pct"): return float(df[(df.dist == dist) & (df.cv == cv) & (df.n == n) & (df.cap == cap)][col].iloc[0])
    main_js = dict(
        caps={d_.name: {lab: (None if np.isinf(d_.q(p)) else round(d_.q(p))) for p, lab in zip(QS, QL)} for d_ in DISTS},
        share_below_cap={d_.name: {lab: round(d_.lev(d_.q(p)) / MEAN, 4) for p, lab in zip(QS, QL)} for d_ in DISTS},
        rmse_cv02={d_.name: {str(n): {lab: round(val(d_.name, 0.2, n, lab), 2) for lab in QL} for n in NS} for d_ in DISTS},
        best=best.round(3).to_dict("records"),
        max_theory_gap_pct_capped=float((df.rmse_pct - df.theory_rmse_pct)[df.cap != "上限なし"].abs().max()),
        max_theory_gap_pct_nocap=float((df.rmse_pct - df.theory_rmse_pct)[df.cap == "上限なし"].abs().max()),
        same_best_cap_sim_vs_theory=int((best.cap == best.cap_theory).sum()), n_cells=int(len(best)),
        load_err={d_.name: {str(le): {lab: round(float(le_df[(le_df.dist == d_.name) & (le_df.load_err == le) & (le_df.cap == lab)].mean_err_pct.iloc[0]), 2) for lab in QL} for le in (-0.2, 0.2)} for d_ in DISTS})
    json.dump(main_js, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

    D1 = DISTS[1].name
    # 図1：上限の高さと RMSE（対数正規σ=2.0、全体との違い2割）
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))
    cols = [GRAY, LIGHT, BLUE, ORANGE, GREEN]
    for n, col in zip(NS, cols):
        v = [val(D1, 0.2, n, lab) for lab in QL]
        ax[0].plot(range(len(QL)), v, "-o", color=col, lw=1.8, ms=4, label=f"{n:,}契約")
        k = int(np.argmin(v)); ax[0].plot(k, v[k], "o", ms=11, mfc="none", mec=col, mew=1.6)
    ax[0].set_xticks(range(len(QL))); ax[0].set_xticklabels(QL, fontsize=8, rotation=30); ax[0].set_yscale("log")
    ax[0].set_ylabel("見込みのずれ（RMSE、全体の見込みに対する%）"); ax[0].set_xlabel("1事故の上限の高さ")
    ax[0].set_title("上限の高さとずれ（丸で囲んだ点が最小）", loc="left"); ax[0].legend(fontsize=8, frameon=False)
    n = 10000
    nz = [val(D1, 0.2, n, lab, "theory_noise_pct") for lab in QL]; bs = [val(D1, 0.2, n, lab, "theory_bias_pct") for lab in QL]
    ax[1].plot(range(len(QL)), nz, "-o", color=BLUE, lw=1.8, ms=4, label="振れ（実績の偶然の出入り）")
    ax[1].plot(range(len(QL)), bs, "-o", color=ORANGE, lw=1.8, ms=4, label="偏り（全体の数字で置き換えた分）")
    ax[1].plot(range(len(QL)), [val(D1, 0.2, n, lab) for lab in QL], "--", color=INK, lw=1.2, label="合わせたずれ（シミュレーション）")
    ax[1].set_xticks(range(len(QL))); ax[1].set_xticklabels(QL, fontsize=8, rotation=30); ax[1].set_xlabel("1事故の上限の高さ")
    ax[1].set_ylabel("ずれ（全体の見込みに対する%）"); ax[1].set_title("1万契約のとき：振れと偏りの入れ替わり", loc="left"); ax[1].legend(fontsize=8, frameon=False)
    fig.suptitle(f"{D1}、自分の集まりの事故の頻度が全体と2割ほど違う場合", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(); save(fig, "a457_rmse_by_cap.png", SRC)

    # 図2：いちばんずれが小さい上限（分布×契約の数×全体との違い）
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.0), sharey=True)
    for a, d_ in zip(ax, DISTS):
        M = np.array([[QL.index(best[(best.dist == d_.name) & (best.cv == cv) & (best.n == n)].cap.iloc[0]) for n in NS] for cv in (0.0, 0.1, 0.2, 0.4)])
        im = a.imshow(M, cmap="Blues", vmin=0, vmax=len(QL) - 1, aspect="auto")
        for i in range(4):
            for j in range(len(NS)):
                a.text(j, i, QL[M[i, j]], ha="center", va="center", fontsize=8.5, color="white" if M[i, j] > 5 else INK)
        a.set_xticks(range(len(NS))); a.set_xticklabels([f"{n:,}" for n in NS], fontsize=8); a.set_xlabel("契約の数")
        a.set_yticks(range(4)); a.set_yticklabels(["違いなし", "1割", "2割", "4割"]); a.set_title(d_.name, loc="left", fontsize=11)
        for s_ in a.spines.values(): s_.set_visible(False)
    ax[0].set_ylabel("自分の集まりと全体の違い")
    fig.suptitle("ずれがいちばん小さかった上限の高さ", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(); save(fig, "a457_best_cap_grid.png", SRC)

    # 図3：上限なしと比べたずれの小ささ、上乗せを読み違えたときの偏り
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.3))
    x = np.arange(len(NS)); w = 0.26
    for k, (d_, col) in enumerate(zip(DISTS, (LIGHT, BLUE, ORANGE))):
        b = best[(best.dist == d_.name) & (best.cv == 0.2)].set_index("n").loc[NS]
        ax[0].bar(x + (k - 1) * w, b.rmse_ratio * 100, w, color=col, label=d_.name)
        for xi, vi in zip(x + (k - 1) * w, b.rmse_ratio * 100): ax[0].text(xi, vi + 1.5, f"{vi:.0f}", ha="center", fontsize=7.5)
    ax[0].axhline(100, color=INK, lw=0.8, ls=":"); ax[0].set_xticks(x); ax[0].set_xticklabels([f"{n:,}" for n in NS]); ax[0].set_xlabel("契約の数")
    ax[0].set_ylabel("いちばんよい上限でのずれ（上限なし＝100、式の値）"); ax[0].set_title("上限を置くと、ずれはどこまで小さくなるか（違い2割）", loc="left", fontsize=11); ax[0].legend(fontsize=8, frameon=False)
    for le, ls in ((-0.2, "--"), (0.2, "-")):
        for d_, col in zip(DISTS, (LIGHT, BLUE, ORANGE)):
            v = [float(le_df[(le_df.dist == d_.name) & (le_df.load_err == le) & (le_df.cap == lab)].mean_err_pct.iloc[0]) for lab in QL]
            ax[1].plot(range(len(QL)), v, ls, color=col, lw=1.6, label=f"{d_.name}・上乗せを{'2割大きく' if le > 0 else '2割小さく'}読んだ")
    ax[1].axhline(0, color=INK, lw=0.8); ax[1].set_xticks(range(len(QL))); ax[1].set_xticklabels(QL, fontsize=8, rotation=30)
    ax[1].set_ylabel("見込みの偏り（全体の見込みに対する%）"); ax[1].set_xlabel("1事故の上限の高さ")
    ax[1].set_title("上乗せの見積もりを読み違えたとき", loc="left", fontsize=11); ax[1].legend(fontsize=7, frameon=False)
    fig.tight_layout(); save(fig, "a457_gain_and_load_error.png", SRC)

    print({k: main_js[k] for k in ("max_theory_gap_pct_capped", "max_theory_gap_pct_nocap", "same_best_cap_sim_vs_theory", "n_cells")})
    for d_ in DISTS:
        print(d_.name); print(df[(df.dist == d_.name) & (df.cv == 0.2)].pivot(index="n", columns="cap", values="rmse_pct")[QL].round(1).to_string())
    print(df[(df.dist == D1) & (df.n == 10000)].pivot(index="cv", columns="cap", values="rmse_pct")[QL].round(1).to_string())
    print(best.round(2).to_string())
    print(pd.DataFrame(dec)[lambda t: (t.n == 10000)].round(2).to_string())


if __name__ == "__main__":
    main()
