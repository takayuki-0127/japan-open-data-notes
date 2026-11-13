"""512 割合を小数1桁で表示すると、前月比の増減が「0.0」や逆の向きに見える月は何か月あるのか（実務の型）

架空の月次 KPI（率、単位は%）を作り、表示の桁（整数・小数1桁・小数2桁）で丸めた値どうしの差と、
丸める前の差を比べる。構成比の表では、丸めた値の合計が100.0にならない表の割合を数える。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 512
SRC = "架空の月次KPI（作成者が乱数で作成、seed 512）"


def round_half_up(x, nd):
    """表示の丸め（四捨五入）。2進数の誤差で .x5 が切り下がらないよう、10進で丸める"""
    q = 10.0 ** nd
    return np.floor(np.round(x * q, 9) + 0.5) / q


def make_kpis(n=300, months=37, seed=SEED):
    """n 本の率（%）を37か月分。水準は0.5〜15%、月ごとの動きの大きさは0.02〜0.5ポイント"""
    rng = np.random.default_rng(seed)
    lvl = rng.uniform(0.5, 15, n)
    sd = np.exp(rng.uniform(np.log(0.02), np.log(0.5), n))
    steps = rng.normal(0, 1, (n, months)) * sd[:, None]
    x = np.clip(lvl[:, None] + np.cumsum(steps, axis=1), 0.05, None)
    return pd.DataFrame(x, index=[f"K{i:03d}" for i in range(n)]), sd


def compare(x, nd):
    d = np.diff(x, axis=1)                         # 丸める前の差
    r = round_half_up(x, nd); dr = np.diff(r, axis=1)   # 表示どうしの差（読む人が引き算する差）
    dround = round_half_up(np.abs(d), nd) * np.sign(d)  # 「前月差」として別に表示する値
    unit = 10.0 ** -nd
    zero = np.isclose(dr, 0)
    flip = (np.sign(dr) * np.sign(d) < 0)
    mism = ~np.isclose(dr, dround)
    return {"桁": nd, "月数": int(d.size),
            "表示の差が0に見える": float(zero.mean()),
            "向きが逆に見える": float(flip.mean()),
            "表示どうしの差と前月差の表示が食い違う": float(mism.mean()),
            "本当の差が表示の1単位以上なのに0に見える": float((zero & (np.abs(d) >= unit)).mean())}, d, dr


def from_rounded_counts(x, seed=SEED + 2):
    """率を、千人単位に丸めた分子と分母から計算し直す（公表の表から率を出すときの形）"""
    rng = np.random.default_rng(seed)
    n, m = x.shape
    den = rng.uniform(20, 500, n)[:, None] * 1000 * np.exp(np.cumsum(rng.normal(0, 0.003, (n, m)), axis=1))
    num = den * x / 100
    rate_shown = np.round(num / 1000) / np.round(den / 1000) * 100       # 千人単位の表から計算した率
    d_true = np.diff(num / den * 100, axis=1)
    d_shown = np.diff(round_half_up(rate_shown, 1), axis=1)               # それを小数1桁で表示
    flip = np.sign(d_shown) * np.sign(d_true) < 0
    return {"向きが逆に見える": float(flip.mean()), "0.0に見える": float(np.isclose(d_shown, 0).mean()),
            "逆に見える月の本当の差_中央値": float(np.median(np.abs(d_true[flip]))) if flip.any() else None,
            "逆に見える月の表示の差_最大": float(np.abs(d_shown[flip]).max()) if flip.any() else None,
            "分母_千人_中央値": float(np.median(den / 1000))}, flip, den


def shares_table(k, n_tab, rng, nd=1):
    w = rng.dirichlet(np.ones(k), n_tab) * 100
    r = round_half_up(w, nd)
    tot = np.round(r.sum(axis=1), 6)
    return float((~np.isclose(tot, 100.0)).mean()), float(np.abs(tot - 100).max())


def main():
    x, sd = make_kpis()
    x.round(6).to_csv(DATA / "fictional_kpi_rates.csv")
    rows, keep = [], {}
    for nd in [0, 1, 2]:
        s, d, dr = compare(x.to_numpy(), nd)
        rows.append(s); keep[nd] = (d, dr)
    tab = pd.DataFrame(rows); tab.to_csv(RES / "by_digits.csv", index=False)
    # 動きの大きさ（表示の1単位に対する本当の差の大きさ）ごとの「0に見える」「逆に見える」割合（小数1桁）
    d, dr = keep[1]
    ratio = np.abs(d) / 0.1
    bins = [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 100]
    cut = pd.cut(ratio.ravel(), bins, right=False)
    g = pd.DataFrame({"bin": cut, "zero": np.isclose(dr, 0).ravel(), "flip": (np.sign(dr) * np.sign(d) < 0).ravel()}).groupby("bin", observed=True).agg(件数=("zero", "size"), 零=("zero", "mean"), 逆=("flip", "mean"))
    g.to_csv(RES / "by_change_size.csv")
    # KPIごと：36か月のうち「0.0」に見える月の数
    per = pd.Series(np.isclose(dr, 0).sum(axis=1), index=x.index)
    per_flip = pd.Series((np.sign(dr) * np.sign(d) < 0).sum(axis=1), index=x.index)
    small = sd < 0.1
    # 構成比：k 区分の表を1万枚ずつ
    rng = np.random.default_rng(SEED + 1)
    comp = []
    for k in [2, 3, 4, 5, 6, 8, 10, 15, 20]:
        p, mx = shares_table(k, 10000, rng)
        p0, _ = shares_table(k, 10000, rng, nd=0)
        comp.append({"区分の数": k, "小数1桁で100.0にならない表": round(p, 4), "合計のずれの最大": round(mx, 2), "整数で100にならない表": round(p0, 4)})
    comp = pd.DataFrame(comp); comp.to_csv(RES / "shares_sum_not_100.csv", index=False)
    cnt, cflip, den = from_rounded_counts(x.to_numpy())
    small_den = (den[:, 0] < 100000)
    cnt["分母10万人未満のKPI_逆に見える"] = float(cflip[small_den].mean())
    cnt["分母10万人以上のKPI_逆に見える"] = float(cflip[~small_den].mean())
    json.dump(cnt, open(RES / "from_rounded_counts.json", "w"), ensure_ascii=False, indent=1)
    # SQL：DuckDB の ROUND は .x5 をどう丸めるか（2進の誤差のある値で確かめる）
    con = duckdb.connect()
    sq = con.execute(open(SQL / "02_round_duckdb.sql").read()).df()
    sq.to_csv(RES / "duckdb_round_check.csv", index=False)
    out = {"seed": SEED, "KPIの本数": int(x.shape[0]), "前月比の月数": int(d.size), "桁ごと": rows,
           "小数1桁_KPIごと_0に見える月_中央値": float(per.median()), "小数1桁_動きの小さいKPI(sd<0.1)_0に見える月_平均": float(per[small].mean()),
           "小数1桁_動きの小さいKPI_逆に見える月_平均": float(per_flip[small].mean()), "動きの小さいKPIの本数": int(small.sum()),
           "構成比": comp.to_dict("records"), "千人単位の分子分母から計算した率": cnt}
    json.dump(out, open(RES / "a512_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：桁ごとの割合（＋千人単位の分子分母から計算した率）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    lab = ["整数で表示", "小数1桁で表示", "小数2桁で表示", "千人単位の分子・分母\nから計算して小数1桁"]; xx = np.arange(4); wd = 0.27
    vals = {"表示の差が0に見える": list(tab["表示の差が0に見える"] * 100) + [cnt["0.0に見える"] * 100],
            "向きが逆に見える": list(tab["向きが逆に見える"] * 100) + [cnt["向きが逆に見える"] * 100],
            "表示どうしの差と前月差の表示が食い違う": list(tab["表示どうしの差と前月差の表示が食い違う"] * 100) + [np.nan]}
    for j, (k, c) in enumerate([("表示の差が0に見える", GRAY), ("向きが逆に見える", ORANGE), ("表示どうしの差と前月差の表示が食い違う", BLUE)]):
        v = np.array(vals[k])
        ax.bar(xx + (j - 1) * wd, np.nan_to_num(v), wd, color=c, label=k)
        for a_, b_ in zip(xx, v):
            if not np.isnan(b_): ax.text(a_ + (j - 1) * wd, b_ + 0.8, f"{b_:.1f}", ha="center", fontsize=8)
    ax.set_xticks(xx, lab, fontsize=9); ax.set_ylabel("前月比の月のうちの割合（%）")
    ax.set_title("値を丸めて表示しても向きは逆にならないが、丸めた数から率を出すと逆になる")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a512_by_digits.png", SRC + "。300本×36か月＝10,800か月")
    # 図2：動きの大きさごと
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    labs = ["0.025未満", "0.025〜0.05", "0.05〜0.075", "0.075〜0.1", "0.1〜0.15", "0.15〜0.2", "0.2〜0.3", "0.3以上"]
    ax.plot(labs, g["零"] * 100, marker="o", color=GRAY, label="0.0 に見える")
    ax.plot(labs, g["逆"] * 100, marker="s", color=ORANGE, label="向きが逆に見える")
    ax.set_xlabel("本当の前月差の大きさ（ポイント）"); ax.set_ylabel("割合（%）"); ax.tick_params(axis="x", labelsize=8.5, rotation=20)
    ax.set_title("小数1桁の表示：本当の差が0.1未満だと、多くが0.0に見える")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a512_by_change_size.png", SRC + "。小数1桁で表示した場合")
    # 図3：構成比
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(comp["区分の数"], comp["小数1桁で100.0にならない表"] * 100, marker="o", color=BLUE, label="小数1桁で表示")
    ax.plot(comp["区分の数"], comp["整数で100にならない表"] * 100, marker="s", color=ORANGE, label="整数で表示")
    ax.set_xlabel("構成比の区分の数"); ax.set_ylabel("合計が100にならない表の割合（%）")
    ax.set_title("区分が多い構成比ほど、表示の合計は100にならない")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a512_shares.png", "架空の構成比の表（区分の数ごとに1万枚、seed 513）")
    print(tab.to_string()); print(g.to_string()); print(comp.to_string()); print(sq.to_string()); print(cnt)
    print({k: v for k, v in out.items() if k not in ("桁ごと", "構成比")})


if __name__ == "__main__":
    main()
