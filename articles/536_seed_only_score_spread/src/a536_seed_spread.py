"""536 乱数の種を変えるだけで、同じモデルの検証の成績は何ポイント揺れるのか（機械学習・検証）

架空の2値分類データ（データ自体と学習・検証の分け方は固定）。
- 件数 n = 500・2,000・8,000、特徴量の数 p = 10・40（うち効くのは5個、残りは雑音）
- 学習 70%・検証 30%（層別、分け方は固定）
- モデル：ランダムフォレスト（100本）と勾配ブースティング（sklearn の HistGradientBoosting、行と特徴量を抜き出して学習）
- 変えるのはモデルの乱数の種だけ（30通り）。データ・分け方・ハイパーパラメータは同じ
- 「設定A と 設定B」：RF は max_features 'sqrt' と 0.5、GB は学習率 0.1 と 0.05。同じ種どうしで比べ、勝ち負けが入れ替わる割合を見る
追加：分け方の種も変えた場合（30通り）と比べる。乱数の種 536。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の2値分類データ（作成者が乱数で作成、seed 536）"
NS = [500, 2000, 8000]
PS = [10, 40]
SEEDS = list(range(30))


def make_data(n, p, seed):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, p))
    z = 1.0 * X[:, 0] - 0.8 * X[:, 1] + 0.6 * X[:, 2] * X[:, 3] + 0.5 * np.sin(2 * X[:, 4]) - 0.3
    y = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(int)
    return X, y


def model(kind, setting, seed):
    if kind == "RF":
        return RandomForestClassifier(n_estimators=100, max_features="sqrt" if setting == "A" else 0.5,
                                      min_samples_leaf=3, random_state=seed, n_jobs=1)
    return HistGradientBoostingClassifier(learning_rate=0.1 if setting == "A" else 0.05, max_iter=150,
                                          max_leaf_nodes=15, max_features=0.5, early_stopping=False,
                                          random_state=seed)


def fit_score(kind, setting, seed, Xtr, ytr, Xva, yva):
    m = model(kind, setting, seed).fit(Xtr, ytr)
    pr = m.predict_proba(Xva)[:, 1]
    return roc_auc_score(yva, pr), accuracy_score(yva, (pr >= 0.5).astype(int))


def main():
    rows = []
    for n in NS:
        for p in PS:
            X, y = make_data(n, p, 536 + n + p)
            Xtr, Xva, ytr, yva = train_test_split(X, y, test_size=0.3, stratify=y, random_state=536)
            for kind in ["RF", "GB"]:
                for st in ["A", "B"]:
                    for s in SEEDS:
                        auc, acc = fit_score(kind, st, s, Xtr, ytr, Xva, yva)
                        rows.append(dict(scheme="model_seed", n=n, p=p, model=kind, setting=st, seed=s, auc=auc, acc=acc))
    # 追加：n=2000, p=10 で分け方の種も変える
    n, p = 2000, 10
    X, y = make_data(n, p, 536 + n + p)
    for s in SEEDS:
        Xtr, Xva, ytr, yva = train_test_split(X, y, test_size=0.3, stratify=y, random_state=1000 + s)
        for kind in ["RF", "GB"]:
            for st in ["A", "B"]:
                auc, acc = fit_score(kind, st, s, Xtr, ytr, Xva, yva)
                rows.append(dict(scheme="split_and_model_seed", n=n, p=p, model=kind, setting=st, seed=s, auc=auc, acc=acc))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "scores.csv", index=False, float_format="%.6f")

    # 揺れの幅
    g = df.groupby(["scheme", "n", "p", "model", "setting"])
    spread = g.agg(auc_mean=("auc", "mean"), auc_sd=("auc", "std"), auc_min=("auc", "min"), auc_max=("auc", "max"),
                   acc_mean=("acc", "mean"), acc_sd=("acc", "std"), acc_min=("acc", "min"), acc_max=("acc", "max")).reset_index()
    spread["auc_range_pt"] = (spread.auc_max - spread.auc_min) * 100
    spread["acc_range_pt"] = (spread.acc_max - spread.acc_min) * 100
    # 入れ替わり：同じ種どうしで A と B を比べる
    w = df.pivot_table(index=["scheme", "n", "p", "model", "seed"], columns="setting", values="auc").reset_index()
    w["a_better"] = w.A > w.B
    flip = w.groupby(["scheme", "n", "p", "model"]).agg(share_a_better=("a_better", "mean"),
                                                         mean_diff_pt=("A", lambda s: 0)).reset_index()
    md = w.assign(d=(w.A - w.B) * 100).groupby(["scheme", "n", "p", "model"]).d.agg(["mean", "std"]).reset_index()
    flip["mean_diff_pt"] = md["mean"].values
    flip["sd_diff_pt"] = md["std"].values
    flip["flip_share"] = np.minimum(flip.share_a_better, 1 - flip.share_a_better)
    # 1回だけ比べて「勝ったほうを選ぶ」と、30回の平均で負けているほうを選んでしまう割合
    flip["wrong_pick_share"] = np.where(flip.mean_diff_pt > 0, 1 - flip.share_a_better, flip.share_a_better)
    summary = spread.merge(flip[["scheme", "n", "p", "model", "share_a_better", "mean_diff_pt", "sd_diff_pt", "flip_share", "wrong_pick_share"]],
                           on=["scheme", "n", "p", "model"])
    summary.to_csv(RES / "summary.csv", index=False, float_format="%.6f")
    json.dump({"rows": summary.round(6).to_dict("records")}, open(RES / "a536_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：n=2000, p=10 の AUC の分布（種だけ変える）
    sub = df[(df.scheme == "model_seed") & (df.n == 2000) & (df.p == 10)]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    pos = 0
    labels = []
    for kind, nm in [("RF", "ランダムフォレスト"), ("GB", "勾配ブースティング")]:
        for st, col in [("A", BLUE), ("B", ORANGE)]:
            v = sub[(sub.model == kind) & (sub.setting == st)].auc.values * 100
            jit = np.linspace(-0.18, 0.18, len(v))
            ax.scatter(pos + jit, np.sort(v), s=14, color=col, alpha=0.85)
            ax.plot([pos - 0.25, pos + 0.25], [v.mean()] * 2, color=INK, lw=1.5)
            labels.append(f"{nm}\n設定{st}")
            pos += 1
    ax.set_xticks(range(pos)); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("検証の AUC（×100）")
    ax.set_title("同じデータ・同じ設定でも、種だけで AUC はこれだけ散らばる（2,000件・特徴量10）")
    save(fig, "a536_auc_by_seed.png", SRC + "。点は種30通り、黒い線は平均")

    # 図2：件数と揺れの幅（AUC の最大−最小）
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    ms = spread[(spread.scheme == "model_seed") & (spread.setting == "A")]
    for ax, kind, nm in [(axs[0], "RF", "ランダムフォレスト"), (axs[1], "GB", "勾配ブースティング")]:
        for p, col in [(10, BLUE), (40, ORANGE)]:
            s = ms[(ms.model == kind) & (ms.p == p)].sort_values("n")
            ax.plot(s.n, s.auc_range_pt, "o-", color=col, label=f"特徴量 {p}")
            ax.plot(s.n, s.acc_range_pt, "o--", color=col, alpha=0.5, label=f"特徴量 {p}（正解率）")
        ax.set_xscale("log"); ax.minorticks_off(); ax.set_xticks(NS); ax.set_xticklabels([f"{n:,}" for n in NS])
        ax.set_title(nm); ax.set_xlabel("件数（検証はその30%）")
    axs[0].set_ylabel("種30通りでの最大−最小（ポイント）")
    axs[1].legend(fontsize=8, frameon=False)
    fig.suptitle("件数が少ないほど、種による揺れは大きい（実線 AUC・点線 正解率、設定A）", y=1.02)
    save(fig, "a536_range_by_n.png", SRC)

    # 図3：A と B の差の分布（入れ替わり）
    fig, ax = plt.subplots(figsize=(8, 4))
    fm = flip[flip.scheme == "model_seed"].copy()
    fm["lab"] = fm.model.map({"RF": "RF", "GB": "GB"}) + "・" + fm.n.map(lambda v: f"{v:,}件") + "・特徴量" + fm.p.astype(str)
    fm = fm.sort_values(["model", "p", "n"])
    y = np.arange(len(fm))
    ax.barh(y, fm.flip_share * 100, color=[BLUE if m == "RF" else GREEN for m in fm.model])
    for yi, (fs, d) in enumerate(zip(fm.flip_share, fm.mean_diff_pt)):
        ax.text(fs * 100 + 1, yi, f"{fs*100:.0f}%（平均の差 {d:+.2f}pt）", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(fm.lab, fontsize=8)
    ax.set_xlim(0, 65); ax.axvline(50, color=GRAY, ls=":")
    ax.set_xlabel("「設定Aのほうが良い」が種で入れ替わる割合（%）")
    ax.set_title("同じ種どうしで設定AとBの AUC を比べたとき、少数派の結果が出る割合")
    save(fig, "a536_flip_share.png", SRC + "。50%なら勝ち負けは五分五分")

    print(summary[["scheme", "n", "p", "model", "setting", "auc_mean", "auc_range_pt", "acc_range_pt", "auc_sd", "flip_share", "mean_diff_pt", "sd_diff_pt"]].to_string())


if __name__ == "__main__":
    main()
