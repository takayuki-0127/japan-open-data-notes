"""840 1本のバズで、再生数の平均はどれだけ動くのか？（架空のデータ）

架空の動画アカウント。1か月に20本投稿する。ふだんの投稿の再生数は対数正規分布
（中央値3,000回・対数の標準偏差0.7）。投稿1本ごとに2%の確率で「バズ」が起き、
再生数がふだんの値の約50倍（対数正規、中央値50倍・対数の標準偏差0.5）になる。
アカウントの実力（ふだんの再生数の分布とバズの起きやすさ）は月が変わっても同じと置き、
月ごとの「平均」「中央値」「上位1本を除いた平均」が、実力が同じでもどれだけ動くかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 840
SRC = "架空の動画アカウントの再生数（作成者が乱数で作成、seed 840）"
rng = np.random.default_rng(SEED)
BASE_MED, BASE_SIG = 3000, 0.7
P_BUZZ, BUZZ_MED, BUZZ_SIG = 0.02, 50, 0.5
N_POST = 20
N_MONTH = 20000
METRICS = ["平均", "中央値", "上位1本を除いた平均"]


def make_months(rng, n_month, n_post=N_POST, base_med=BASE_MED, sig=BASE_SIG, p_buzz=P_BUZZ, lift=1.0):
    base = np.exp(rng.normal(np.log(base_med * lift), sig, (n_month, n_post)))
    buzz = rng.random((n_month, n_post)) < p_buzz
    mult = np.exp(rng.normal(np.log(BUZZ_MED), BUZZ_SIG, (n_month, n_post)))
    views = np.where(buzz, base * mult, base)
    return views, buzz


def metrics(views):
    s = np.sort(views, axis=1)
    return {"平均": views.mean(1), "中央値": np.median(views, 1), "上位1本を除いた平均": s[:, :-1].mean(1)}


def summarize(rng, n_post=N_POST, sig=BASE_SIG, p_buzz=P_BUZZ, n_month=N_MONTH):
    """実力が同じ月どうしの動き：+50%以上に見える月の割合、前月比±30%以上の割合、+20%の改善を当てる割合"""
    v, b = make_months(rng, n_month, n_post, sig=sig, p_buzz=p_buzz)
    m = metrics(v)
    up, _ = make_months(rng, n_month, n_post, sig=sig, p_buzz=p_buzz, lift=1.2)
    dn, _ = make_months(rng, n_month, n_post, sig=sig, p_buzz=p_buzz, lift=0.8)
    mu, md = metrics(up), metrics(dn)
    out = {"months_with_buzz": round(float(b.any(1).mean()), 4)}
    for k in METRICS:
        x = m[k]
        typ = np.median(x)
        ratio = x[1:] / x[:-1]
        out[k] = {"typical_month": round(float(typ), 1),
                  "share_ge_1_5x_typical": round(float((x >= 1.5 * typ).mean()), 4),
                  "share_mom_change_ge_30pct": round(float(((ratio >= 1.3) | (ratio <= 1 / 1.3)).mean()), 4),
                  "p10_ratio": round(float(np.quantile(x / typ, .1)), 3),
                  "p90_ratio": round(float(np.quantile(x / typ, .9)), 3),
                  "max_ratio": round(float((x / typ).max()), 2),
                  "P_up_when_lift_1_2": round(float((mu[k] > x).mean()), 4),
                  "P_down_when_lift_0_8": round(float((md[k] < x).mean()), 4)}
    return out, v, b, m


def main():
    # 1) 例の1か月：ふだんの20本、うち1本をバズ（30万回）に置きかえる
    month = np.round(np.exp(rng.normal(np.log(BASE_MED), BASE_SIG, N_POST))).astype(int)
    buzz_views = 300000
    idx = 11
    with_buzz = month.copy(); with_buzz[idx] = buzz_views
    s_wb = np.sort(with_buzz)
    ex = {"buzz_views": buzz_views, "replaced_views": int(month[idx]),
          "mean_before": round(float(month.mean()), 1), "mean_after": round(float(with_buzz.mean()), 1),
          "mean_ratio": round(float(with_buzz.mean() / month.mean()), 2),
          "median_before": float(np.median(month)), "median_after": float(np.median(with_buzz)),
          "trim1_after": round(float(s_wb[:-1].mean()), 1),
          "buzz_share_of_total": round(float(buzz_views / with_buzz.sum()), 3),
          "posts_above_mean_after": int((with_buzz > with_buzz.mean()).sum())}

    # 2) バズの大きさと投稿本数で、平均は何倍になるか（式：ふだんの1本の期待値 E を使う）
    e_base = BASE_MED * np.exp(BASE_SIG ** 2 / 2)
    sizes = [10000, 30000, 100000, 300000, 1000000]
    rows = []
    for n in [10, 20, 60]:
        for x in sizes:
            rows.append({"posts_per_month": n, "buzz_views": x,
                         "mean_ratio": round(((n - 1) * e_base + x) / (n * e_base), 3)})
    size_tab = pd.DataFrame(rows)
    size_tab.to_csv(RES / "buzz_size_mean_ratio.csv", index=False)

    # 3) 実力が同じ月を2万か月：指標ごとの動き
    base, v, b, m = summarize(np.random.default_rng(SEED * 10))
    pooled_mean = float(v.mean())
    base["long_run_mean_all_posts"] = round(pooled_mean, 1)
    base["share_months_mean_below_long_run"] = round(float((m["平均"] < pooled_mean).mean()), 4)
    base["expected_base_post"] = round(float(e_base), 1)

    # 4) 確かめ：バズの起きやすさ・ふだんの散らばり・投稿本数を変える
    rob = []
    settings = [("基本（バズ2%・散らばり0.7・20本）", dict()),
                ("バズ0.5%", dict(p_buzz=0.005)), ("バズ5%", dict(p_buzz=0.05)),
                ("散らばり0.5", dict(sig=0.5)), ("散らばり1.0", dict(sig=1.0)),
                ("1か月10本", dict(n_post=10)), ("1か月60本", dict(n_post=60)),
                ("バズなし", dict(p_buzz=0.0))]
    for i, (name, kw) in enumerate(settings):
        o = base if i == 0 else summarize(np.random.default_rng(SEED * 100 + i), **kw)[0]
        for k in METRICS:
            rob.append({"setting": name, "metric": k, "months_with_buzz": o["months_with_buzz"],
                        "share_ge_1_5x_typical": o[k]["share_ge_1_5x_typical"],
                        "share_mom_change_ge_30pct": o[k]["share_mom_change_ge_30pct"],
                        "P_up_when_lift_1_2": o[k]["P_up_when_lift_1_2"]})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    # data：12か月分の投稿（1年）
    v12, b12 = make_months(np.random.default_rng(SEED + 1), 12)
    d = pd.DataFrame({"month": np.repeat(np.arange(1, 13), N_POST), "post": np.tile(np.arange(1, N_POST + 1), 12),
                      "views": np.round(v12.ravel()).astype(int), "is_buzz": b12.ravel().astype(int)})
    d.to_csv(DATA / "posts_12months.csv", index=False)
    g = d.groupby("month").views
    year = pd.DataFrame({"mean": g.mean().round(1), "median": g.median(), "buzz_posts": d.groupby("month").is_buzz.sum()})
    year.to_csv(RES / "year_by_month.csv")

    out = {"example_month": ex, "buzz_size_mean_ratio": size_tab.to_dict("records"),
           "same_ability_20000_months": base, "robustness": rob.to_dict("records"),
           "year_by_month": year.reset_index().to_dict("records")}
    json.dump(out, open(RES / "a840_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の1か月
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    col = [ORANGE if i == idx else BLUE for i in range(N_POST)]
    ax.bar(np.arange(1, N_POST + 1), with_buzz, color=col)
    ax.set_yscale("log"); ax.set_ylim(500, 1e6)
    ax.axhline(ex["mean_after"], color=ORANGE, ls="--", lw=1.2)
    ax.axhline(ex["median_after"], color=INK, ls=":", lw=1.2)
    ax.axhline(ex["mean_before"], color=GRAY, ls="-", lw=1)
    ax.text(20.6, ex["mean_after"], f"バズを入れた平均\n{ex['mean_after']:,.0f}回", color=ORANGE, fontsize=8.5, va="center")
    ax.text(20.6, ex["median_after"] * 0.72, f"中央値 {ex['median_after']:,.0f}回", color=INK, fontsize=8.5, va="center")
    ax.text(20.6, ex["mean_before"] * 1.35, f"バズ前の平均 {ex['mean_before']:,.0f}回", color=GRAY, fontsize=8.5, va="center")
    ax.set_xlabel("その月の投稿（1〜20本目）"); ax.set_ylabel("再生数（対数の目盛り）")
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_title(f"1本が30万回になると、平均は{ex['mean_ratio']:.1f}倍、中央値はほぼ同じ")
    save(fig, "a840_month.png", SRC)

    # 図2：実力が同じ2万か月の、指標の動き（ふつうの月を1とした比）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.exp(np.linspace(np.log(0.4), np.log(12), 70))
    for k, c in [("平均", ORANGE), ("中央値", BLUE), ("上位1本を除いた平均", GREEN)]:
        x = m[k] / np.median(m[k])
        ax.hist(x, bins=bins, histtype="step", lw=1.6, color=c, density=True, label=k)
    ax.set_xscale("log"); ax.set_xticks([0.5, 1, 1.5, 2, 3, 5, 10]); ax.set_xticklabels(["0.5", "1", "1.5", "2", "3", "5", "10"])
    ax.axvline(1.5, color=GRAY, ls="--", lw=1); ax.text(1.53, ax.get_ylim()[1] * 0.9, "ふつうの月の1.5倍", color=GRAY, fontsize=8.5)
    ax.set_xlabel("その月の値 ÷ ふつうの月（中央の月）の値（対数の目盛り）"); ax.set_yticks([])
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("実力が同じでも、月の平均だけは右に長く伸びる（2万か月）")
    save(fig, "a840_months.png", SRC)

    # 図3：バズの大きさと投稿本数で、平均は何倍になるか
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for n, c in [(10, ORANGE), (20, BLUE), (60, GREEN)]:
        t = size_tab[size_tab.posts_per_month == n]
        ax.plot(t.buzz_views, t.mean_ratio, marker="o", color=c, label=f"1か月{n}本")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(sizes); ax.set_xticklabels(["1万", "3万", "10万", "30万", "100万"])
    ax.set_yticks([1, 2, 5, 10, 20]); ax.set_yticklabels(["1", "2", "5", "10", "20"])
    ax.set_xlabel("バズした1本の再生数"); ax.set_ylabel("月の平均がふだんの何倍になるか（対数）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("平均の動きは「バズの大きさ ÷ 投稿本数」でほぼ決まる")
    save(fig, "a840_size.png", SRC)
    print(json.dumps({k: out[k] for k in ["example_month", "same_ability_20000_months"]}, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print(year)


if __name__ == "__main__":
    main()
