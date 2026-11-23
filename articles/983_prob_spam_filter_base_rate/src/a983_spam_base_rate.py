"""983 「迷惑メール」と判定されたとき、本当に迷惑メールの確率は？（もとの割合、架空のデータ）

架空の会社の300人の受信箱に4週間で届いたメール。受信箱ごとの迷惑メールの割合（もとの割合）を作成者が置き、
振り分けの仕組みは、迷惑メールを95%の確率で「迷惑」と判定し（見逃し5%）、ふつうのメールを1%の確率で「迷惑」と判定する（誤検出1%）と置く。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 983
SRC = "架空の会社の受信箱のメール（作成者が乱数で作成、seed 983）"
rng = np.random.default_rng(SEED)
N_BOX, MEAN_MAIL = 300, 500
TPR, FPR = 0.95, 0.01
SPREADS = {"なし（全員5%）": None, "小": (2.0, 38.0), "基本": (0.5, 9.5), "大": (0.2, 3.8)}


def make_company(g, spread=(0.5, 9.5), tpr=TPR, fpr=FPR, mean_p=None):
    n = g.poisson(MEAN_MAIL, N_BOX)
    if spread is None:
        p = np.full(N_BOX, 0.05 if mean_p is None else mean_p)
    else:
        p = g.beta(*spread, N_BOX)
    spam = g.binomial(n, p)
    ham = n - spam
    tp = g.binomial(spam, tpr)
    fp = g.binomial(ham, fpr)
    return pd.DataFrame({"box_id": np.arange(1, N_BOX + 1), "p_set": p, "mails": n, "spam": spam, "ham": ham,
                         "flag_spam": tp, "flag_ham": fp})


def ppv_formula(p, tpr=TPR, fpr=FPR):
    return p * tpr / (p * tpr + (1 - p) * fpr)


def box_summary(df):
    fl = df.flag_spam + df.flag_ham
    has = fl > 0
    ppv = df.flag_spam[has] / fl[has]
    return {"boxes_with_flag": int(has.sum()),
            "share_boxes_ppv_lt50": round(float((ppv < 0.5).mean()) * 100, 2),
            "share_boxes_all_flag_ham": round(float((ppv == 0).mean()) * 100, 2),
            "median_box_ppv": round(float(ppv.median()) * 100, 2),
            "p10_box_ppv": round(float(ppv.quantile(.1)) * 100, 2),
            "p90_box_ppv": round(float(ppv.quantile(.9)) * 100, 2),
            "company_ppv": round(float(df.flag_spam.sum() / fl.sum()) * 100, 2),
            "company_spam_share": round(float(df.spam.sum() / df.mails.sum()) * 100, 3),
            "share_of_misfiled_ham_in_boxes_ppv_lt50": round(float(df.flag_ham[has][ppv < 0.5].sum() / df.flag_ham.sum()) * 100, 2)}


def main():
    # 1) 基本：1社（1回分）
    df = make_company(rng)
    df["flagged"] = df.flag_spam + df.flag_ham
    df["flagged_share"] = df.flagged / df.mails
    df["box_ppv"] = np.where(df.flagged > 0, df.flag_spam / df.flagged.where(df.flagged > 0, 1), np.nan)
    df.to_csv(DATA / "mailboxes.csv", index=False, float_format="%.5f")
    M, S = int(df.mails.sum()), int(df.spam.sum())
    TP, FP = int(df.flag_spam.sum()), int(df.flag_ham.sum())
    FN, TN = S - TP, M - S - FP
    base = {"mails": M, "spam": S, "spam_share": round(S / M * 100, 3),
            "accuracy": round((TP + TN) / M * 100, 3),
            "flagged": TP + FP, "flag_true_spam": TP, "flag_ham": FP, "missed_spam": FN,
            "ppv_sim": round(TP / (TP + FP) * 100, 2),
            "ppv_formula_at_realized_share": round(ppv_formula(S / M) * 100, 2),
            "ppv_formula_at_5pct": round(ppv_formula(0.05) * 100, 2),
            "per_10000": {"spam": round(S / M * 1e4), "flagged": round((TP + FP) / M * 1e4),
                          "flag_true_spam": round(TP / M * 1e4), "flag_ham": round(FP / M * 1e4),
                          "missed_spam": round(FN / M * 1e4)},
            "inbox_spam_share": round(FN / (FN + TN) * 100, 3),
            "ham_over_spam": round((M - S) / S, 2),
            "box_p_set_median": round(float(df.p_set.median()) * 100, 2),
            "box_p_set_p10": round(float(df.p_set.quantile(.1)) * 100, 2),
            "box_p_set_p90": round(float(df.p_set.quantile(.9)) * 100, 2)}
    base.update({"box_" + k: v for k, v in box_summary(df).items()})
    # 受信箱の迷惑メールの割合の帯ごと
    bins = [0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 1.0]
    lab = ["0.5%未満", "0.5〜1%", "1〜2%", "2〜5%", "5〜10%", "10〜20%", "20%以上"]
    df["band"] = pd.cut(df.spam / df.mails, bins, labels=lab, include_lowest=True, right=False)
    band = df.groupby("band", observed=False).agg(boxes=("box_id", "size"), spam=("spam", "sum"), mails=("mails", "sum"),
                                                  flag_spam=("flag_spam", "sum"), flag_ham=("flag_ham", "sum")).reset_index()
    band["ppv"] = (band.flag_spam / (band.flag_spam + band.flag_ham) * 100).round(2)
    band["spam_share"] = (band.spam / band.mails * 100).round(3)
    band.to_csv(RES / "by_box_band.csv", index=False)

    # 2) 確かめ：受信箱ごとの散らばり×誤検出の割合（各50社）
    rows = []
    for name, sp in SPREADS.items():
        for fpr in [0.002, 0.01, 0.03]:
            acc = []
            for r in range(50):
                g = np.random.default_rng(SEED * 1000 + r)
                acc.append(box_summary(make_company(g, sp, fpr=fpr)))
            a = pd.DataFrame(acc).mean()
            rows.append({"spread": name, "fpr": fpr, **{k: round(float(v), 2) for k, v in a.items()}})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "robust_spread_fpr.csv", index=False)

    # 3) もとの割合×誤検出の割合：式（会社全体）
    frows = []
    for p in [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]:
        for fpr in [0.002, 0.01, 0.03]:
            frows.append({"spam_share": p, "fpr": fpr, "ppv": round(ppv_formula(p, TPR, fpr) * 100, 2),
                          "accuracy": round((p * TPR + (1 - p) * (1 - fpr)) * 100, 2),
                          "flagged_share": round((p * TPR + (1 - p) * fpr) * 100, 3)})
    fgrid = pd.DataFrame(frows)
    fgrid.to_csv(RES / "formula_share_fpr.csv", index=False)

    # 4) 「迷惑」と出た割合から、もとの割合を読む：そのまま／直す（置いた誤検出を使う）
    est = []
    for p in [0.005, 0.01, 0.02, 0.05, 0.2]:
        f = p * TPR + (1 - p) * FPR
        row = {"true_share": round(p * 100, 2), "flagged_share_formula": round(f * 100, 3),
               "naive_over_true": round(f / p, 2)}
        for fa in [0.005, 0.01, 0.02]:
            row[f"corrected_assume_fpr_{fa}"] = round((f - fa) / (TPR - fa) * 100, 3)
        # 1つの受信箱（500通）での直した値の振れ（誤検出を正しく1%と置いたとき）
        g = np.random.default_rng(SEED + int(p * 1e4))
        n = 500
        sp = g.binomial(n, p, 20000)
        fl = g.binomial(sp, TPR) + g.binomial(n - sp, FPR)
        corr = (fl / n - FPR) / (TPR - FPR) * 100
        row.update({"box500_corr_p10": round(float(np.quantile(corr, .1)), 3),
                    "box500_corr_p90": round(float(np.quantile(corr, .9)), 3),
                    "box500_share_negative": round(float((corr < 0).mean()) * 100, 2)})
        est.append(row)
    est = pd.DataFrame(est)
    est.to_csv(RES / "estimate_share.csv", index=False)

    out = {"settings": {"boxes": N_BOX, "mean_mails_per_box": MEAN_MAIL, "tpr": TPR, "fpr": FPR,
                        "spread_beta": {k: v for k, v in SPREADS.items()}},
           "base_company": base, "by_box_band": band.to_dict("records"),
           "robust_spread_fpr": grid.to_dict("records"), "formula_share_fpr": fgrid.to_dict("records"),
           "estimate_share": est.to_dict("records"),
           "range_share_boxes_ppv_lt50": [float(grid.share_boxes_ppv_lt50.min()), float(grid.share_boxes_ppv_lt50.max())],
           "range_company_ppv": [float(grid.company_ppv.min()), float(grid.company_ppv.max())]}
    json.dump(out, open(RES / "a983_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：もとの割合と「迷惑」の当たり（式）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for fpr, col in [(0.002, GREEN), (0.01, BLUE), (0.03, ORANGE)]:
        g = fgrid[fgrid.fpr == fpr]
        ax.plot(g.spam_share * 100, g.ppv, marker="o", color=col, label=f"誤検出{fpr*100:g}%")
    ax.set_xscale("log"); ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50]); ax.set_xticklabels(["0.5%", "1%", "2%", "5%", "10%", "20%", "50%"])
    ax.axhline(50, color=GRAY, lw=.8, ls=":")
    ax.set_xlabel("届いたメールのうち、本当に迷惑メールの割合（もとの割合、対数の目盛り）")
    ax.set_ylabel("「迷惑」と出たメールのうち\n本当に迷惑メールの割合（%）"); ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=9, loc="lower right", title="見逃し5%と")
    ax.set_title("同じ振り分けでも、もとの割合が小さいと「迷惑」の当たりは下がる（式）")
    save(fig, "a983_base_rate.png", SRC)

    # 図2：受信箱ごと
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    d = df[df.flagged > 0]
    sh = (d.spam / d.mails * 100).clip(lower=0.05)
    ax.scatter(sh, d.box_ppv * 100, s=12, color=BLUE, alpha=.6, lw=0)
    xs = np.logspace(np.log10(0.05), np.log10(60), 100)
    ax.plot(xs, ppv_formula(xs / 100) * 100, color=ORANGE, lw=1.5, label="式（見逃し5%・誤検出1%）")
    ax.set_xscale("log"); ax.set_xticks([0.1, 1, 10, 50]); ax.set_xticklabels(["0.1%", "1%", "10%", "50%"])
    ax.axhline(50, color=GRAY, lw=.8, ls=":")
    ax.set_xlabel("その受信箱の、本当に迷惑メールの割合（対数の目盛り。0件は0.05%に置いた）")
    ax.set_ylabel("その受信箱で「迷惑」と出たメールのうち\n本当に迷惑メールの割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title(f"会社全体では{base['box_company_ppv']:.1f}%でも、{base['box_share_boxes_ppv_lt50']:.1f}%の受信箱では半分未満")
    save(fig, "a983_boxes.png", SRC)

    # 図3：「迷惑」と出た割合をそのまま読むと
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(len(est))
    ax.bar(x, est.naive_over_true, width=.55, color=BLUE)
    for i, r in est.iterrows():
        ax.text(i, r.naive_over_true + .06, f"{r.naive_over_true:g}倍\n（{r.flagged_share_formula:g}%）", ha="center", fontsize=9)
    ax.axhline(1, color=GRAY, lw=1, ls="--", label="本当どおり（1倍）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_xticks(x); ax.set_xticklabels([f"{v:g}%" for v in est.true_share]); ax.set_ylim(0, 3.6)
    ax.set_xlabel("本当の迷惑メールの割合（もとの割合）"); ax.set_ylabel("「迷惑」と出た割合÷本当の割合")
    ax.set_title("もとの割合が小さいほど、「迷惑」と出た割合は本当より大きく出る（式）")
    save(fig, "a983_flagged_share.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
