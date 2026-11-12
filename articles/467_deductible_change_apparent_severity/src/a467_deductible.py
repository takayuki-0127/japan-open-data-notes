"""467 免責金額を上げた年をまたいで平均の支払額を比べると、損害が同じでも何%上がって見えるか（架空の損害、seed 467）"""
import json
import numpy as np, pandas as pd
from scipy import stats, integrate
from common import *

SEED = 467
LAM = 0.10                 # 1契約あたり年の事故の件数（元の損害）
SRC = "架空の損害（作成者が乱数で作成、seed 467）"
DEDS = [0, 50_000, 100_000, 200_000]


class LogN:
    name = "対数正規（中央値15万円・σ=1.2）"
    def __init__(self, med=150_000, sigma=1.2): self.mu, self.s = np.log(med), sigma
    def mean(self): return np.exp(self.mu + self.s ** 2 / 2)
    def sf(self, d): return 1.0 if d <= 0 else float(stats.norm.sf((np.log(d) - self.mu) / self.s))
    def lev(self, d):          # E[min(X,d)]
        if d <= 0: return 0.0
        z = (np.log(d) - self.mu) / self.s
        return float(self.mean() * stats.norm.cdf(z - self.s) + d * stats.norm.sf(z))
    def draw(self, rng, n): return rng.lognormal(self.mu, self.s, n)
    def scaled(self, k): return LogN(np.exp(self.mu) * k, self.s)


class Lomax:
    name = "パレート型（α=2.5、平均は同じ）"
    def __init__(self, mean, alpha=2.5): self.a, self.th = alpha, mean * (alpha - 1)
    def mean(self): return self.th / (self.a - 1)
    def sf(self, d): return float((1 + max(d, 0) / self.th) ** (-self.a))
    def lev(self, d): return float(self.mean() * (1 - (1 + max(d, 0) / self.th) ** (1 - self.a)))
    def draw(self, rng, n): return self.th * ((1 - rng.random(n)) ** (-1 / self.a) - 1)
    def scaled(self, k): return Lomax(self.mean() * k, self.a)


def stats_at(D, d):
    """免責 d のときの、支払いのある事故の割合・1件あたり支払額・契約あたり支払額・足し戻した平均"""
    p = D.sf(d); pay = D.mean() - D.lev(d)
    return dict(支払いのある割合=p, 件数=LAM * p, 一件あたり=pay / p, 契約あたり=LAM * pay, 足し戻し=pay / p + d)


def table(D):
    rows = []
    for d in DEDS:
        s = stats_at(D, d); rows.append(dict(分布=D.name, 免責=d, **{k: round(v, 4) if v < 10 else round(v, 1) for k, v in s.items()}))
    return rows


def steps(D):
    rows = []
    for a, b in [(0, 50_000), (50_000, 100_000), (100_000, 200_000), (0, 100_000), (0, 200_000)]:
        sa, sb = stats_at(D, a), stats_at(D, b)
        rows.append(dict(分布=D.name, 前の免責=a, 後の免責=b,
                         件数の変化=round((sb["件数"] / sa["件数"] - 1) * 100, 1), 一件あたりの変化=round((sb["一件あたり"] / sa["一件あたり"] - 1) * 100, 1),
                         契約あたりの変化=round((sb["契約あたり"] / sa["契約あたり"] - 1) * 100, 1),
                         足し戻したあとの変化=round((sb["足し戻し"] / sa["足し戻し"] - 1) * 100, 1),
                         同じ免責で切り直したあとの変化=0.0))
    return rows


def inflation(D, g=0.03):
    """損害が一律に g 上がり、免責は据え置きのとき"""
    D2 = D.scaled(1 + g); rows = []
    for d in DEDS:
        a, b = stats_at(D, d), stats_at(D2, d)
        rows.append(dict(分布=D.name, 免責=d, 損害の上がり=g * 100, 件数の変化=round((b["件数"] / a["件数"] - 1) * 100, 2),
                         一件あたりの変化=round((b["一件あたり"] / a["一件あたり"] - 1) * 100, 2), 契約あたりの変化=round((b["契約あたり"] / a["契約あたり"] - 1) * 100, 2)))
    return rows


def both(D, g=0.03):
    """損害が g 上がった年に、免責も上げた場合。見かけと、切り直したあと"""
    D2 = D.scaled(1 + g); rows = []
    for a, b in [(0, 50_000), (50_000, 100_000), (100_000, 200_000)]:
        sa, sb, sa_cut = stats_at(D, a), stats_at(D2, b), stats_at(D, b)
        rows.append(dict(分布=D.name, 前の免責=a, 後の免責=b, 損害の上がり=g * 100,
                         見かけの一件あたり=round((sb["一件あたり"] / sa["一件あたり"] - 1) * 100, 1),
                         見かけの契約あたり=round((sb["契約あたり"] / sa["契約あたり"] - 1) * 100, 1),
                         切り直した一件あたり=round((sb["一件あたり"] / sa_cut["一件あたり"] - 1) * 100, 2),
                         切り直した契約あたり=round((sb["契約あたり"] / sa_cut["契約あたり"] - 1) * 100, 2)))
    return rows


def simulate(D, rng, n_pol, reps=1000):
    """契約 n_pol 件の2年分。免責を 5万→10万円に上げたときの、1件あたり支払額の変化の散らばり（損害は同じ）"""
    out = []
    for _ in range(reps):
        x1 = D.draw(rng, rng.poisson(n_pol * LAM)); x2 = D.draw(rng, rng.poisson(n_pol * LAM))
        p1 = x1[x1 > 50_000] - 50_000; p2 = x2[x2 > 100_000] - 100_000
        cut = x1[x1 > 100_000] - 100_000          # 前の年を、後の年と同じ免責で切り直す
        out.append((p2.mean() / p1.mean() - 1, p2.mean() / cut.mean() - 1, len(p2) / len(p1) - 1, p2.sum() / p1.sum() - 1, p2.sum() / cut.sum() - 1))
    return np.array(out) * 100


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    L = LogN(); P = Lomax(L.mean())
    # 式の確かめ：シミュレーション（200万事故）と比べる
    chk = []
    for D in (L, P):
        x = D.draw(rng, 2_000_000)
        for d in DEDS:
            s = stats_at(D, d); pay = np.maximum(x - d, 0)
            chk.append(dict(分布=D.name, 免責=d, 式_一件あたり=round(s["一件あたり"]), 乱数_一件あたり=round(pay[pay > 0].mean()),
                            式_支払いのある割合=round(s["支払いのある割合"], 4), 乱数_支払いのある割合=round((pay > 0).mean(), 4)))
    pd.DataFrame(chk).to_csv(RES / "formula_check.csv", index=False)
    lv = pd.DataFrame(table(L) + table(P)); lv.to_csv(RES / "levels_by_deductible.csv", index=False)
    st = pd.DataFrame(steps(L) + steps(P)); st.to_csv(RES / "apparent_change.csv", index=False)
    inf = pd.DataFrame(inflation(L) + inflation(P) + inflation(L, 0.10)); inf.to_csv(RES / "inflation_leverage.csv", index=False)
    bo = pd.DataFrame(both(L) + both(P)); bo.to_csv(RES / "inflation_and_deductible.csv", index=False)
    sims = {}
    rows = []
    for n in (2_000, 20_000, 200_000):
        s = simulate(L, rng, n); sims[n] = s
        rows.append(dict(契約数=n, 見かけの変化_平均=round(s[:, 0].mean(), 1), 見かけの変化_標準偏差=round(s[:, 0].std(), 1),
                         切り直したあと_平均=round(s[:, 1].mean(), 1), 切り直したあと_標準偏差=round(s[:, 1].std(), 1),
                         切り直したあと_5ポイント以上ずれた割合=round(np.mean(np.abs(s[:, 1]) >= 5) * 100, 1),
                         契約あたり_切り直したあと_標準偏差=round(s[:, 4].std(), 1)))
    sm = pd.DataFrame(rows); sm.to_csv(RES / "sampling_noise.csv", index=False)
    ex = L.draw(np.random.default_rng(SEED + 1), 30)
    pd.DataFrame({"元の損害": np.round(ex), "免責5万円の支払い": np.round(np.maximum(ex - 50_000, 0)), "免責10万円の支払い": np.round(np.maximum(ex - 100_000, 0))}).to_csv(DATA / "example_claims.csv", index=False)

    # 図1：免責を上げたときの見かけの変化
    d = st[(st.分布 == L.name)].iloc[:3]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    for ax, dd, ttl in [(axes[0], st[st.分布 == L.name].iloc[:3], L.name), (axes[1], st[st.分布 == P.name].iloc[:3], P.name)]:
        x = np.arange(3); w = 0.27
        for i, (c, lab, col) in enumerate([("件数の変化", "支払いのある事故の件数", GRAY), ("一件あたりの変化", "1件あたりの支払額", ORANGE), ("契約あたりの変化", "契約あたりの支払額", BLUE)]):
            b = ax.bar(x + (i - 1) * w, dd[c], w, color=col, label=lab)
            for r in b: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + (1 if r.get_height() >= 0 else -4.5), f"{r.get_height():+.0f}", ha="center", fontsize=8)
        ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(["0→5万円", "5万→10万円", "10万→20万円"]); ax.set_title(ttl, fontsize=11)
        ax.set_ylim(-50, 60)
    axes[0].set_ylabel("前の年からの変化（%）"); axes[0].legend(frameon=False, fontsize=9, loc="lower left")
    fig.suptitle("免責金額を上げた年の、見かけの変化（元の損害は同じ）", y=1.02)
    save(fig, "a467_apparent_change.png", SRC + "。式の値")
    # 図2：補正
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    dd = st[st.分布 == L.name].iloc[:3]; x = np.arange(3); w = 0.27
    ax = axes[0]
    for i, (c, lab, col) in enumerate([("一件あたりの変化", "そのまま比べる", ORANGE), ("足し戻したあとの変化", "免責を足し戻して比べる", LIGHT), ("同じ免責で切り直したあとの変化", "前の年を同じ免責で切り直す", GREEN)]):
        b = ax.bar(x + (i - 1) * w, dd[c], w, color=col, label=lab)
        for r in b: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.8, f"{r.get_height():+.0f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(["0→5万円", "5万→10万円", "10万→20万円"]); ax.set_ylabel("1件あたりの額の変化（%）。0が正しい"); ax.legend(frameon=False, fontsize=8.5); ax.set_title("3つの比べ方（対数正規）", fontsize=11)
    ax = axes[1]
    bins = np.linspace(-40, 60, 51)
    for n, col in [(2_000, LIGHT), (20_000, BLUE)]:
        ax.hist(np.clip(sims[n][:, 1], -40, 60), bins=bins, color=col, alpha=0.75, label=f"契約 {n:,}件（標準偏差 {sims[n][:,1].std():.0f}ポイント）")
    ax.axvline(0, color=INK, lw=1); ax.set_xlabel("切り直したあとの、1件あたりの支払額の変化（%）"); ax.set_ylabel("回数（1,000回のうち）"); ax.set_ylim(0, 140); ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("切り直しても残る、偶然の振れ（5万→10万円）", fontsize=11)
    save(fig, "a467_corrections.png", SRC)
    # 図3：損害が3%上がったとき
    fig, ax = plt.subplots(figsize=(8.4, 4.2)); x = np.arange(4); w = 0.2
    for i, (D, g, col, lab) in enumerate([(L, 3.0, BLUE, "対数正規：契約あたりの支払額"), (P, 3.0, ORANGE, "パレート型：契約あたりの支払額")]):
        dd = inf[(inf.分布 == D.name) & (inf.損害の上がり == g)]
        b = ax.bar(x + (i - 1.5) * w, dd.契約あたりの変化, w, color=col, label=lab)
        for r in b: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.05, f"{r.get_height():.1f}", ha="center", fontsize=8)
        b = ax.bar(x + (i + 0.5) * w, dd.一件あたりの変化, w, color=col, alpha=0.4, label=lab.replace("契約あたりの支払額", "1件あたりの支払額"))
        for r in b: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.05, f"{r.get_height():.1f}", ha="center", fontsize=8)
    ax.axhline(3, color=INK, lw=1, ls="--"); ax.text(3.45, 3.06, "損害の上がり 3%", fontsize=8.5, ha="right")
    ax.set_xticks(x); ax.set_xticklabels(["免責なし", "5万円", "10万円", "20万円"]); ax.set_ylabel("支払額の変化（%）"); ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left"); ax.set_ylim(0, 6.2)
    ax.set_title("損害が一律に3%上がり、免責を据え置いたとき")
    save(fig, "a467_inflation_leverage.png", SRC + "。式の値")

    main = {"mean_loss": round(L.mean()), "levels_lognormal": lv[lv.分布 == L.name].to_dict("records"), "steps": st.to_dict("records"),
            "inflation": inf.to_dict("records"), "both": bo.to_dict("records"), "noise": sm.to_dict("records")}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    for t in (lv, st, inf, bo, sm, pd.DataFrame(chk)): print(t.to_string(), "\n")
