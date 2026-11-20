"""862 質問の順番で、後の質問の答えはどれだけ変わるのか？（架空のデータ）

架空の飲食店の客600人に、5段階で「店員の対応」と「店全体」の満足を聞く。
半分（300人）は「店全体 → 店員の対応」の順（順番A）、残り半分（300人）は「店員の対応 → 店全体」の順（順番B）。
客ごとに料理 f・店員の対応 s・値段 p の本当の満足（1〜5の連続の値）を置き、本当の全体の満足 g=(f+s+p)/3 とする。
  店全体を先に聞く（順番A）：round(g + e)
  店員の対応のあとに聞く（順番B）：round((1-λ)g + λ s + e)   λ は「前の質問に引っぱられる強さ」（基本0.3）
  店員の対応：round(s + e)。e は答えるときのぶれ（標準偏差0.5）。答えは1〜5に収める。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 862
SRC = "架空の飲食店の客アンケート（作成者が乱数で作成、seed 862）"
N = 600
REPS = 2000
F_MEAN, P_MEAN, S_MEAN, SD, RHO, NOISE, LAM = 4.2, 3.8, 3.0, 0.7, 0.3, 0.5, 0.3


def people(rng, shape, s_mean=S_MEAN):
    """料理・対応・値段の本当の満足。3つは相関 RHO（その人の機嫌などの共通の部分）"""
    c = rng.normal(0, 1, shape)
    z = [np.sqrt(RHO) * c + np.sqrt(1 - RHO) * rng.normal(0, 1, shape) for _ in range(3)]
    f, s, p = F_MEAN + SD * z[0], s_mean + SD * z[1], P_MEAN + SD * z[2]
    return f, s, p, (f + s + p) / 3


def ans(v):
    return np.clip(np.round(v), 1, 5)


def survey(rng, reps, lam=LAM, s_mean=S_MEAN, n=N):
    f, s, p, g = people(rng, (reps, n), s_mean)
    h = n // 2
    e1, e2 = rng.normal(0, NOISE, (reps, n)), rng.normal(0, NOISE, (reps, n))
    q_srv = ans(s + e1)
    q_all = np.where(np.arange(n) < h, ans(g + e2), ans((1 - lam) * g + lam * s + e2))
    A, B = slice(0, h), slice(h, n)
    sat = q_all >= 4
    shareA, shareB = sat[:, A].mean(1), sat[:, B].mean(1)
    meanA, meanB = q_all[:, A].mean(1), q_all[:, B].mean(1)

    def corr(x, y):
        x = x - x.mean(1, keepdims=True); y = y - y.mean(1, keepdims=True)
        return (x * y).sum(1) / np.sqrt((x * x).sum(1) * (y * y).sum(1))
    # 割合の差の z（2つの割合の差の検定、目安）
    pp = (shareA + shareB) / 2
    se = np.sqrt(pp * (1 - pp) * 2 / h)
    z = (shareB - shareA) / np.where(se > 0, se, np.nan)
    return {"shareA": shareA, "shareB": shareB, "diff": shareB - shareA, "meanA": meanA, "meanB": meanB,
            "corrA": corr(q_srv[:, A], q_all[:, A]), "corrB": corr(q_srv[:, B], q_all[:, B]),
            "srv_share": (q_srv >= 4).mean(1), "true_g_share": (g >= 3.5).mean(1),
            "gap": (s - g).mean(1), "visible": np.abs(z) > 1.96}


def q(v):
    return {"mean": round(float(np.mean(v)), 4), "p10": round(float(np.quantile(v, .1)), 4),
            "p90": round(float(np.quantile(v, .9)), 4)}


def main():
    rng = np.random.default_rng(SEED)

    # 1回分の調査（data）
    f, s, p, g = people(rng, N)
    order = np.where(np.arange(N) < N // 2, "A_全体が先", "B_対応が先")
    q_srv = ans(s + rng.normal(0, NOISE, N))
    e2 = rng.normal(0, NOISE, N)
    q_all = np.where(order == "A_全体が先", ans(g + e2), ans((1 - LAM) * g + LAM * s + e2))
    one = pd.DataFrame({"id": np.arange(1, N + 1), "order": order, "food": f.round(4), "service": s.round(4),
                        "price": p.round(4), "q_service": q_srv.astype(int), "q_overall": q_all.astype(int)})
    one.to_csv(DATA / "respondents.csv", index=False)
    oa, ob = one[one.order == "A_全体が先"], one[one.order == "B_対応が先"]
    one_res = {"shareA": round(float((oa.q_overall >= 4).mean()), 4), "shareB": round(float((ob.q_overall >= 4).mean()), 4),
               "corrA": round(float(np.corrcoef(oa.q_service, oa.q_overall)[0, 1]), 4),
               "corrB": round(float(np.corrcoef(ob.q_service, ob.q_overall)[0, 1]), 4)}
    one_res["diff_points"] = round((one_res["shareB"] - one_res["shareA"]) * 100, 2)

    # 2) 2,000回
    r = survey(rng, REPS)
    summ = {k: q(v) for k, v in r.items() if k != "visible"}
    summ["diff_points"] = q(r["diff"] * 100)
    summ["visible_rate"] = round(float(r["visible"].mean()), 4)
    summ["share_reps_B_lower"] = round(float((r["diff"] < 0).mean()), 4)
    pd.DataFrame({k: np.round(v.astype(float), 4) for k, v in r.items()}).describe().round(4).to_csv(RES / "reps_describe.csv")

    # 3) 確かめ：引っぱられる強さ λ と、店員の対応の平均（全体との差）を変える（各500回）
    rows = []
    for lam in [-0.2, 0.0, 0.1, 0.2, 0.3, 0.5]:
        for sm in [2.6, 3.0, 3.4, 4.0, 4.4]:
            rr = survey(np.random.default_rng(SEED * 100 + int((lam + 1) * 100) * 10 + int(sm * 10)), 500, lam, sm)
            rows.append({"lam": lam, "service_mean": sm, "gap_service_minus_overall": round(float(rr["gap"].mean()), 3),
                         "shareA": round(float(rr["shareA"].mean()), 4), "shareB": round(float(rr["shareB"].mean()), 4),
                         "diff_points": round(float(rr["diff"].mean() * 100), 2),
                         "corrA": round(float(rr["corrA"].mean()), 3), "corrB": round(float(rr["corrB"].mean()), 3),
                         "visible_rate": round(float(rr["visible"].mean()), 3)})
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robustness.csv", index=False)
    pos = rob[rob.lam > 0]
    robs = {"diff_min": float(rob.diff_points.min()), "diff_max": float(rob.diff_points.max()),
            "lam03_by_service_mean": rob[rob.lam == 0.3].set_index("service_mean")[["gap_service_minus_overall", "diff_points", "corrA", "corrB", "visible_rate"]].to_dict("index"),
            "s30_by_lam": rob[rob.service_mean == 3.0].set_index("lam")[["diff_points", "corrA", "corrB", "visible_rate"]].to_dict("index"),
            "gap0_abs_diff_max": float(rob[rob.service_mean == 4.0].diff_points.abs().max()),
            "corr_up_all_pos_lam": bool((pos.corrB > pos.corrA).all()),
            "corr_up_min": float((pos.corrB - pos.corrA).min()), "corr_up_max": float((pos.corrB - pos.corrA).max())}

    out = {"setting": {"N": N, "per_order": N // 2, "reps": REPS, "food_mean": F_MEAN, "service_mean": S_MEAN,
                       "price_mean": P_MEAN, "sd": SD, "rho": RHO, "noise": NOISE, "lambda": LAM},
           "one_survey": one_res, "reps_summary": summ, "robustness": robs}
    json.dump(out, open(RES / "a862_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：順番ごとの「店全体に満足（4・5）」の割合
    lab = ["店員の対応に満足\n（参考）", "店全体に満足\n順番A：全体が先", "店全体に満足\n順番B：対応のあと"]
    keys = ["srv_share", "shareA", "shareB"]
    m = [summ[k]["mean"] * 100 for k in keys]
    lo = [m[i] - summ[k]["p10"] * 100 for i, k in enumerate(keys)]
    hi = [summ[k]["p90"] * 100 - m[i] for i, k in enumerate(keys)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    yy = np.arange(3)[::-1]
    ax.barh(yy, m, color=[GRAY, BLUE, ORANGE], xerr=[lo, hi], error_kw={"ecolor": INK, "lw": 1, "capsize": 3})
    for i, v, h_ in zip(yy, m, hi):
        ax.text(v + h_ + 1.5, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels(lab, fontsize=9); ax.set_xlim(0, 100)
    ax.set_xlabel("「満足」「やや満足」（5段階の4・5）の割合（%、2,000回の平均。線は10〜90%の範囲）", fontsize=9.5)
    ax.set_title(f"対応を先に聞くと、店全体の満足は{-summ['diff_points']['mean']:.1f}ポイント下がった（引っぱり0.3と置いた場合）",
                 fontsize=11.5)
    save(fig, "a862_order_share.png", SRC)

    # 図2：確かめ（λ と 対応の平均）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cols = {2.6: ORANGE, 3.0: "#c0502a", 3.4: GRAY, 4.0: INK, 4.4: BLUE}
    for sm, gdf in rob.groupby("service_mean"):
        gap = gdf.gap_service_minus_overall.mean()
        ax.plot(gdf.lam, gdf.diff_points, marker="o", color=cols[sm], lw=1.5,
                label=f"対応の平均{sm:.1f}（全体との差{gap:+.2f}" + ("、基本）" if sm == S_MEAN else "）"))
    ax.axhline(0, color=GRAY, lw=.8); ax.axvline(0, color=GRAY, lw=.8, ls=":")
    ax.set_xlabel("前の質問に引っぱられる強さ λ（作成者が置く値。負は逆に離れる）")
    ax.set_ylabel("順番B − 順番A（ポイント）")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title("動く向きと大きさは、引っぱりの強さ×前の質問と全体の差で決まる（30通り）", fontsize=11.5)
    save(fig, "a862_robustness.png", SRC)

    # 図3：2つの答えの相関（順番A・B）
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.6), sharey=True)
    for ax, sm, ttl in [(axs[0], 3.0, "対応の平均3.0（基本）"), (axs[1], 4.0, "対応の平均4.0（全体とほぼ同じ）")]:
        gdf = rob[rob.service_mean == sm]
        ax.plot(gdf.lam, gdf.corrA, marker="o", color=BLUE, label="順番A：全体が先")
        ax.plot(gdf.lam, gdf.corrB, marker="o", color=ORANGE, label="順番B：対応のあと")
        ax.set_title(ttl, fontsize=10); ax.set_xlabel("引っぱられる強さ λ")
    axs[0].set_ylabel("「対応」と「全体」の答えの相関"); axs[0].legend(frameon=False, fontsize=8.5)
    fig.suptitle("平均が動かないときでも、対応のあとに聞くと2つの答えは似てくる", fontsize=12, y=1.04)
    save(fig, "a862_corr.png", SRC, y=-0.07)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
