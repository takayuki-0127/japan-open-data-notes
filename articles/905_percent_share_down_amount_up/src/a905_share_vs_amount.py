"""905 構成比が下がっても、量は増えていることはあるのか？（架空のデータ）

架空の会社2,000社。各社に5つの商品分類（A〜E）があり、売上は毎年
「会社全体の伸び（会社ごとの傾き＋年ごとの振れ）」×「分類ごとの傾き＋年ごとの振れ」で動くと置く。
構成比（その分類の売上÷会社の売上）が下がった分類のうち、売上そのものは増えていた割合を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 905
SRC = "架空の会社の商品分類別の売上（作成者が乱数で作成、seed 905）"
N_CO, N_CAT, YEARS = 2000, 5, 10
CATS = list("ABCDE")
M_MED, M_SD, ETA_SD = 0.03, 0.04, 0.03   # 会社全体の伸び（対数）：会社ごとの傾き 平均0.03・標準偏差0.04、年ごとの振れ0.03
TAU_SD, EPS_SD = 0.05, 0.08              # 分類ごとの傾きの標準偏差、年ごとの振れ


def simulate(rng, n=N_CO, m_med=M_MED, scale=1.0, years=YEARS):
    share0 = rng.dirichlet(np.full(N_CAT, 2.0), n)
    sales = np.zeros((n, N_CAT, years + 1))
    sales[:, :, 0] = 100 * share0
    m = rng.normal(m_med, M_SD, n)
    tau = rng.normal(0, TAU_SD * scale, (n, N_CAT))
    for t in range(1, years + 1):
        eta = rng.normal(0, ETA_SD, n)
        eps = rng.normal(0, EPS_SD * scale, (n, N_CAT))
        sales[:, :, t] = sales[:, :, t - 1] * np.exp((m + eta)[:, None] + tau + eps)
    return sales


def share_vs_amount(sales, t0, t1):
    tot0, tot1 = sales[:, :, t0].sum(1, keepdims=True), sales[:, :, t1].sum(1, keepdims=True)
    s0, s1 = sales[:, :, t0] / tot0, sales[:, :, t1] / tot1
    a0, a1 = sales[:, :, t0], sales[:, :, t1]
    down, up = s1 < s0, s1 > s0
    G = np.repeat(tot1 / tot0 - 1, N_CAT, 1)
    return {"cells": int(down.size), "share_down": int(down.sum()), "share_up": int(up.sum()),
            "share_down_amount_up": round(float((a1[down] > a0[down]).mean()), 4),
            "share_up_amount_down": round(float((a1[up] < a0[up]).mean()), 4) if up.sum() else None,
            "total_up_share": round(float((tot1 > tot0).mean()), 4)}, (s0, s1, a0, a1, G)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    sales = simulate(rng)

    one, (s0, s1, a0, a1, G) = share_vs_amount(sales, 0, 1)
    ten, (S0, S1, A0, A1, G10) = share_vs_amount(sales, 0, YEARS)
    one["median_total_growth_pct"] = round(float(np.median(G[:, 0]) * 100), 2)
    ten["median_total_growth_pct"] = round(float(np.median(G10[:, 0]) * 100), 2)

    rows = []
    for i in range(N_CO):
        for j in range(N_CAT):
            rows.append((i + 1, CATS[j], sales[i, j, 0], sales[i, j, 1], s0[i, j], s1[i, j]))
    pd.DataFrame(rows, columns=["company_id", "category", "sales_y0", "sales_y1", "share_y0", "share_y1"]).to_csv(
        DATA / "companies_year0_1.csv", index=False, float_format="%.4f")

    # 1) 全体の伸びごと（1年）
    bands = [(-1, -0.05, "−5%未満"), (-0.05, 0, "−5〜0%"), (0, 0.05, "0〜+5%"), (0.05, 0.10, "+5〜+10%"), (0.10, 9, "+10%以上")]
    by_g = []
    down, up = s1 < s0, s1 > s0
    for lo, hi, lab in bands:
        g = (G >= lo) & (G < hi)
        d, u = down & g, up & g
        by_g.append({"total_growth": lab, "companies": int(g[:, 0].sum()), "share_down_cells": int(d.sum()),
                     "share_down_amount_up": round(float((a1[d] > a0[d]).mean()), 4) if d.sum() else None,
                     "share_up_amount_down": round(float((a1[u] < a0[u]).mean()), 4) if u.sum() else None})
    by_g = pd.DataFrame(by_g)
    by_g.to_csv(RES / "by_total_growth.csv", index=False)

    # 2) 構成比が下がった分類を、構成比の下がり方（ポイント）ごとに
    drop_pt = (s0 - s1) * 100
    by_pt = []
    for lo, hi, lab in [(0, 0.5, "0.5ポイント以内"), (0.5, 1, "0.5〜1ポイント"), (1, 2, "1〜2ポイント"),
                        (2, 5, "2〜5ポイント"), (5, 100, "5ポイントより大きい")]:
        sel = down & (drop_pt > lo) & (drop_pt <= hi)
        by_pt.append({"share_drop": lab, "cells": int(sel.sum()),
                      "amount_up": round(float((a1[sel] > a0[sel]).mean()), 4) if sel.sum() else None})
    by_pt = pd.DataFrame(by_pt)
    by_pt.to_csv(RES / "by_share_drop.csv", index=False)

    # 3) 式：全体が G 伸びたとき、売上が減らない構成比の下限（元の構成比40%のとき）
    rule = [{"total_growth_pct": g, "min_share_ratio": round(1 / (1 + g / 100), 4),
             "from_40pct_min_share_pct": round(40 / (1 + g / 100), 2)} for g in [-10, 0, 3, 10, 20, 34, 50]]
    pd.DataFrame(rule).to_csv(RES / "rule_share_floor.csv", index=False)

    # 4) 10年の例：会社全体の10年の伸びが+30〜+70%（真ん中あたり）の会社で、
    #    構成比が10年で下がり、売上は増えた分類から、構成比の下がり方のいちばん大きいもの
    mid = (G10 >= 0.30) & (G10 <= 0.70)
    dn10 = (S1 < S0) & (A1 > A0) & mid
    drop = np.where(dn10, S0 - S1, -1)
    i, j = np.unravel_index(np.argmax(drop), drop.shape)
    ex = []
    for t in range(YEARS + 1):
        tot = sales[i, :, t].sum()
        for k in range(N_CAT):
            ex.append({"year": t, "category": CATS[k], "sales": round(float(sales[i, k, t]), 2),
                       "share_pct": round(float(sales[i, k, t] / tot * 100), 2)})
    ex = pd.DataFrame(ex)
    ex.to_csv(DATA / "example_company_10y.csv", index=False)
    exs = ex[ex.category == CATS[j]]
    example = {"company_id": int(i + 1), "category": CATS[j],
               "share_y0": float(exs.share_pct.iloc[0]), "share_y10": float(exs.share_pct.iloc[-1]),
               "sales_y0": float(exs.sales.iloc[0]), "sales_y10": float(exs.sales.iloc[-1]),
               "total_y0": round(float(sales[i, :, 0].sum()), 2), "total_y10": round(float(sales[i, :, YEARS].sum()), 2),
               "share_down_years": int((np.diff(exs.share_pct.values) < 0).sum()),
               "sales_up_years": int((np.diff(exs.sales.values) > 0).sum())}

    # 5) 確かめ：会社全体の伸びの中心 × 分類の動きの大きさ（4×3通り、各2,000社）
    sens = []
    for mm in [-0.05, 0.0, 0.03, 0.10]:
        for sc in [0.5, 1.0, 2.0]:
            sl = simulate(np.random.default_rng(SEED * 31 + int((mm + 1) * 100) * 10 + int(sc * 10)), N_CO, mm, sc)
            o1, _ = share_vs_amount(sl, 0, 1)
            o10, _ = share_vs_amount(sl, 0, YEARS)
            sens.append({"m_med": mm, "category_scale": sc,
                         "y1_share_down_amount_up": o1["share_down_amount_up"],
                         "y1_share_up_amount_down": o1["share_up_amount_down"],
                         "y10_share_down_amount_up": o10["share_down_amount_up"],
                         "y10_share_up_amount_down": o10["share_up_amount_down"]})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_grid.csv", index=False)

    out = {"one_year": one, "ten_years": ten, "by_total_growth": by_g.to_dict("records"),
           "by_share_drop": by_pt.to_dict("records"), "rule_share_floor": rule, "example_10y": example,
           "sensitivity": {"rows": sens.to_dict("records"),
                           "y1_min": float(sens.y1_share_down_amount_up.min()), "y1_max": float(sens.y1_share_down_amount_up.max()),
                           "y10_min": float(sens.y10_share_down_amount_up.min()), "y10_max": float(sens.y10_share_down_amount_up.max())}}
    json.dump(out, open(RES / "a905_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の会社の10年（構成比と売上）
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.8))
    yrs = np.arange(YEARS + 1)
    for k, c in enumerate(CATS):
        e = ex[ex.category == c]
        col, lw = (ORANGE, 2.4) if c == CATS[j] else (GRAY, 1.0)
        axs[0].plot(yrs, e.share_pct, color=col, lw=lw)
        axs[1].plot(yrs, e.sales, color=col, lw=lw)
        axs[0].text(YEARS + 0.2, e.share_pct.iloc[-1], c, color=col, fontsize=9, va="center")
        axs[1].text(YEARS + 0.2, e.sales.iloc[-1], c, color=col, fontsize=9, va="center")
    axs[0].set_title("構成比（%）", fontsize=11); axs[1].set_title("売上（1年目の会社全体＝100）", fontsize=11)
    for a in axs:
        a.set_xlabel("年"); a.set_xticks([0, 2, 4, 6, 8, 10]); a.set_ylim(bottom=0)
    fig.suptitle(f"分類{CATS[j]}：構成比は{example['share_y0']:.0f}%→{example['share_y10']:.0f}%に下がり、売上は{example['sales_y0']:.0f}→{example['sales_y10']:.0f}に増えた（架空の1社）", fontsize=12)
    fig.tight_layout()
    save(fig, "a905_example.png", SRC)

    # 図2：会社全体の伸びごと
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    bg = by_g.dropna(subset=["share_down_amount_up"])
    ax.bar(bg.total_growth, bg.share_down_amount_up * 100, color=[GRAY, GRAY, LIGHT, BLUE, BLUE][:len(bg)])
    for x, (v, n) in enumerate(zip(bg.share_down_amount_up * 100, bg.companies)):
        ax.text(x, v + 2, f"{v:.0f}%\n（{n:,}社）", ha="center", fontsize=8.5)
    ax.set_ylim(0, 105); ax.set_ylabel("構成比が下がった分類のうち、売上が増えた割合（%）", fontsize=10)
    ax.set_xlabel("その年の会社全体の売上の伸び（かっこは会社の数）")
    ax.set_title("全体が伸びた会社ほど、構成比の下がった分類の売上も増えている")
    save(fig, "a905_by_total_growth.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = 0.26
    mms = [-0.05, 0.0, 0.03, 0.10]
    for k, (sc, col, lab) in enumerate([(0.5, LIGHT, "分類の動き 半分"), (1.0, BLUE, "基本"), (2.0, INK, "2倍")]):
        s = sens[sens.category_scale == sc]
        xs = np.arange(4) + (k - 1) * w
        ax.bar(xs, s.y1_share_down_amount_up * 100, w, color=col, label=lab)
        for xx, v in zip(xs, s.y1_share_down_amount_up * 100):
            ax.text(xx, v + 1.5, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(np.arange(4)); ax.set_xticklabels(["年−5%", "年0%", "年+3%（基本）", "年+10%"])
    ax.set_xlabel("会社全体の伸びの中心（1年あたり）。1年目→2年目で数えた")
    ax.set_ylabel("構成比が下がった分類のうち、売上が増えた割合（%）", fontsize=10); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("割合は、全体の伸びと分類の動きの大きさの置き方で決まる")
    save(fig, "a905_sensitivity.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
