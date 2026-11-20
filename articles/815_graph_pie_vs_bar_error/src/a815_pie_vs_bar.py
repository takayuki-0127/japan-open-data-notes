"""815 円グラフと棒グラフで、割合の読み取りの誤差はどれだけ違うのか？（架空のデータ）

架空の会社2,000社の「商品5つの売上の構成比」を作り、数字の書いていない円グラフと棒グラフから
読み手が割合を読むときの誤差を数える。読み手のくせは作成者が置いたもの（下の READER_* と手がかりの線）。

読み手のくせ（作成者が置いた）：
- 読み手は、いちばん近い「手がかりの線」からの距離を目で測る。読み違いの大きさ（標準偏差）は
  「手がかりの線までの距離 × w」＋ 0.2ポイント。w は円も棒も同じ（基本 0.3）。
- 棒グラフ：手がかりの線は目盛り線（基本は10ポイントごと）。
- 円グラフ：手がかりは円の4分の1（25ポイント）ごと。12時から始まる1つ目の項目以外は、
  始まりの位置が目盛りとずれるので、読み違いを m 倍にする（基本 1.5）。
- 項目の並びは商品A〜Eの決まった順（大きい順に並べ替えない）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 815
SRC = "架空の会社の商品別の売上の構成比（作成者が乱数で作成、seed 815）"
rng = np.random.default_rng(SEED)
N_CO = 2000
FLOOR = 0.2


def make_shares(rng, n=N_CO, k=5, alpha=2.0):
    s = rng.dirichlet(np.full(k, alpha), n) * 100
    return s


def dist_to_ref(x, step):
    """x から、step ごとの線までのいちばん近い距離。step=None は 0 と軸の端だけ"""
    r = np.mod(x, step)
    return np.minimum(r, step - r)


def read_bar(rng, s, w=0.3, grid=10):
    if grid is None:   # 目盛り線なし：手がかりは0と軸の端（いちばん大きい項目を切り上げた10の倍数）
        top = np.ceil(s.max(1, keepdims=True) / 10) * 10
        d = np.minimum(s, top - s)
    else:
        d = dist_to_ref(s, grid)
    sd = w * d + FLOOR
    return s + rng.normal(0, 1, s.shape) * sd


def read_pie(rng, s, w=0.3, m=1.5, quarter=25):
    d = dist_to_ref(s, quarter)
    mult = np.ones(s.shape); mult[:, 1:] = m
    sd = (w * d + FLOOR) * mult
    return s + rng.normal(0, 1, s.shape) * sd


def evaluate(s, est):
    err = np.abs(est - s)
    k = s.shape[1]
    wrong, close = [], []
    for i in range(k):
        for j in range(i + 1, k):
            diff = s[:, i] - s[:, j]
            m = np.abs(diff) <= 3
            close.append(m.sum())
            wrong.append(((np.sign(est[:, i] - est[:, j]) != np.sign(diff)) & m).sum())
    top_ok = (est.argmax(1) == s.argmax(1)).mean()
    return {"mean_abs_error": round(float(err.mean()), 2), "p90_abs_error": round(float(np.quantile(err, .9)), 2),
            "share_off_5pt": round(float((err >= 5).mean()), 3),
            "close_pairs_wrong_order": round(float(sum(wrong) / max(sum(close), 1)), 3),
            "top1_correct": round(float(top_ok), 3)}


def run(rng, s, w=0.3, m=1.5, grid=10, reps=20):
    rows = {"bar": [], "pie": []}
    for _ in range(reps):
        rows["bar"].append(evaluate(s, read_bar(rng, s, w, grid)))
        rows["pie"].append(evaluate(s, read_pie(rng, s, w, m)))
    return {k: {kk: round(float(np.mean([r[kk] for r in v])), 3) for kk in v[0]} for k, v in rows.items()}


def main():
    s = make_shares(rng)
    df = pd.DataFrame(np.round(s, 2), columns=[f"商品{c}" for c in "ABCDE"])
    df.insert(0, "company_id", np.arange(1, N_CO + 1))
    df.to_csv(DATA / "shares.csv", index=False)

    base = run(np.random.default_rng(SEED * 10), s)

    # 項目の位置ごと（円の1つ目と2つ目以降）
    r2 = np.random.default_rng(SEED * 11)
    eb = np.abs(np.concatenate([read_bar(r2, s) - s for _ in range(20)]))
    ep = np.abs(np.concatenate([read_pie(r2, s) - s for _ in range(20)]))
    by_pos = pd.DataFrame({"position": [f"{i+1}つ目（商品{c}）" for i, c in enumerate("ABCDE")],
                           "bar_mean_abs_error": np.round(eb.mean(0), 2), "pie_mean_abs_error": np.round(ep.mean(0), 2)})
    by_pos.to_csv(RES / "by_position.csv", index=False)

    # 本当の割合の帯ごと
    bands = []
    ss = np.tile(s, (20, 1))
    for lo, hi in [(0, 10), (10, 20), (20, 30), (30, 100)]:
        mk = (ss >= lo) & (ss < hi)
        bands.append({"true_share": f"{lo}〜{hi}%" if hi < 100 else f"{lo}%以上", "items": int(mk.sum() / 20),
                      "bar_mean_abs_error": round(float(eb[mk].mean()), 2), "pie_mean_abs_error": round(float(ep[mk].mean()), 2)})
    bands = pd.DataFrame(bands)
    bands.to_csv(RES / "by_true_share.csv", index=False)

    # 確かめ：置き方を変える
    sens = []
    settings = [("基本（w=0.3・m=1.5・目盛り線10ごと・5項目）", dict(), 5),
                ("w=0.15（読み手が上手）", dict(w=0.15), 5), ("w=0.5（読み手が下手）", dict(w=0.5), 5),
                ("m=1（円の2つ目以降も1つ目と同じ）", dict(m=1.0), 5), ("m=2", dict(m=2.0), 5),
                ("棒の目盛り線5ポイントごと", dict(grid=5), 5), ("棒の目盛り線20ポイントごと", dict(grid=20), 5),
                ("棒の目盛り線なし", dict(grid=None), 5),
                ("棒の目盛り線なし・m=1", dict(grid=None, m=1.0), 5),
                ("3項目", dict(), 3), ("8項目", dict(), 8)]
    for i, (name, kw, k) in enumerate(settings):
        s2 = s if k == 5 else make_shares(np.random.default_rng(SEED + k), N_CO, k)
        r = run(np.random.default_rng(SEED * 100 + i), s2, **kw)
        sens.append({"setting": name, "bar_mean_abs_error": r["bar"]["mean_abs_error"],
                     "pie_mean_abs_error": r["pie"]["mean_abs_error"],
                     "ratio_pie_over_bar": round(r["pie"]["mean_abs_error"] / r["bar"]["mean_abs_error"], 2),
                     "bar_close_wrong": r["bar"]["close_pairs_wrong_order"], "pie_close_wrong": r["pie"]["close_pairs_wrong_order"],
                     "bar_top1": r["bar"]["top1_correct"], "pie_top1": r["pie"]["top1_correct"]})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    share_band = {"lt5": round(float((s < 5).mean()), 3), "5_40": round(float(((s >= 5) & (s < 40)).mean()), 3),
                  "ge40": round(float((s >= 40).mean()), 3), "median": round(float(np.median(s)), 2)}
    out = {"n_companies": N_CO, "items": 5, "true_share_dist": share_band, "base": base,
           "by_position": by_pos.to_dict("records"), "by_true_share": bands.to_dict("records"),
           "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a815_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ構成比を円と棒で（1社分、数字は書かない）
    i = int(np.argsort(np.abs(np.sort(s, 1)[:, -1] - np.sort(s, 1)[:, -2]))[N_CO // 10])
    v = s[i]; labs = [f"商品{c}" for c in "ABCDE"]
    cols = [BLUE, ORANGE, GREEN, GRAY, LIGHT]
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.9), gridspec_kw={"width_ratios": [1, 1.25]})
    axs[0].pie(v, labels=labs, colors=cols, startangle=90, counterclock=False,
               wedgeprops={"edgecolor": "white", "linewidth": 1.2}, textprops={"fontsize": 10})
    axs[0].set_title("円グラフ（12時から時計回り）", fontsize=11)
    axs[1].barh(labs[::-1], v[::-1], color=cols[::-1])
    axs[1].set_xlim(0, np.ceil(v.max() / 10) * 10); axs[1].xaxis.grid(True, color="#dddddd"); axs[1].set_axisbelow(True)
    axs[1].set_xlabel("構成比（%）"); axs[1].set_title("棒グラフ（目盛り線10ポイントごと）", fontsize=11)
    order = np.argsort(-v)
    fig.suptitle(f"同じ1社の構成比。いちばん大きいのは商品{'ABCDE'[order[0]]}（{v[order[0]]:.1f}%）、"
                 f"2番目は商品{'ABCDE'[order[1]]}（{v[order[1]]:.1f}%）", fontsize=11.5)
    fig.tight_layout()
    save(fig, "a815_pair.png", SRC)

    # 図2：誤差の大きさ（基本）
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.6))
    for ax, key, lab, fmt in [(axs[0], "mean_abs_error", "読み違いの平均（ポイント）", "{:.1f}"),
                              (axs[1], "close_pairs_wrong_order", "差3ポイント以内の2項目の\n大小を読み違えた割合（%）", "{:.0f}%")]:
        vals = [base["bar"][key], base["pie"][key]]
        if "%" in fmt:
            vals = [x * 100 for x in vals]
        ax.bar(["棒グラフ", "円グラフ"], vals, color=[BLUE, ORANGE], width=0.55)
        for xi, y in enumerate(vals):
            ax.text(xi, y + max(vals) * 0.03, fmt.format(y), ha="center", fontsize=10)
        ax.set_ylabel(lab); ax.set_ylim(0, max(vals) * 1.2)
    fig.suptitle("置いた読み手のくせでは、円グラフの読み違いは棒グラフより大きい（2,000社×20回）", fontsize=11.5)
    fig.tight_layout()
    save(fig, "a815_error.png", SRC)

    # 図3：確かめ（円÷棒の誤差の比）
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    sv = sens.iloc[::-1]
    col = [ORANGE if r >= 1 else BLUE for r in sv.ratio_pie_over_bar]
    ax.barh(sv.setting, sv.ratio_pie_over_bar, color=col)
    for yi, r in enumerate(sv.ratio_pie_over_bar):
        ax.text(max(r, 1) + 0.05, yi, f"{r:.2f}倍", va="center", fontsize=9)
    ax.axvline(1, color=INK, lw=1)
    ax.set_xlabel("円グラフの読み違い ÷ 棒グラフの読み違い（1より大きいと円が不利）")
    ax.set_xlim(0, sv.ratio_pie_over_bar.max() * 1.18)
    ax.set_title("差の大きさは、棒の目盛り線の間隔と置いたくせで大きく動く")
    save(fig, "a815_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
