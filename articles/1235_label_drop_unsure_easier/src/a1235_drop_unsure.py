"""1235 迷った件を「分からない」として除くと、残ったデータで作った分類はどれだけ易しい問題になるのか？（架空のデータ）

架空の問い合わせ文。件ごとに本当の分類（「返品の相談」か「それ以外」か）と、文から取れる2つの手がかりの値を作成者が置く。
付け手は、手がかりから見た「返品の相談らしさ」に自分の見え方のぶれを足して判断し、どちらとも言いにくい件を「分からない」として除く。
残った件で分類する仕組み（2つの手がかりの重み付きの和で分ける）を作り、残った件で確かめた正しさと、実際に来る件全体での正しさを比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1235
SRC = "架空の問い合わせ文と付け手（作成者が置いた返品の相談らしさ・手がかり・見え方のぶれからの乱数、seed 1235）"
C = 0.253347        # 標準の山形の分布で上側40%になる境目（本当の「返品の相談」が40%）
N_TRAIN, N_TEST = 2000, 2000
RATER_SD = 0.3      # 付け手が文を読んだときの見え方のぶれ


def sig(x):
    return 1 / (1 + np.exp(-x))


def make_items(rng, n, cue_sd):
    """本当のらしさ z（z が境目 C を超えたら返品の相談）と、分類する仕組みが見る2つの手がかり x"""
    z = rng.normal(0, 1, n)
    y = (z > C).astype(int)
    x = z[:, None] + rng.normal(0, cue_sd, (n, 2))
    # 手がかりから出せる最善の分け方：手がかりから見込んだ z の中心が境目を超えるか（式で決まる）
    zhat = x.sum(1) / cue_sd ** 2 / (1 + 2 / cue_sd ** 2)
    return x, y, z, (zhat > C).astype(int)


def rate(rng, z, lo, hi):
    """付け手：z にぶれを足して読み、境目から lo〜hi の幅にある件は「分からない」とする"""
    v = z + rng.normal(0, RATER_SD, len(z))
    unsure = (v > C - lo) & (v < C + hi)
    return (v > C).astype(int), unsure


def fit(x, y, lam=1e-3, it=30):
    """重み付きの和で分ける仕組み（対数オッズを直線で当てはめる、わずかな縮め）"""
    X = np.c_[np.ones(len(x)), x]
    w = np.zeros(X.shape[1])
    for _ in range(it):
        p = sig(X @ w)
        g = X.T @ (p - y) + lam * np.r_[0, w[1:]]
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.diag([0] + [1] * (X.shape[1] - 1))
        w -= np.linalg.solve(H + 1e-9 * np.eye(len(w)), g)
    return w


def predict(w, x):
    return sig(np.c_[np.ones(len(x)), x] @ w)


def one_run(rng, cue_sd, lo, hi):
    xtr, ytr, ztr, _ = make_items(rng, N_TRAIN, cue_sd)
    lab_tr, uns_tr = rate(rng, ztr, lo, hi)
    xte, yte, zte, best = make_items(rng, N_TEST, cue_sd)
    lab_te, uns_te = rate(rng, zte, lo, hi)
    keep_tr, keep_te = ~uns_tr, ~uns_te
    w_drop = fit(xtr[keep_tr], lab_tr[keep_tr])            # 除いて作る
    w_all = fit(xtr, lab_tr)                               # 除かずに、迷った件も「どちらかといえば」で入れて作る
    ph, pa = predict(w_drop, xte), predict(w_all, xte)
    pred, pred_all = (ph > 0.5).astype(int), (pa > 0.5).astype(int)
    return {
        "share_unsure": float(uns_tr.mean()),
        "acc_kept_vs_label": float((pred[keep_te] == lab_te[keep_te]).mean()),   # 残った件で、付けた分類と比べる（ふつう見る数字）
        "acc_kept_vs_true": float((pred[keep_te] == yte[keep_te]).mean()),       # 残った件で、本当の分類と比べる
        "acc_all_vs_true": float((pred == yte).mean()),                           # 来る件全体で、本当の分類と比べる
        "acc_unsure_vs_true": float((pred[uns_te] == yte[uns_te]).mean()) if uns_te.any() else np.nan,
        "noexcl_seen": float((pred_all == lab_te).mean()),                        # 除かずに作り、全体で付けた分類と比べる
        "noexcl_all_vs_true": float((pred_all == yte).mean()),                    # 除かずに作り、全体で本当の分類と比べる
        "best_kept": float((best[keep_te] == yte[keep_te]).mean()),              # 手がかりから出せる最善（残った件）
        "best_all": float((best == yte).mean()),                                  # 同（来る件全体）
        "label_err_kept": float((lab_te[keep_te] != yte[keep_te]).mean()),
        "pos_true": float(yte.mean()), "pos_kept_label": float(lab_te[keep_te].mean()),
        "pos_pred_all": float(pred.mean()), "pos_pred_noexcl": float(pred_all.mean()),
        "conf_all": float(np.maximum(ph, 1 - ph).mean()),                         # 仕組みが出す確からしさの平均（来る件全体）
        "conf_noexcl": float(np.maximum(pa, 1 - pa).mean()),
        "w_norm_drop": float(np.linalg.norm(w_drop[1:])), "w_norm_all": float(np.linalg.norm(w_all[1:])),
    }


SETS = {"対称（境目の上下0.4を除く）": (0.4, 0.4), "片寄り（下0.4・上0.8を除く）": (0.4, 0.8)}


def main():
    t0 = time.time()
    m0 = 1.0
    # 1回分のデータ（対称・基本）
    rng = np.random.default_rng(SEED)
    x, y, z, _ = make_items(rng, N_TRAIN, m0)
    lab, uns = rate(rng, z, 0.4, 0.4)
    pd.DataFrame({"item_id": np.arange(1, N_TRAIN + 1), "cue1": x[:, 0].round(4), "cue2": x[:, 1].round(4),
                  "true_label": y, "true_likeliness": z.round(4), "rater_label": np.where(uns, -1, lab)}
                 ).to_csv(DATA / "items_one_set.csv", index=False)

    # 1) 基本（手がかりのぶれ1.0）、対称と片寄り、各200回
    rows, reps = [], []
    for k, (name, (lo, hi)) in enumerate(SETS.items()):
        rs = [one_run(np.random.default_rng(SEED * 1000 + k * 10000 + i), m0, lo, hi) for i in range(200)]
        df = pd.DataFrame(rs)
        df.insert(0, "setting", name); reps.append(df)
        mean = df.drop(columns="setting").mean()
        rows.append({"setting": name, **{c: round(float(v) * (1 if c.startswith("w_norm") else 100), 3 if c.startswith("w_norm") else 2)
                                         for c, v in mean.items()}})
    base = pd.DataFrame(rows)
    base["gap_seen_minus_all"] = (base.acc_kept_vs_label - base.acc_all_vs_true).round(2)
    base["best_kept_minus_all"] = (base.best_kept - base.best_all).round(2)
    base["drop_minus_noexcl"] = (base.acc_all_vs_true - base.noexcl_all_vs_true).round(2)
    base.to_csv(RES / "base.csv", index=False)
    pd.concat(reps).round(4).to_csv(RES / "reps_base.csv", index=False)

    # 2) 確かめ：除く幅 × 手がかりのぶれ × 対称/片寄り（各30回）
    grid = []
    for wi, wd in enumerate([0.1, 0.2, 0.4, 0.6, 0.8]):
        for mi, m in enumerate([0.5, 1.0, 2.0]):
            for k, kind in enumerate(["対称", "片寄り"]):
                lo, hi = (wd, wd) if kind == "対称" else (wd, 2 * wd)
                rs = pd.DataFrame([one_run(np.random.default_rng(SEED * 77 + wi * 100000 + mi * 10000 + k * 1000 + i), m, lo, hi)
                                   for i in range(30)]).mean()
                grid.append({"half_width": wd, "cue_sd": m, "kind": kind, "drop_below": lo, "drop_above": hi,
                             "share_unsure": round(rs.share_unsure * 100, 2),
                             "acc_kept_vs_label": round(rs.acc_kept_vs_label * 100, 2),
                             "acc_all_vs_true": round(rs.acc_all_vs_true * 100, 2),
                             "gap_seen_minus_all": round((rs.acc_kept_vs_label - rs.acc_all_vs_true) * 100, 2),
                             "noexcl_seen": round(rs.noexcl_seen * 100, 2),
                             "noexcl_all_vs_true": round(rs.noexcl_all_vs_true * 100, 2),
                             "acc_kept_vs_true": round(rs.acc_kept_vs_true * 100, 2),
                             "best_kept": round(rs.best_kept * 100, 2), "best_all": round(rs.best_all * 100, 2),
                             "pos_true": round(rs.pos_true * 100, 2), "pos_kept_label": round(rs.pos_kept_label * 100, 2),
                             "pos_pred_all": round(rs.pos_pred_all * 100, 2),
                             "conf_all": round(rs.conf_all * 100, 2), "conf_noexcl": round(rs.conf_noexcl * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    sym, asy = grid[grid.kind == "対称"], grid[grid.kind == "片寄り"]
    rob = {"n_settings": int(len(grid)),
           "gap_range_all": [float(grid.gap_seen_minus_all.min()), float(grid.gap_seen_minus_all.max())],
           "n_gap_positive": int((grid.gap_seen_minus_all > 0).sum()),
           "gap_range_halfwidth01": [float(grid[grid.half_width == 0.1].gap_seen_minus_all.min()), float(grid[grid.half_width == 0.1].gap_seen_minus_all.max())],
           "share_unsure_range": [float(grid.share_unsure.min()), float(grid.share_unsure.max())],
           "best_kept_minus_all_range": [round(float((grid.best_kept - grid.best_all).min()), 2), round(float((grid.best_kept - grid.best_all).max()), 2)],
           "conf_minus_acc_range": [round(float((grid.conf_all - grid.acc_all_vs_true).min()), 2), round(float((grid.conf_all - grid.acc_all_vs_true).max()), 2)],
           "n_conf_over_acc": int((grid.conf_all > grid.acc_all_vs_true).sum()),
           "noexcl_gap_range": [round(float((grid.noexcl_seen - grid.noexcl_all_vs_true).min()), 2), round(float((grid.noexcl_seen - grid.noexcl_all_vs_true).max()), 2)],
           "sym_drop_minus_noexcl_range": [round(float((sym.acc_all_vs_true - sym.noexcl_all_vs_true).min()), 2),
                                           round(float((sym.acc_all_vs_true - sym.noexcl_all_vs_true).max()), 2)],
           "asym_drop_minus_noexcl_range": [round(float((asy.acc_all_vs_true - asy.noexcl_all_vs_true).min()), 2),
                                            round(float((asy.acc_all_vs_true - asy.noexcl_all_vs_true).max()), 2)],
           "asym_n_drop_worse": int((asy.acc_all_vs_true < asy.noexcl_all_vs_true).sum()), "asym_n": int(len(asy)),
           "sym_n_drop_worse": int((sym.acc_all_vs_true < sym.noexcl_all_vs_true).sum()), "sym_n": int(len(sym)),
           "asym_pos_pred_range": [float(asy.pos_pred_all.min()), float(asy.pos_pred_all.max())],
           "sym_pos_pred_range": [float(sym.pos_pred_all.min()), float(sym.pos_pred_all.max())],
           "gap_by_cue": {str(m): [float(grid[grid.cue_sd == m].gap_seen_minus_all.min()),
                                   float(grid[grid.cue_sd == m].gap_seen_minus_all.max())] for m in [0.5, 1.0, 2.0]}}
    out = {"base_200reps": base.to_dict("records"), "robust": rob,
           "setting": {"prev": 0.4, "boundary": C, "n_train": N_TRAIN, "n_test": N_TEST, "rater_sd": RATER_SD, "cue_sd_base": m0},
           "one_set": {"share_unsure": round(float(uns.mean()) * 100, 2), "n_unsure": int(uns.sum())}}
    json.dump(out, open(RES / "a1235_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の件（対称）
    fig, ax = plt.subplots(figsize=(6.8, 5.0))
    ax.scatter(x[uns, 0], x[uns, 1], s=8, color=GRAY, alpha=.6, lw=0, label=f"「分からない」で除いた件（{round(uns.mean()*100, 2):g}%）")
    k1 = (~uns) & (lab == 1); k0 = (~uns) & (lab == 0)
    ax.scatter(x[k0, 0], x[k0, 1], s=8, color=BLUE, alpha=.55, lw=0, label="付けた分類：それ以外")
    ax.scatter(x[k1, 0], x[k1, 1], s=8, color=ORANGE, alpha=.55, lw=0, label="付けた分類：返品の相談")
    ax.set_xlabel("手がかり1（作成者が置いた値）"); ax.set_ylabel("手がかり2（作成者が置いた値）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", markerscale=2.5)
    ax.set_title("除いた件は境目のあたりに集まり、残った2つの分類は離れて見える", fontsize=10.5)
    save(fig, "a1235_scatter.png", SRC + "。1回分の2,000件、境目の上下0.4を除く")

    # 図2：基本の正しさ（対称・片寄り）
    labels = [("acc_kept_vs_label", "残った件で、付けた分類と比べる"), ("acc_kept_vs_true", "残った件で、本当の分類と比べる"),
              ("acc_all_vs_true", "来る件全体で、本当の分類と比べる"), ("best_all", "来る件全体で出せる最善")]
    cols = [LIGHT, GRAY, BLUE, INK]
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    xs = np.arange(len(base)); w_ = 0.2
    for j, ((c, lab_), col) in enumerate(zip(labels, cols)):
        ax.bar(xs + (j - 1.5) * w_, base[c], w_, color=col, label=lab_)
        for xx, v in zip(xs, base[c]):
            ax.text(xx + (j - 1.5) * w_, v + 1, f"{v:.2f}", ha="center", fontsize=7)
    ax.set_xticks(xs); ax.set_xticklabels(base.setting, fontsize=9)
    ax.set_ylim(0, 115); ax.set_ylabel("正しく分けた件の割合（%、200回の平均）")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center")
    ax.set_title("残った件で確かめた正しさは、来る件全体での正しさより高く出る", fontsize=11)
    save(fig, "a1235_accuracy.png", SRC + "。手がかりのぶれ1.0・分類する仕組みは残った件で作った")

    # 図3：除いた割合と、見かけと実際の差（対称・片寄り、手がかりの強さごと）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for m, c in zip([0.5, 1.0, 2.0], [GREEN, BLUE, ORANGE]):
        for kind, ls, mk in [("対称", "-", "o"), ("片寄り", "--", "s")]:
            d = grid[(grid.cue_sd == m) & (grid.kind == kind)]
            ax.plot(d.share_unsure, d.gap_seen_minus_all, color=c, ls=ls, marker=mk, ms=4,
                    label=f"手がかりのぶれ{m}・{kind}")
    ax.axhline(0, color=GRAY, lw=.8)
    ax.set_xlabel("「分からない」で除いた件の割合（%）"); ax.set_ylabel("見かけの正しさ − 来る件全体での正しさ（ポイント）")
    ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left")
    ax.set_title("多く除くほど、見かけの正しさは来る件全体での正しさより上に出る（30通り）", fontsize=10.5)
    save(fig, "a1235_gap_grid.png", SRC + "。見かけの正しさ＝残った件で付けた分類と比べた正しさ。各30回")
    print(base.T.to_string()); print(json.dumps(rob, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
