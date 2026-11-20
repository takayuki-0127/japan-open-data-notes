"""822 積み上げ棒グラフで、真ん中の項目の増減は読めるのか？（架空のデータ）

架空の会社2,000社。どの会社も商品A〜Dの4つの月の売上（24か月）を持ち、
下からA・B・C・Dの順に積み上げた棒グラフを描くと置く。
真ん中の項目Bの増減（作成者が置いた答え）が、図の上で見える「Bの上端の動き」とどれだけ合うかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 822
SRC = "架空の会社の商品別の売上（作成者が乱数で作成、seed 822）"
N_CO, T = 2000, 24
ITEMS = ["A", "B", "C", "D"]
# 基本の置き方：月の平均の大きさ・季節の振れ（±）・月ごとのばらつき（変動係数）・1年の伸びの範囲
BASE = {"A": dict(level=100, amp=0.15, cv=0.08, trend=0.10),
        "B": dict(level=40, amp=0.05, cv=0.05, trend=0.20),
        "C": dict(level=30, amp=0.10, cv=0.06, trend=0.10),
        "D": dict(level=20, amp=0.10, cv=0.06, trend=0.10)}


def make(rng, n=N_CO, spec=BASE):
    """会社×月×商品の売上（n, T, 4）と、商品ごとの1年の伸び（n, 4）"""
    t = np.arange(T)
    out, trends = [], []
    for it in ITEMS:
        s = spec[it]
        g = rng.uniform(-s["trend"], s["trend"], n)            # 1年あたりの伸び（対数）
        ph = rng.uniform(0, 2 * np.pi, n)                     # 季節の山の位置
        season = 1 + s["amp"] * np.sin(2 * np.pi * t[None, :] / 12 + ph[:, None])
        noise = np.exp(rng.normal(0, s["cv"], (n, T)))
        out.append(s["level"] * np.exp(g[:, None] * t[None, :] / 12) * season * noise)
        trends.append(g)
    return np.stack(out, -1), np.stack(trends, -1)


def edge_stats(x, order, target="B"):
    """order の順に積んだとき、target の上端（下の項目との合計）の動きが target 自身の動きとどれだけ合うか"""
    k = order.index(target)
    cols = [ITEMS.index(o) for o in order[:k + 1]]
    own = x[:, :, ITEMS.index(target)]
    top = x[:, :, cols].sum(-1)
    d_own, d_top = np.diff(own, axis=1), np.diff(top, axis=1)
    mism = float((np.sign(d_own) != np.sign(d_top)).mean())
    share = float(np.var(d_own) / np.var(d_top))  # 上端の動きのばらつきのうち、自分の動きの分（独立なのでほぼ分け前）
    # 前年同月（12か月後との比べ）
    y_own, y_top = own[:, 12:] - own[:, :12], top[:, 12:] - top[:, :12]
    mism_y = float((np.sign(y_own) != np.sign(y_top)).mean())
    # 24か月の傾き（対数でなく実数の直線の傾き）の向き
    tt = np.arange(T) - (T - 1) / 2
    s_own, s_top = (own * tt).sum(1), (top * tt).sum(1)
    mism_s = float((np.sign(s_own) != np.sign(s_top)).mean())
    d_bot = d_top - d_own
    ratio = float(np.median(np.abs(d_bot) / np.maximum(np.abs(d_own), 1e-9))) if k > 0 else 0.0
    return {"position": k + 1, "bottom_move_over_own_move_median": round(ratio, 2), "monthly_mismatch": round(mism, 3), "own_share_of_edge_var": round(share, 3),
            "yoy_mismatch": round(mism_y, 3), "trend_mismatch": round(mism_s, 3)}, s_own, s_top


def main():
    rng = np.random.default_rng(SEED)
    x, g = make(rng)
    order = ["A", "B", "C", "D"]

    # 全社の月の売上（長い形）
    long = pd.DataFrame({"company_id": np.repeat(np.arange(1, N_CO + 1), T),
                         "month": np.tile(np.arange(1, T + 1), N_CO)})
    for i, it in enumerate(ITEMS):
        long[f"item_{it}"] = x[:, :, i].ravel().round(2)
    long.to_csv(DATA / "companies_monthly.csv", index=False)

    # 1) 基本：B（下から2番目）の上端の動き
    base, s_own, s_top = edge_stats(x, order, "B")
    tot = x.sum(-1)
    dB = np.abs(np.diff(x[:, :, 1], axis=1))
    base["median_abs_change_B_pct_of_bar"] = round(float(np.median(dB / tot[:, 1:]) * 100), 2)
    base["median_abs_change_B_pct_of_B"] = round(float(np.median(dB / x[:, 1:, 1]) * 100), 2)
    # Bの24か月の伸びの大きさごとに、傾きの向きの食い違い
    gB = np.abs(g[:, 1])
    bands = [(0, .05), (.05, .10), (.10, .15), (.15, .20)]
    by_g = []
    for lo, hi in bands:
        m = (gB >= lo) & (gB < hi)
        by_g.append({"B_trend_abs": f"{int(lo*100)}〜{int(hi*100)}%", "companies": int(m.sum()),
                     "trend_mismatch": round(float((np.sign(s_own[m]) != np.sign(s_top[m])).mean()), 3)})
    # 月の増減の大きさごとの食い違い（Bの月の増減率の絶対値）
    rB = np.abs(np.diff(np.log(x[:, :, 1]), axis=1))
    d_own, d_top = np.diff(x[:, :, 1], axis=1), np.diff(x[:, :, :2].sum(-1), axis=1)
    mb = []
    for lo, hi in [(0, .03), (.03, .06), (.06, .10), (.10, 1)]:
        m = (rB >= lo) & (rB < hi)
        mb.append({"B_monthly_change_abs": f"{int(lo*100)}〜{int(hi*100) if hi < 1 else ''}%".replace("〜%", "%以上"),
                   "share_of_months": round(float(m.mean()), 3),
                   "monthly_mismatch": round(float((np.sign(d_own[m]) != np.sign(d_top[m])).mean()), 3)})

    # 2) 積む位置を変える（Bを1〜4番目に）
    pos = []
    for k, od in enumerate([["B", "A", "C", "D"], ["A", "B", "C", "D"], ["A", "C", "B", "D"], ["A", "C", "D", "B"]]):
        r, _, _ = edge_stats(x, od, "B")
        r["order"] = "→".join(od)
        pos.append(r)
    # 4つの項目それぞれ（基本の順）
    each = []
    for it in ITEMS:
        r, _, _ = edge_stats(x, order, it)
        r["item"] = it
        each.append(r)

    # 3) 確かめ：下の項目Aの振れ方、Bの大きさを変える
    sens = []
    variants = [("基本（Aのばらつき8%・季節15%・Bの大きさ40）", {}),
                ("Aのばらつき4%", {"A": {"cv": 0.04}}), ("Aのばらつき16%", {"A": {"cv": 0.16}}),
                ("Aの季節の振れ0%", {"A": {"amp": 0.0}}), ("Aの季節の振れ30%", {"A": {"amp": 0.30}}),
                ("Bの大きさ20（Aの5分の1）", {"B": {"level": 20}}), ("Bの大きさ80（Aの5分の4）", {"B": {"level": 80}}),
                ("Bのばらつき10%", {"B": {"cv": 0.10}})]
    for j, (name, ch) in enumerate(variants):
        spec = {k: dict(v, **ch.get(k, {})) for k, v in BASE.items()}
        xx = x if j == 0 else make(np.random.default_rng(SEED * 10 + j), spec=spec)[0]
        r, _, _ = edge_stats(xx, order, "B")
        r["variant"] = name
        sens.append(r)

    pd.DataFrame(pos).to_csv(RES / "by_position.csv", index=False)
    pd.DataFrame(sens).to_csv(RES / "sensitivity.csv", index=False)
    pd.DataFrame(by_g).to_csv(RES / "trend_mismatch_by_size.csv", index=False)
    out = {"base_B_middle": base, "trend_mismatch_by_B_trend": by_g, "monthly_mismatch_by_B_change": mb,
           "by_position": pos, "each_item_base_order": each, "sensitivity": sens,
           "companies": N_CO, "months": T}
    json.dump(out, open(RES / "a822_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の会社。積み上げ棒（左）と、Bだけの線（右）
    # 例として、Bが伸びているのに上端は下がっている会社を選ぶ
    ab = x[:, :, :2].sum(-1)
    cand = np.where((g[:, 1] > 0.12) & (s_top < 0) & (ab[:, 12:].mean(1) < ab[:, :12].mean(1) * 0.97))[0]
    e = int(cand[0]) if len(cand) else 0
    xe = x[e]
    ex = pd.DataFrame(xe, columns=[f"item_{i}" for i in ITEMS]).round(2)
    ex.insert(0, "month", np.arange(1, T + 1))
    ex.to_csv(DATA / "example_company.csv", index=False)   # 図1の会社
    out["figure_example"] = {"company_id": e + 1, "B_trend_per_year": round(float(g[e, 1]), 3),
                             "A_trend_per_year": round(float(g[e, 0]), 3),
                             "B_first12_mean": round(float(xe[:12, 1].mean()), 1), "B_last12_mean": round(float(xe[12:, 1].mean()), 1),
                             "AB_first12_mean": round(float(xe[:12, :2].sum(1).mean()), 1),
                             "AB_last12_mean": round(float(xe[12:, :2].sum(1).mean()), 1)}
    json.dump(out, open(RES / "a822_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.0), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axs[0]
    m = np.arange(1, T + 1)
    bottom = np.zeros(T)
    cols = {"A": LIGHT, "B": ORANGE, "C": "#cfd8e3", "D": "#e6e6e3"}
    for i, it in enumerate(ITEMS):
        ax.bar(m, xe[:, i], bottom=bottom, color=cols[it], width=.8, label=f"商品{it}", edgecolor="white", lw=.4)
        bottom += xe[:, i]
    ax.plot(m, xe[:, :2].sum(1), color=INK, lw=1, marker="o", ms=2.5, label="Bの上端")
    ax.set_xlabel("月"); ax.set_ylabel("売上（架空の単位）")
    ax.legend(frameon=False, fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(.5, -.15))
    ax.set_title("積み上げ棒：Bの上端は下がって見える", fontsize=11)
    ax = axs[1]
    ax.plot(m, xe[:, 1], color=ORANGE, lw=1.6, marker="o", ms=2.5)
    ax.set_ylim(0, xe[:, 1].max() * 1.25)
    ax.set_xlabel("月"); ax.set_ylabel("商品Bの売上")
    ax.set_title(f"Bだけを0から描く：1年に{g[e,1]*100:+.0f}%の伸び", fontsize=11)
    fig.suptitle(f"同じ会社（{e+1}社目）の同じ数字", fontsize=12, y=1.01)
    save(fig, "a822_example.png", SRC, y=-0.08)

    # 図2：積む位置ごとの食い違い
    p = pd.DataFrame(pos)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    lab = [f"{r.position}番目（{r.order}）" for r in p.itertuples()]
    ax.barh(lab[::-1], p.monthly_mismatch[::-1] * 100, color=[BLUE, ORANGE, ORANGE, ORANGE][::-1], height=.55)
    for i, v in enumerate(p.monthly_mismatch[::-1] * 100):
        ax.text(v + .8, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 60)
    ax.set_xlabel("前の月からの増減の向きが、Bの上端とB自身で食い違った月の割合（%）")
    ax.set_title("Bを下から何番目に積むか（2,000社×23回の月の増減）")
    save(fig, "a822_position.png", SRC, y=-0.05)

    # 図3：Bの伸びの大きさと、24か月の傾きの向きの食い違い
    bg = pd.DataFrame(by_g)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar(bg.B_trend_abs, bg.trend_mismatch * 100, color=ORANGE, width=.55)
    for i, v in enumerate(bg.trend_mismatch * 100):
        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9)
    ax.set_ylim(0, 60)
    ax.set_xlabel("商品Bの1年あたりの伸び・減りの大きさ（作成者が置いた値）")
    ax.set_ylabel("24か月の傾きの向きが\n食い違った会社の割合（%）")
    ax.set_title("Bの伸びが小さいほど、Bの上端の向きはBの向きと食い違う")
    save(fig, "a822_trend.png", SRC, y=-0.05)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
