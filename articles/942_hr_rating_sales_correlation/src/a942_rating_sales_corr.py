"""942 評価の点と売上の相関は、評価の正しさを示すのか？（架空のデータ）

架空の会社の営業の人たち。作成者が人ごとに「本当の貢献」を置く。本当の貢献は、売る力と、
売上に出ない仕事（後輩の指導・チームの仕事など）の2つでできている。
年の売上は、売る力・担当地域の良さ・その年の運でできている。
評価者の付け方を4通り置き、評価の点が売上とどれだけ相関するか、本当の貢献とどれだけ相関するかを比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 942
SRC = "架空の会社の営業の評価と売上（作成者が乱数で作成、seed 942）"
LUCK = 0.2          # 売上のうち、その年の運の分（分散の割合）
BASE_T, BASE_W = 0.4, 0.5   # 売上のうち担当地域の分、本当の貢献のうち売る力の分
RATERS = ["売上を見て付ける", "半分ずつ", "仕事ぶりを見て付ける", "本当の貢献そのまま（理想）"]


def z(x, axis=None):
    m = x.mean(axis=axis, keepdims=True) if axis is not None else x.mean()
    s = x.std(axis=axis, keepdims=True) if axis is not None else x.std()
    return (x - m) / s


def make(rng, n, t=BASE_T, w=BASE_W):
    """n 人分。t：売上のうち担当地域の分、w：本当の貢献のうち売る力の分"""
    S, G, L, O = (rng.standard_normal(n) for _ in range(4))
    E1, E2, E3 = (rng.standard_normal(n) for _ in range(3))
    y = np.sqrt(1 - t - LUCK) * S + np.sqrt(t) * G + np.sqrt(LUCK) * L
    T = np.sqrt(w) * S + np.sqrt(1 - w) * O
    zy = z(y)
    ra = np.sqrt(0.8) * zy + np.sqrt(0.2) * E1
    rc = np.sqrt(0.7) * z(zy + z(T)) + np.sqrt(0.3) * E2
    rb = np.sqrt(0.6) * T + np.sqrt(0.4) * E3
    return dict(skill=S, territory=G, luck=L, other=O, true=T, y=y, A=ra, C=rc, B=rb, P=T)


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def r2(x):
    return round(float(x), 2) + 0.0   # -0.0 を 0.0 にする


def top_overlap(r, T, q=0.2):
    k = int(len(T) * q)
    return len(set(np.argsort(-r)[:k]) & set(np.argsort(-T)[:k])) / k


def summarize(d):
    out = []
    for name, key in zip(RATERS, ["A", "C", "B", "P"]):
        out.append({"rater": name, "corr_sales": r2(corr(d[key], d["y"])),
                    "corr_true": r2(corr(d[key], d["true"])),
                    "corr_territory": r2(corr(d[key], d["territory"])),
                    "top20_overlap_pct": round(100 * top_overlap(d[key], d["true"]), 1)})
    return out


def dept_corr(rng, size, n_dept=20000):
    """1部署 size 人の中で、評価と売上の相関（部署ごと）"""
    d = make(rng, n_dept * size)
    rz = rng.standard_normal(n_dept * size)   # 売上も仕事も見ないでたらめな付け方
    def per(r):
        a, b = z(r.reshape(n_dept, size), 1), z(d["y"].reshape(n_dept, size), 1)
        return (a * b).mean(1)
    cb, ca, cr = per(d["B"]), per(d["A"]), per(rz)
    return {"size": size, "B_corr_sales_p10": round(float(np.quantile(cb, .1)), 2),
            "B_corr_sales_p50": round(float(np.quantile(cb, .5)), 2),
            "B_corr_sales_p90": round(float(np.quantile(cb, .9)), 2),
            "A_corr_sales_p10": round(float(np.quantile(ca, .1)), 2),
            "A_corr_sales_p90": round(float(np.quantile(ca, .9)), 2),
            "B_below_0_2_pct": round(100 * float((cb < 0.2).mean()), 1),
            "random_above_B_pct": round(100 * float((cr > cb).mean()), 1)}, cb


def main():
    rng = np.random.default_rng(SEED)

    # 0) 1社分（400人）を data に置く
    d0 = make(rng, 400)
    sales = 1200 + 300 * d0["y"]
    df = pd.DataFrame({"staff_id": np.arange(1, 401), "skill": d0["skill"], "territory": d0["territory"],
                       "other_work": d0["other"], "true_contribution": d0["true"], "sales_man_yen": sales,
                       "rating_sales_based": 50 + 10 * z(d0["A"]), "rating_half": 50 + 10 * z(d0["C"]),
                       "rating_work_based": 50 + 10 * z(d0["B"])})
    df.to_csv(DATA / "staff_400.csv", index=False, float_format="%.3f")
    one = summarize(d0)

    # 1) 基本の置き方（40万人で、ほぼ式の値）
    d = make(rng, 400000)
    base = summarize(d)
    pd.DataFrame(base).to_csv(RES / "base_raters.csv", index=False)
    theory = {"corr_true_sales": round(np.sqrt((1 - BASE_T - LUCK) * BASE_W), 3),
              "A_corr_sales": round(np.sqrt(0.8), 3),
              "A_corr_true": round(np.sqrt(0.8) * np.sqrt((1 - BASE_T - LUCK) * BASE_W), 3),
              "B_corr_true": round(np.sqrt(0.6), 3),
              "B_corr_sales": round(np.sqrt(0.6) * np.sqrt((1 - BASE_T - LUCK) * BASE_W), 3)}

    # 2) 確かめ：担当地域の分 t と、本当の貢献のうち売る力の分 w を変える（9通り）
    grid = []
    for t in [0.2, 0.4, 0.6]:
        for w in [0.3, 0.5, 0.8]:
            g = summarize(make(np.random.default_rng(SEED * 100 + int(t * 10) * 10 + int(w * 10)), 200000, t, w))
            row = {"territory_share": t, "skill_share_in_true": w}
            for r, key in zip(g, ["A", "C", "B", "P"]):
                row[f"{key}_corr_sales"] = r["corr_sales"]; row[f"{key}_corr_true"] = r["corr_true"]
                row[f"{key}_top20_pct"] = r["top20_overlap_pct"]
            grid.append(row)
    grid_df = pd.DataFrame(grid)
    grid_df.to_csv(RES / "grid_territory_skill.csv", index=False)
    gsum = {"A_corr_sales_range": [float(grid_df.A_corr_sales.min()), float(grid_df.A_corr_sales.max())],
            "B_corr_sales_range": [float(grid_df.B_corr_sales.min()), float(grid_df.B_corr_sales.max())],
            "P_corr_sales_range": [float(grid_df.P_corr_sales.min()), float(grid_df.P_corr_sales.max())],
            "A_corr_true_range": [float(grid_df.A_corr_true.min()), float(grid_df.A_corr_true.max())],
            "B_corr_true_range": [float(grid_df.B_corr_true.min()), float(grid_df.B_corr_true.max())],
            "A_top20_range": [float(grid_df.A_top20_pct.min()), float(grid_df.A_top20_pct.max())],
            "B_top20_range": [float(grid_df.B_top20_pct.min()), float(grid_df.B_top20_pct.max())],
            "n_A_sales_corr_above_B": int((grid_df.A_corr_sales > grid_df.B_corr_sales).sum()),
            "n_B_true_corr_above_A": int((grid_df.B_corr_true > grid_df.A_corr_true).sum()),
            "n_settings": int(len(grid_df))}

    # 3) 確かめ：1部署の人数（部署ごとに相関を数える、各2万部署）
    dept, dist = [], {}
    for s in [10, 15, 30, 60]:
        r, cb = dept_corr(np.random.default_rng(SEED * 7 + s), s)
        dept.append(r); dist[s] = cb
    pd.DataFrame(dept).to_csv(RES / "dept_size_corr.csv", index=False)

    out = {"base_400k": base, "theory_base": theory, "one_company_400": one, "grid_9": gsum,
           "dept_size": dept}
    json.dump(out, open(RES / "a942_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1社400人の評価と売上（2人の評価者）
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True)
    for ax, key, col, o in [(axes[0], "rating_sales_based", ORANGE, one[0]), (axes[1], "rating_work_based", BLUE, one[2])]:
        ax.scatter(df[key], df.sales_man_yen, s=8, color=col, alpha=.5, lw=0)
        ax.set_xlabel("評価の点（平均50）")
        ax.set_title(f"{o['rater']}\n売上との相関{o['corr_sales']:.2f}・本当の貢献との相関{o['corr_true']:.2f}", fontsize=11)
    axes[0].set_ylabel("年の売上（万円）")
    fig.suptitle("売上との相関が高い評価が、本当の貢献をよく当てているとは限らない（1社400人）", fontsize=12, y=1.04)
    save(fig, "a942_scatter.png", SRC, y=-0.03)

    # 図2：4つの付け方の、売上との相関と本当の貢献との相関
    b = pd.DataFrame(base)
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    yy = np.arange(len(b))[::-1]
    ax.barh(yy + 0.2, b.corr_sales, height=0.38, color=ORANGE, label="売上との相関")
    ax.barh(yy - 0.2, b.corr_true, height=0.38, color=BLUE, label="本当の貢献との相関")
    for i, (cs, ct) in enumerate(zip(b.corr_sales, b.corr_true)):
        ax.text(cs + 0.01, yy[i] + 0.2, f"{cs:.2f}", va="center", fontsize=9)
        ax.text(ct + 0.01, yy[i] - 0.2, f"{ct:.2f}", va="center", fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels(b.rater); ax.set_xlim(0, 1.45)
    ax.set_xlabel("相関係数（40万人で数えた値）")
    ax.legend(frameon=False, fontsize=9, loc="center right")
    ax.set_title(f"理想の評価でも、売上との相関は{b.corr_sales[3]:.2f}にとどまる")
    save(fig, "a942_raters.png", SRC)

    # 図3：1部署15人で数えた、仕事ぶりを見る評価と売上の相関
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    r15 = [r for r in dept if r["size"] == 15][0]
    ax.hist(dist[15], bins=np.linspace(-0.8, 1, 55), color=BLUE, alpha=.75)
    ax.axvline(b.corr_sales[2], color=INK, lw=1, ls="--")
    ax.text(b.corr_sales[2] - 0.02, ax.get_ylim()[1] * 0.92, f"大人数での値 {b.corr_sales[2]:.2f}", fontsize=9, ha="right")
    ax.set_xlabel("1部署（15人）の中での、評価の点と売上の相関"); ax.set_yticks([])
    ax.set_ylabel("部署の数（2万部署）")
    ax.set_title(f"仕事ぶりを見て付けても、部署ごとの相関は{r15['B_corr_sales_p10']:.2f}〜{r15['B_corr_sales_p90']:.2f}"
                 "（10〜90%の範囲）に散らばる", fontsize=12)
    save(fig, "a942_dept15.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
