"""924 平均点が年ごとに違う試験の点は、そのまま比べてよいのか？（架空のデータ）

架空の社内の資格試験を5年分作る。毎年50問（1問2点の100点満点）。
そのうち10問は毎年同じ「共通の問題」、残り40問は年ごとに作り直し、年ごとに難しさが違う。
受ける人の実力の平均も年ごとに違う。
本当の点は「1年目の50問を解いたときの正答率の見込み×100」（1年目の物差し）として作成者が分かる形で置き、
年ごとの点を1年目の物差しに直す3つの方法を比べる。
 A そのまま比べる
 B 年ごとに平均と標準偏差を1年目にそろえる（受ける人の実力は毎年同じとみなす）
 C 共通の10問でつなぐ（共通の問題の点を通して、2段の直線で1年目の点に直す）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 924
SRC = "架空の社内の資格試験5年分（作成者が乱数で作成、seed 924）"
N_YEAR, N_PER, N_ITEM, N_ANCHOR = 5, 1000, 50, 10
DIFF = np.array([0.0, 0.4, -0.3, 0.3, -0.5])     # 年ごとの問題の難しさ（+は難しい。共通の問題以外の40問）
COHORT = np.array([0.0, 0.2, -0.2, -0.1, 0.3])   # 年ごとの受ける人の実力の平均
PASS = 60
METHODS = ["A そのまま", "B 年ごとに平均と散らばりをそろえる", "C 共通の10問でつなぐ"]


def prob(theta, b):
    return 1.0 / (1.0 + np.exp(-1.7 * (theta - b)))


def simulate(rng, diff_scale=1.0, cohort_scale=1.0, n_anchor=N_ANCHOR, n_per=N_PER, leak=0.0):
    """5年分を作り、方法ごとに1年目の物差しへ直した点を返す。
    leak：2年目以降、共通の問題だけが易しくなる幅（問題が出回って覚えられる場合）"""
    anc_b = rng.normal(0, 1, n_anchor)
    forms = [rng.normal(DIFF[y] * diff_scale, 1, N_ITEM - n_anchor) for y in range(N_YEAR)]
    b1 = np.concatenate([anc_b, forms[0]])
    rows = []
    for y in range(N_YEAR):
        th = rng.normal(COHORT[y] * cohort_scale, 1, n_per)
        anc_eff = anc_b - (leak if y > 0 else 0.0)
        b = np.concatenate([anc_eff, forms[y]])
        c = rng.random((n_per, N_ITEM)) < prob(th[:, None], b[None, :])
        raw = 100 * c.mean(1)
        anc = 100 * c[:, :n_anchor].mean(1)
        true1 = 100 * prob(th[:, None], b1[None, :]).mean(1)
        rows.append(pd.DataFrame({"year": y + 1, "theta": th, "raw": raw, "anchor": anc, "true_on_year1": true1}))
    df = pd.concat(rows, ignore_index=True)
    df.attrs["form_mean_b"] = [float(f.mean()) for f in forms]
    st = df.groupby("year").agg(mx=("raw", "mean"), sx=("raw", "std"), ma=("anchor", "mean"), sa=("anchor", "std"))
    s1 = st.loc[1]
    o = st.loc[df.year].reset_index(drop=True)
    df["A"] = df.raw
    df["B"] = s1.mx + s1.sx * (df.raw - o.mx) / o.sx
    a_on_y = o.ma + o.sa / o.sx * (df.raw - o.mx)          # その年の点 → 共通の問題の点
    df["C"] = s1.mx + s1.sx / s1.sa * (a_on_y - s1.ma)     # 共通の問題の点 → 1年目の点
    return df


def evaluate(df):
    res = {}
    for k, name in zip("ABC", METHODS):
        g = df.assign(err=df[k] - df.true_on_year1, ok=(df[k] >= PASS) == (df.true_on_year1 >= PASS))
        by = g.groupby("year").agg(bias=("err", "mean"), ok=("ok", "mean"),
                                   pass_rate=(k, lambda s: (s >= PASS).mean()))
        res[k] = {"year_bias": by.bias.values, "max_abs_bias": float(by.bias.abs().max()),
                  "accuracy": float(g.ok.mean()), "pass_rate": by.pass_rate.values}
    res["true_pass_rate"] = df.groupby("year").true_on_year1.apply(lambda s: (s >= PASS).mean()).values
    res["true_mean"] = df.groupby("year").true_on_year1.mean().values
    res["raw_mean"] = df.groupby("year").raw.mean().values
    return res


def f3(x):
    return round(float(x), 3)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 例の5年分（各1,000人）
    df = simulate(rng)
    df.insert(1, "person_id", df.groupby("year").cumcount() + 1)
    df.round(3).to_csv(DATA / "examinees_5years.csv", index=False)
    form_mean_b = df.attrs["form_mean_b"]
    ev = evaluate(df)
    year_tbl = pd.DataFrame({"year": np.arange(1, N_YEAR + 1), "form_difficulty": DIFF, "cohort_mean": COHORT,
                             "form_mean_difficulty_drawn_40": form_mean_b,
                             "raw_mean": ev["raw_mean"], "true_mean_on_year1": ev["true_mean"],
                             "raw_mean_minus_year1": ev["raw_mean"] - ev["raw_mean"][0],
                             "true_mean_minus_year1": ev["true_mean"] - ev["true_mean"][0],
                             "raw_minus_true": ev["A"]["year_bias"], "B_minus_true": ev["B"]["year_bias"],
                             "C_minus_true": ev["C"]["year_bias"],
                             "true_pass_rate": ev["true_pass_rate"], "A_pass_rate": ev["A"]["pass_rate"],
                             "B_pass_rate": ev["B"]["pass_rate"], "C_pass_rate": ev["C"]["pass_rate"]}).round(3)
    year_tbl.to_csv(RES / "by_year_example.csv", index=False)
    # 同じ「そのままの点58〜62点」の人の本当の点（年ごと）
    near60 = df[df.raw.between(58, 62)].groupby("year").true_on_year1.agg(["mean", "count"]).round(3)
    near60.columns = ["true_mean_of_raw58_62", "n"]
    near60.to_csv(RES / "raw60_true_by_year.csv")

    # 2) 人と問題を作り直して200回（年ごとの難しさ・受ける人の平均は同じ）
    reps = []
    for r in range(200):
        e = evaluate(simulate(np.random.default_rng(SEED * 1000 + r)))
        for k in "ABC":
            reps.append({"rep": r, "method": k, "max_abs_bias": e[k]["max_abs_bias"], "accuracy": e[k]["accuracy"],
                         **{f"bias_y{y+1}": e[k]["year_bias"][y] for y in range(N_YEAR)}})
    reps = pd.DataFrame(reps)
    rep_sum = reps.groupby("method").agg(max_abs_bias_mean=("max_abs_bias", "mean"),
                                         max_abs_bias_p10=("max_abs_bias", lambda s: s.quantile(.1)),
                                         max_abs_bias_p90=("max_abs_bias", lambda s: s.quantile(.9)),
                                         accuracy_mean=("accuracy", "mean"),
                                         **{f"bias_y{y+1}_mean": (f"bias_y{y+1}", "mean") for y in range(N_YEAR)}).round(3)
    rep_sum.to_csv(RES / "methods_200reps.csv")

    # 3) 確かめ：置き方を1つずつ変えると（各50回の平均）
    settings = [("基本", {}),
                ("問題の難しさの差 0倍（問題を選ぶ偶然の差だけ）", {"diff_scale": 0.0}),
                ("問題の難しさの差 0.5倍", {"diff_scale": 0.5}),
                ("問題の難しさの差 2倍", {"diff_scale": 2.0}),
                ("受ける人の差 0倍（毎年同じ）", {"cohort_scale": 0.0}),
                ("受ける人の差 2倍", {"cohort_scale": 2.0}),
                ("共通の問題 5問", {"n_anchor": 5}),
                ("共通の問題 20問", {"n_anchor": 20}),
                ("受ける人 各200人", {"n_per": 200}),
                ("共通の問題が出回り0.3易しくなる", {"leak": 0.3}),
                ("共通の問題が出回り0.6易しくなる", {"leak": 0.6})]
    grid = []
    for i, (name, kw) in enumerate(settings):
        es = [evaluate(simulate(np.random.default_rng(SEED * 77 + i * 1000 + j), **kw)) for j in range(50)]
        row = {"setting": name}
        for k in "ABC":
            row[f"{k}_max_abs_bias"] = f3(np.mean([e[k]["max_abs_bias"] for e in es]))
            row[f"{k}_accuracy"] = f3(np.mean([e[k]["accuracy"] for e in es]))
        grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness.csv", index=False)
    no_leak = grid[~grid.setting.str.contains("出回り")]

    out = {"setting": {"years": N_YEAR, "examinees_per_year": N_PER, "items": N_ITEM, "anchor_items": N_ANCHOR,
                       "form_difficulty_by_year": DIFF.tolist(), "cohort_mean_by_year": COHORT.tolist(),
                       "pass_line_on_year1_scale": PASS},
           "example_by_year": year_tbl.to_dict("records"),
           "example_accuracy": {k: f3(ev[k]["accuracy"]) for k in "ABC"},
           "example_max_abs_bias": {k: f3(ev[k]["max_abs_bias"]) for k in "ABC"},
           "raw58_62_true_by_year": near60.reset_index().to_dict("records"),
           "raw58_62_true_range": [f3(near60.true_mean_of_raw58_62.min()), f3(near60.true_mean_of_raw58_62.max())],
           "raw58_62_true_spread": f3(near60.true_mean_of_raw58_62.max() - near60.true_mean_of_raw58_62.min()),
           "reps200_wrong_share": {k: f3(1 - rep_sum.loc[k, "accuracy_mean"]) for k in "ABC"},
           "reps200": rep_sum.reset_index().to_dict("records"),
           "robustness": grid.to_dict("records"),
           "robustness_no_leak_range": {f"{k}_max_abs_bias": [f3(no_leak[f"{k}_max_abs_bias"].min()),
                                                               f3(no_leak[f"{k}_max_abs_bias"].max())] for k in "ABC"}}
    json.dump(out, open(RES / "a924_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：年ごとの平均点（そのまま）と本当の平均（1年目の物差し）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    yrs = year_tbl.year.values
    ax.plot(yrs, year_tbl.raw_mean, color=ORANGE, marker="o", label="その年の平均点（そのまま）")
    ax.plot(yrs, year_tbl.true_mean_on_year1, color=BLUE, marker="s", lw=2.2, label="本当の平均（1年目の問題で測った見込み）")
    for y, v1, v2 in zip(yrs, year_tbl.raw_mean, year_tbl.true_mean_on_year1):
        up = v1 >= v2
        l1 = y == 1     # 1年目は線と重ならないよう左に置く
        ax.text(y + (-0.1 if l1 else 0.1), v1 + (1.8 if up else -1.8), f"{v1:.1f}", color=ORANGE, fontsize=8.5,
                va="center", ha="right" if l1 else "left")
        left = y == 4   # 4年目は線と重ならないよう左に置く
        ax.text(y + (-0.1 if left else 0.1), v2 + (-1.8 if up else 1.8), f"{v2:.1f}", color=BLUE, fontsize=8.5,
                va="center", ha="right" if left else "left")
    ax.set_xticks(yrs); ax.set_xticklabels([f"{y}年目" for y in yrs]); ax.set_xlim(0.45, 5.6)
    ax.set_ylabel("平均点（100点満点）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
    lo = min(year_tbl.raw_mean.min(), year_tbl.true_mean_on_year1.min()); hi = max(year_tbl.raw_mean.max(), year_tbl.true_mean_on_year1.max())
    ax.set_ylim(lo - 6, hi + 9)
    ax.set_title("平均点の上下は、問題の難しさと受ける人の差がまざったもの（各1,000人）", fontsize=12)
    save(fig, "a924_year_means.png", SRC)

    # 図2：方法ごとの年の平均のずれ（200回の平均）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    w = 0.26
    for k, (m, col) in enumerate(zip("ABC", [ORANGE, GRAY, BLUE])):
        v = [rep_sum.loc[m, f"bias_y{y}_mean"] for y in yrs]
        ax.bar(yrs + (k - 1) * w, v, width=w, color=col, label=METHODS[k])
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(yrs); ax.set_xticklabels([f"{y}年目" for y in yrs])
    ax.set_ylabel("直した点の平均 − 本当の平均（点）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_ylim(-9, 14)
    ax.set_title("そのままは問題の難しさの分、Bは受ける人の差の分だけずれる（200回の平均）", fontsize=12)
    save(fig, "a924_bias_by_method.png", SRC)

    # 図3：確かめ（年の平均のずれの最大）
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    yy = np.arange(len(grid))[::-1]
    h = 0.26
    for k, (m, col) in enumerate(zip("ABC", [ORANGE, GRAY, BLUE])):
        ax.barh(yy + (1 - k) * h, grid[f"{m}_max_abs_bias"], height=h, color=col, label=METHODS[k])
    ax.set_yticks(yy); ax.set_yticklabels(grid.setting, fontsize=9)
    ax.set_xlabel("5年のうち、年の平均のずれがいちばん大きい年のずれ（点、各50回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=3)
    ax.set_title("共通の問題でつなぐ方法は、共通の問題が出回ると崩れる", fontsize=12, pad=26)
    save(fig, "a924_settings.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])
    print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
