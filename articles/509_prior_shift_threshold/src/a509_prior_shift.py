"""509 起きる割合が学習のときから変わると、0.5で切る予測は何件を見逃し、確率はどれだけ外れるのか

架空の分類データ。起きた例（1）と起きなかった例（0）で、5つの特徴の平均が少しずつ違う（中身の分布は学習と本番で同じ）。
変わるのは「起きる割合」だけ（学習 1% → 本番 2%・3%・5%、学習 30% → 本番 15%・45%）。
学習データでロジスティック回帰を作り、本番の10万件で次の3通りを比べる。
  ① 0.5で切る（学習のときのまま）
  ② しきい値を直す：本番で「起きる」と出す件数が、本番の割合（推定値）と同じになるように切る
  ③ 確率を直す：本番の割合を推定し、確率を割合の比で直してから0.5で切る
本番の割合は、正解を見ずに、予測した確率だけから推定する（EM法、Saerens ら 2002 の方法）。
"""
import json
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 509
SRC = "架空の分類データ（作成者が乱数で作成、seed 509）"
D = np.array([1.5, 1.2, 1.0, 0.8, 0.6])     # 起きた例の特徴の平均のずれ（標準偏差1）
N_TR, N_TE = 200_000, 100_000
SCEN = [(0.01, 0.01), (0.01, 0.02), (0.01, 0.03), (0.01, 0.05), (0.30, 0.30), (0.30, 0.15), (0.30, 0.45)]


def draw(n, rate, rng):
    y = (rng.random(n) < rate).astype(int)
    x = rng.standard_normal((n, len(D))) + y[:, None] * D
    return x, y


def adjust(p, tr, new):
    """割合の比で確率を直す（中身の分布が同じとき）"""
    a = p * new / tr; b = (1 - p) * (1 - new) / (1 - tr)
    return a / (a + b)


def em_rate(p, tr, it=200):
    new = tr
    for _ in range(it):
        new = adjust(p, tr, new).mean()
    return new


def evaluate(pred, y, prob):
    return dict(miss=int(((pred == 0) & (y == 1)).sum()), false_alarm=int(((pred == 1) & (y == 0)).sum()),
                hit=int(((pred == 1) & (y == 1)).sum()), flagged=int(pred.sum()), mean_prob=float(prob.mean()))


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for tr, new in SCEN:
        xtr, ytr = draw(N_TR, tr, rng)
        m = LogisticRegression(C=1e6, max_iter=1000).fit(xtr, ytr)
        xte, yte = draw(N_TE, new, rng)
        p = m.predict_proba(xte)[:, 1]
        est = em_rate(p, ytr.mean())
        p_adj = adjust(p, ytr.mean(), est)
        thr = np.quantile(p, 1 - est)
        p_known = adjust(p, ytr.mean(), yte.mean())
        base = dict(train_rate=tr, test_rate=new, actual_test_rate=float(yte.mean()), est_rate=float(est), positives=int(yte.sum()))
        for name, pred, prob in [("① 0.5で切る", (p >= 0.5).astype(int), p),
                                 ("② しきい値を直す", (p >= thr).astype(int), p),
                                 ("③ 確率を直す", (p_adj >= 0.5).astype(int), p_adj),
                                 ("参考：本当の割合で確率を直す", (p_known >= 0.5).astype(int), p_known)]:
            r = evaluate(pred, yte, prob); r.update(base); r["method"] = name
            r["prob_gap_pt"] = (r["mean_prob"] - r["actual_test_rate"]) * 100
            rows.append(r)
    df = pd.DataFrame(rows)
    df.round(5).to_csv(RES / "methods_by_scenario.csv", index=False)
    show = df[["train_rate", "test_rate", "positives", "est_rate", "method", "miss", "false_alarm", "hit", "flagged", "mean_prob", "prob_gap_pt"]]
    print(show.round(4).to_string(index=False))
    out = dict(seed=SEED, n_train=N_TR, n_test=N_TE, shift_D=D.tolist(),
               rows=show.round(4).to_dict("records"))
    json.dump(out, open(RES / "a509_main.json", "w"), ensure_ascii=False, indent=1)

    meth = ["① 0.5で切る", "② しきい値を直す", "③ 確率を直す"]
    cols = [GRAY, BLUE, ORANGE]
    # 図1：学習1%→本番5% と 学習30%→本番15% の見逃し・空振り
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.2))
    for ax, (tr, new) in zip(axs, [(0.01, 0.05), (0.30, 0.15)]):
        d = df[(df.train_rate == tr) & (df.test_rate == new)].set_index("method").loc[meth]
        xs = np.arange(3); w = 0.38
        ax.bar(xs - w / 2, d.miss, w, color=ORANGE, label="見逃し（起きたのに出さない）")
        ax.bar(xs + w / 2, d.false_alarm, w, color=LIGHT, label="空振り（起きないのに出す）")
        for i, (a, b) in enumerate(zip(d.miss, d.false_alarm)):
            ax.text(i - w / 2, a, f"{a:,}", ha="center", va="bottom", fontsize=8.5); ax.text(i + w / 2, b, f"{b:,}", ha="center", va="bottom", fontsize=8.5)
        ax.set_xticks(xs, [m.replace(" ", "\n", 1) for m in meth], fontsize=9)
        ax.set_title(f"学習 {tr*100:g}% → 本番 {new*100:g}%（起きた {int(d.positives.iloc[0]):,}件）", fontsize=11)
    axs[0].set_ylabel("件数（本番10万件のうち）"); axs[0].legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.suptitle("割合が変わったとき、切り方で見逃しと空振りが入れ替わる", fontsize=13, y=1.03)
    save(fig, "a509_miss_fa.png", SRC + "。本番の割合は正解を見ずに推定")

    # 図2：学習1%のモデルで、本番の割合を変えたときの見逃し
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for mname, c in zip(meth, cols):
        d = df[(df.train_rate == 0.01) & (df.method == mname)].sort_values("test_rate")
        ax.plot(d.test_rate * 100, d.miss / d.positives * 100, "o-", color=c, lw=2, label=mname)
    ax.set_xlabel("本番で起きる割合（%）"); ax.set_ylabel("起きた例のうち見逃した割合（%）"); ax.set_ylim(0, 100)
    ax.set_title("学習1%のまま0.5で切ると、起きた例の4分の3以上を見逃す")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a509_miss_rate.png", SRC + "。学習データで起きる割合は1%")

    # 図3：予測した確率の平均と本当の割合
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    sc = [s for s in SCEN]
    labs = [f"{tr*100:g}%\n→{new*100:g}%" for tr, new in sc]
    raw = [df[(df.train_rate == tr) & (df.test_rate == new) & (df.method == "① 0.5で切る")].mean_prob.iloc[0] * 100 for tr, new in sc]
    adj = [df[(df.train_rate == tr) & (df.test_rate == new) & (df.method == "③ 確率を直す")].mean_prob.iloc[0] * 100 for tr, new in sc]
    act = [df[(df.train_rate == tr) & (df.test_rate == new)].actual_test_rate.iloc[0] * 100 for tr, new in sc]
    xs = np.arange(len(sc)); w = 0.27
    ax.bar(xs - w, act, w, color=INK, label="本番で本当に起きた割合")
    ax.bar(xs, raw, w, color=GRAY, label="予測した確率の平均（直す前）")
    ax.bar(xs + w, adj, w, color=ORANGE, label="予測した確率の平均（③で直した後）")
    ax.set_xticks(xs, labs); ax.set_xlabel("学習の割合 → 本番の割合"); ax.set_ylabel("%")
    ax.set_title("直す前の確率の平均は、学習のときの割合の側に引っぱられる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a509_prob_mean.png", SRC + "。本番10万件")


if __name__ == "__main__":
    main()
