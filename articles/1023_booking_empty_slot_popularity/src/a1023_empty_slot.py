"""1023 予約のない枠は、本当に人気がないのか？（架空のデータ）

架空の陶芸教室を2,000教室作る。どの教室も1週間に28枠（7曜日×4つの時間帯、定員6人）。
枠ごとの本当の人気（受付中の1日あたりの申し込みの多さ）を作成者が置き、
ふだんの枠は28日前から、あとから足した枠（追加の枠）は10日前から受付を始める。
毎週月曜の朝に、その週の28枠の予約の数を見る。予約0件の枠が、本当に人気の低い枠かを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1023
SRC = "架空の陶芸教室の予約（作成者が乱数で作成、seed 1023）"
CAP = 6
DAY_F = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.6, 1.6])     # 月〜日
TIME_F = np.array([0.8, 1.0, 1.1, 1.3])                    # 朝・昼・午後・夜
OPEN_REG, OPEN_LATE = 28, 10                               # 受付を始める日（何日前）
BASE = dict(base=0.2, late_share=0.25, sigma=0.6)
WEEKS = 8


def make(rng, n_class, base, late_share, sigma, weeks=WEEKS):
    n = n_class * 28
    wd = np.tile(np.repeat(np.arange(7), 4), n_class)
    tm = np.tile(np.tile(np.arange(4), 7), n_class)
    f = DAY_F[wd] * TIME_F[tm]
    f = f / f.mean()
    lam = base * f * np.exp(sigma * rng.standard_normal(n) - sigma ** 2 / 2)
    late = rng.random(n) < late_share
    u = wd + 1                                             # 月曜の朝に見る：月=1日後 … 日=7日後
    open_days = np.where(late, OPEN_LATE - u, OPEN_REG - u)
    req = rng.poisson(lam[:, None] * open_days[:, None], size=(n, weeks))
    cnt = np.minimum(req, CAP)
    return dict(cls=np.repeat(np.arange(n_class), 28), wd=wd, tm=tm, lam=lam, late=late,
                open_days=open_days, req=req, cnt=cnt)


def tertile(lam):
    q1, q2 = np.quantile(lam, [1 / 3, 2 / 3])
    return np.where(lam <= q1, 0, np.where(lam <= q2, 1, 2))


def flag_precision(rng, s, k, ter):
    """k週分で下位3分の1の枠を選ぶ。件数の合計で選ぶか、受付の1日あたりで選ぶか（同点はでたらめ）"""
    n = len(s["lam"])
    m = n // 3
    tot = s["cnt"][:, :k].sum(1)
    per = tot / (s["open_days"] * k)
    tie = rng.random(n)
    out = {}
    for name, v in [("count", tot), ("per_day", per)]:
        idx = np.lexsort((tie, v))[:m]
        out[name] = round(float((ter[idx] == 0).mean()) * 100, 2)
        out[name + "_late_share"] = round(float(s["late"][idx].mean()) * 100, 2)
    return out


def summarize(rng, s, ks=(1, 2, 4, 8)):
    ter = tertile(s["lam"])
    z1 = s["cnt"][:, 0] == 0
    p0 = np.exp(-s["lam"] * s["open_days"])
    res = {
        "slots": int(len(z1)),
        "zero_share_week1": round(float(z1.mean()) * 100, 2),
        "zero_share_formula": round(float(p0.mean()) * 100, 2),
        "zero_share_regular": round(float(z1[~s["late"]].mean()) * 100, 2),
        "zero_share_late": round(float(z1[s["late"]].mean()) * 100, 2),
        "late_share_all": round(float(s["late"].mean()) * 100, 2),
        "full_share_week1": round(float((s["cnt"][:, 0] == CAP).mean()) * 100, 2),
        "open_days_regular_min": int(s["open_days"][~s["late"]].min()), "open_days_regular_max": int(s["open_days"][~s["late"]].max()),
        "open_days_late_min": int(s["open_days"][s["late"]].min()) if s["late"].any() else None,
        "open_days_late_max": int(s["open_days"][s["late"]].max()) if s["late"].any() else None,
        "random_precision": round(100 / 3, 2),
    }
    by_k = []
    for k in ks:
        z = (s["cnt"][:, :k] == 0).all(1)
        row = {"weeks": k, "zero_slots": int(z.sum()),
               "zero_share": round(float(z.mean()) * 100, 2),
               "late_among_zero": round(float(s["late"][z].mean()) * 100, 2),
               "bottom_among_zero": round(float((ter[z] == 0).mean()) * 100, 2),
               "middle_among_zero": round(float((ter[z] == 1).mean()) * 100, 2),
               "top_among_zero": round(float((ter[z] == 2).mean()) * 100, 2),
               "bottom_among_zero_regular": round(float((ter[z & ~s["late"]] == 0).mean()) * 100, 2) if (z & ~s["late"]).any() else None,
               "bottom_among_zero_late": round(float((ter[z & s["late"]] == 0).mean()) * 100, 2) if (z & s["late"]).any() else None}
        fp = flag_precision(rng, s, k, ter)
        row.update({"flag_precision_count": fp["count"], "flag_precision_per_day": fp["per_day"],
                    "flag_late_share_count": fp["count_late_share"], "flag_late_share_per_day": fp["per_day_late_share"]})
        by_k.append(row)
    # 1週目の0件の枠の内訳（受付の種類×本当の人気の3分の1）
    comp = {}
    for lt, ln in [(False, "regular"), (True, "late")]:
        for t, tn in enumerate(["bottom", "middle", "top"]):
            comp[f"{ln}_{tn}"] = round(float((z1 & (s["late"] == lt) & (ter == t)).sum() / z1.sum()) * 100, 2)
    res["composition_zero_week1"] = comp
    return res, pd.DataFrame(by_k)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    s = make(rng, 2000, **BASE)
    res, by_k = summarize(rng, s)
    by_k.to_csv(RES / "by_weeks.csv", index=False)
    ter = tertile(s["lam"])
    d = pd.DataFrame({"class_id": s["cls"], "weekday": s["wd"] + 1, "time_slot": s["tm"] + 1,
                      "late_open": s["late"].astype(int), "true_rate": s["lam"], "true_tertile": ter + 1,
                      "open_days": s["open_days"]})
    for w in range(WEEKS):
        d[f"booked_w{w + 1}"] = s["cnt"][:, w]
    d[d.class_id < 200].to_csv(DATA / "slots.csv", index=False, float_format="%.4f")

    # 確かめ：27通り
    rows = []
    for base in (0.1, 0.2, 0.4):
        for ls in (0.0, 0.25, 0.5):
            for sg in (0.3, 0.6, 0.9):
                ss = make(rng, 500, base, ls, sg)
                r, bk = summarize(rng, ss, ks=(1, 4))
                b1 = bk.iloc[0]; b4 = bk.iloc[1]
                rows.append({"base": base, "late_share": ls, "sigma": sg,
                             "zero_share_week1": r["zero_share_week1"],
                             "zero_share_formula": r["zero_share_formula"],
                             "bottom_among_zero_w1": b1.bottom_among_zero,
                             "top_among_zero_w1": b1.top_among_zero,
                             "late_among_zero_w1": b1.late_among_zero,
                             "bottom_among_zero_w4": b4.bottom_among_zero,
                             "flag_precision_count_w4": b4.flag_precision_count,
                             "flag_precision_per_day_w4": b4.flag_precision_per_day})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    g = grid
    gl = g[g.late_share > 0]
    res["grid"] = {
        "bottom_among_zero_w1_min": float(g.bottom_among_zero_w1.min()), "bottom_among_zero_w1_max": float(g.bottom_among_zero_w1.max()),
        "bottom_among_zero_w1_min_late0": float(g[g.late_share == 0].bottom_among_zero_w1.min()),
        "bottom_among_zero_w1_max_late0": float(g[g.late_share == 0].bottom_among_zero_w1.max()),
        "bottom_among_zero_w1_min_late_pos": float(gl.bottom_among_zero_w1.min()),
        "bottom_among_zero_w1_max_late_pos": float(gl.bottom_among_zero_w1.max()),
        "late_among_zero_w1_min_late_pos": float(gl.late_among_zero_w1.min()),
        "late_among_zero_w1_max_late_pos": float(gl.late_among_zero_w1.max()),
        "precision_count_w4_min": float(g.flag_precision_count_w4.min()), "precision_count_w4_max": float(g.flag_precision_count_w4.max()),
        "precision_per_day_w4_min": float(g.flag_precision_per_day_w4.min()), "precision_per_day_w4_max": float(g.flag_precision_per_day_w4.max()),
        "per_day_beats_count_w4": int((g.flag_precision_per_day_w4 > g.flag_precision_count_w4).sum()),
        "per_day_beats_count_w4_late_pos": int((gl.flag_precision_per_day_w4 > gl.flag_precision_count_w4).sum()),
        "n_late_pos": int(len(gl)),
        "max_abs_zero_share_vs_formula_pt": round(float((g.zero_share_week1 - g.zero_share_formula).abs().max()), 2),
    }
    res["setting"] = dict(BASE, capacity=CAP, open_regular=OPEN_REG, open_late=OPEN_LATE, weeks=WEEKS,
                          day_factor=DAY_F.tolist(), time_factor=TIME_F.tolist(), n_class=2000)
    with open(RES / "a1023_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：1週目の0件の枠の内訳
    comp = res["composition_zero_week1"]
    fig, ax = plt.subplots(figsize=(8.2, 3.2))
    labels = ["人気が下位3分の1", "真ん中", "上位3分の1"]
    left = 0
    cols = [BLUE, LIGHT, GRAY]
    for lt, ln, y in [("regular", "ふだんの枠\n（28日前から受付）", 1), ("late", "追加の枠\n（10日前から受付）", 0)]:
        left = 0
        for i, tn in enumerate(["bottom", "middle", "top"]):
            v = comp[f"{lt}_{tn}"]
            ax.barh(y, v, left=left, color=cols[i], edgecolor="white", label=labels[i] if lt == "regular" else None)
            if v >= 6:
                ax.text(left + v / 2, y, f"{v:.1f}%", ha="center", va="center", fontsize=9, color=INK)
            left += v
    ax.set_yticks([0, 1]); ax.set_yticklabels(["追加の枠\n（10日前から受付）", "ふだんの枠\n（28日前から受付）"])
    ax.set_xlim(0, 100); ax.set_xlabel("1週目に予約0件だった枠に占める割合（%）")
    ax.set_title("予約0件の枠の内訳（本当の人気の3分の1ずつ）")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    save(fig, "a1023_zero_breakdown.png", SRC, y=-0.07)

    # 図2：週数と、下位3分の1を選んだときの当たり
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(by_k.weeks, by_k.flag_precision_count, "o-", color=ORANGE, label="予約の件数の合計で選ぶ")
    ax.plot(by_k.weeks, by_k.flag_precision_per_day, "o-", color=BLUE, label="受付していた1日あたりで選ぶ")
    ax.plot(by_k.weeks, by_k.bottom_among_zero, "s--", color=GRAY, label="その週数ずっと0件の枠（参考）")
    for _, r in by_k.iterrows():
        ax.text(r.weeks, r.flag_precision_count - 4, f"{r.flag_precision_count:.1f}", ha="center", fontsize=8, color=ORANGE)
        ax.text(r.weeks, r.flag_precision_per_day + 2.5 if r.weeks < 8 else r.flag_precision_per_day - 5, f"{r.flag_precision_per_day:.1f}", ha="center", fontsize=8, color=BLUE)
    ax.axhline(100 / 3, color=GRAY, lw=0.8, ls=":")
    ax.text(1.0, 100 / 3 + 1.5, "でたらめに選んだとき（33.33%）", fontsize=8, color=GRAY, va="bottom")
    ax.set_xticks(by_k.weeks); ax.set_xlabel("見た週の数"); ax.set_ylim(0, 100)
    ax.set_ylabel("本当に人気が下位3分の1だった割合（%）", labelpad=8)
    ax.set_title("「人気のない枠」を選んだときの当たり")
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    save(fig, "a1023_weeks.png", SRC)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    mk = {0.0: "o", 0.25: "s", 0.5: "^"}
    cl = {0.1: LIGHT, 0.2: BLUE, 0.4: INK}
    for _, r in grid.iterrows():
        ax.scatter(r.flag_precision_count_w4, r.flag_precision_per_day_w4, marker=mk[r.late_share], color=cl[r.base], s=40)
    ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8, ls=":")
    for ls, m in mk.items():
        ax.scatter([], [], marker=m, color=GRAY, label=f"追加の枠 {int(ls * 100)}%")
    for b, c in cl.items():
        ax.scatter([], [], marker="o", color=c, label=f"人気の平均 1日{b}人")
    ax.set_xlim(30, 100); ax.set_ylim(30, 100)
    ax.set_xlabel("件数の合計で選んだときの当たり（%、4週）")
    ax.set_ylabel("1日あたりで選んだときの当たり（%、4週）")
    ax.set_title("置き方を変えた27通り（点線より上＝1日あたりのほうが当たる）")
    ax.legend(fontsize=8, frameon=False, loc="lower right", ncol=2)
    save(fig, "a1023_grid.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(by_k.to_string())
    print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
