"""1260 受注率を、その期に始まった商談で数えるか、その期に決まった商談で数えるかで、どれだけ違うのか？（架空のデータ）

架空の会社の法人向けの商談。商談ごとに、取れるか取れないか（本当の受注の確率で乱数で決める）と、
始まってから決まるまでの日数（取れる商談と取れない商談で平均を変える）を作成者が置く。
期（90日）ごとに、
  A 始まった商談：期末までに取れた数 ÷ 期に始まった数
  B 始まった商談：期末までに取れた数 ÷ 期末までに決まった数
  C 決まった商談：期に取れた数 ÷ 期に決まった数
  本当：期に始まった商談が、最後に取れた割合
を数え、本当の受注の確率が変わったとき・商談の入り方が変わったときの動きも数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1260
SRC = "架空の会社の商談（作成者が乱数で作成、seed 1260）"
Q = 90                 # 1期の日数
NQ = 12                # 数える期の数（1〜12期）
WARM = 4               # 前から続いている分として、1期より前に4期分の商談を置く
LAM = 2.0              # 1日に始まる商談の平均の件数
SIG = 0.6              # 決まるまでの日数の、対数のばらつき
CHANGE_Q = 5           # 6期目（0から数えて5）に始まる商談から置き方を変える
REPS = 200
GRID_REPS = 60
WAITS = (90, 180, 365)   # 期末から待つ日数


def make_deals(rng, Mw=45.0, Ml=75.0, p0=0.25, p1=None, lam1=None):
    """商談を作る。戻り値：始まった日・決まった日・取れたか"""
    cd = CHANGE_Q * Q
    n0 = rng.poisson(LAM * (cd + WARM * Q))
    s0 = rng.uniform(-WARM * Q, cd, n0)
    lam_after = LAM if lam1 is None else lam1
    n1 = rng.poisson(lam_after * (NQ * Q - cd))
    s1 = rng.uniform(cd, NQ * Q, n1)
    start = np.concatenate([s0, s1])
    p = np.where(start < cd, p0, p0 if p1 is None else p1)
    won = rng.random(len(start)) < p
    mw, ml = np.log(Mw) - SIG ** 2 / 2, np.log(Ml) - SIG ** 2 / 2
    dur = np.where(won, rng.lognormal(mw, SIG, len(start)), rng.lognormal(ml, SIG, len(start)))
    order = np.argsort(start, kind="stable")
    return start[order], (start + dur)[order], won[order]


def measures(start, dec, won):
    rows = []
    for q in range(NQ):
        a, e = q * Q, (q + 1) * Q
        st = (start >= a) & (start < e)
        n = st.sum()
        dby = st & (dec < e)
        wby = dby & won
        dq = (dec >= a) & (dec < e)
        rows.append(dict(
            q=q + 1,
            A=wby.sum() / n * 100,
            B=wby.sum() / max(dby.sum(), 1) * 100,
            C=(dq & won).sum() / max(dq.sum(), 1) * 100,
            true=(st & won).sum() / n * 100,
            started=int(n), decided_in_q=int(dq.sum()), decided_by_end=int(dby.sum()),
            C_from_earlier=((dq & (start < a)).sum() / max(dq.sum(), 1) * 100),
        ))
        for k in WAITS:
            dk = st & (dec < e + k)
            rows[-1][f"A_wait{k}"] = (dk & won).sum() / n * 100
            rows[-1][f"B_wait{k}"] = (dk & won).sum() / max(dk.sum(), 1) * 100
            rows[-1][f"decided_wait{k}"] = dk.sum() / n * 100
    return pd.DataFrame(rows)


def run(rng, reps, **kw):
    out = [measures(*make_deals(rng, **kw)).assign(rep=r) for r in range(reps)]
    return pd.concat(out, ignore_index=True)


def summarize(df):
    g = df.groupby("q")
    s = g[["A", "B", "C", "true", "started", "decided_in_q", "decided_by_end", "C_from_earlier"]].mean()
    for c in ["A", "B", "C"]:
        s[c + "_p10"] = g[c].quantile(0.1)
        s[c + "_p90"] = g[c].quantile(0.9)
    return s.reset_index().round(2)


def lognorm_cdf(x, M):
    from math import erf, log, sqrt
    mu = log(M) - SIG ** 2 / 2
    x = np.maximum(x, 1e-9)
    return 0.5 * (1 + np.vectorize(erf)((np.log(x) - mu) / (SIG * sqrt(2))))


def formula_steady(Mw, Ml, p=0.25):
    """始まった日が期の中で一様なときの A・B の式の値（期末までの残りの日数で平均）"""
    t = (np.arange(20000) + 0.5) / 20000 * Q
    fw, fl = lognorm_cdf(t, Mw).mean(), lognorm_cdf(t, Ml).mean()
    return p * fw * 100, p * fw / (p * fw + (1 - p) * fl) * 100


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 置き方を変えない（本当の受注の確率25%、取れる商談は平均45日、取れない商談は平均75日で決まる）
    steady = run(rng, REPS)
    s_steady = summarize(steady)
    s_steady.to_csv(RES / "steady_by_quarter.csv", index=False)
    st_all = steady[steady.q >= 2]
    steady_mean = {c: round(float(st_all[c].mean()), 2) for c in ["A", "B", "C", "true"]}
    steady_rng = {c: [round(float(st_all[c].quantile(0.1)), 2), round(float(st_all[c].quantile(0.9)), 2)] for c in ["A", "B", "C"]}
    fA, fB = formula_steady(45, 75)
    share_earlier = round(float(st_all["C_from_earlier"].mean()), 2)
    wait_rows = [dict(wait_days=0, A=steady_mean["A"], B=steady_mean["B"],
                      decided_share=round(float((st_all.decided_by_end / st_all.started).mean() * 100), 2))]
    for k in WAITS:
        wait_rows.append(dict(wait_days=k, A=round(float(st_all[f"A_wait{k}"].mean()), 2),
                              B=round(float(st_all[f"B_wait{k}"].mean()), 2),
                              decided_share=round(float(st_all[f"decided_wait{k}"].mean()), 2)))
    pd.DataFrame(wait_rows).to_csv(RES / "steady_wait_days.csv", index=False)

    # 2) 6期目に始まる商談から、本当の受注の確率が25%→35%に上がる
    pch = run(rng, REPS, p1=0.35)
    s_pch = summarize(pch)
    s_pch.to_csv(RES / "p_change_by_quarter.csv", index=False)

    # 3) 6期目から、1日に始まる商談が2件→4件に増える（受注の確率は25%のまま）
    lch = run(rng, REPS, lam1=4.0)
    s_lch = summarize(lch)
    s_lch.to_csv(RES / "inflow_change_by_quarter.csv", index=False)

    # 4) 確かめ：決まるまでの日数の平均（取れる商談 × 取れない商談）9通り
    grid = []
    for Mw in [30, 45, 90]:
        for Ml in [30, 75, 150]:
            a = run(rng, GRID_REPS, Mw=Mw, Ml=Ml)
            a = a[a.q >= 2]
            b = summarize(run(rng, GRID_REPS, Mw=Mw, Ml=Ml, p1=0.35)).set_index("q")
            c = summarize(run(rng, GRID_REPS, Mw=Mw, Ml=Ml, lam1=4.0)).set_index("q")
            fa, fb = formula_steady(Mw, Ml)
            grid.append(dict(win_days=Mw, loss_days=Ml,
                             steady_A=round(a.A.mean(), 2), steady_B=round(a.B.mean(), 2), steady_C=round(a.C.mean(), 2),
                             formula_A=round(fa, 2), formula_B=round(fb, 2),
                             pchange_C_q6=b.loc[6, "C"], pchange_C_q7=b.loc[7, "C"], pchange_B_q6=b.loc[6, "B"],
                             pchange_true_q6=b.loc[6, "true"],
                             inflow_C_q6=c.loc[6, "C"], inflow_C_q8=c.loc[8, "C"], inflow_B_q6=c.loc[6, "B"]))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_days.csv", index=False)

    # データ：置き方を変えない1回分の商談
    r1 = np.random.default_rng(SEED + 1)
    s, d, w = make_deals(r1)
    pd.DataFrame({"deal_id": np.arange(1, len(s) + 1), "start_day": np.round(s, 1), "decided_day": np.round(d, 1),
                  "won": w.astype(int)}).to_csv(DATA / "deals_one_rep.csv", index=False)

    def row(sdf, q):
        r = sdf.set_index("q").loc[q]
        return {k: float(r[k]) for k in ["A", "B", "C", "true", "C_from_earlier"]}

    out = {
        "settings": {"days_per_quarter": Q, "quarters": NQ, "warmup_quarters": WARM, "deals_per_day": LAM,
                     "win_prob": 0.25, "win_days_mean": 45, "loss_days_mean": 75, "log_sd_days": SIG, "reps": REPS,
                     "change_from_quarter": CHANGE_Q + 1, "win_prob_after": 0.35, "deals_per_day_after": 4.0,
                     "seed": SEED},
        "steady_q2_12": {"mean": steady_mean, "p10_p90": steady_rng, "formula_A": round(fA, 2), "formula_B": round(fB, 2),
                         "C_share_started_earlier": share_earlier,
                         "decided_by_end_share_of_started": round(float((st_all.decided_by_end / st_all.started).mean() * 100), 2),
                         "undecided_at_end_share": round(100 - float((st_all.decided_by_end / st_all.started).mean() * 100), 2)},
        "steady_wait_days": wait_rows,
        "p_change": {f"q{q}": row(s_pch, q) for q in [5, 6, 7, 8, 9, 10]},
        "inflow_change": {f"q{q}": row(s_lch, q) for q in [5, 6, 7, 8, 9, 10]},
        "grid_max_gap_to_formula": {"A": round(float((grid.steady_A - grid.formula_A).abs().max()), 2),
                                     "B": round(float((grid.steady_B - grid.formula_B).abs().max()), 2)},
        "grid_range": {k: [float(grid[k].min()), float(grid[k].max())] for k in grid.columns if k not in ("win_days", "loss_days")},
    }

    # 図1：置き方を変えないときの4つの数え方（2〜12期の平均）
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels = ["A 始まった商談\n期末までに取れた数\n÷始まった数", "B 始まった商談\n期末までに取れた数\n÷期末までに決まった数",
              "C その期に\n決まった商談\n取れた数÷決まった数", "本当\n始まった商談が\n最後に取れた割合"]
    vals = [steady_mean["A"], steady_mean["B"], steady_mean["C"], steady_mean["true"]]
    bars = ax.bar(range(4), vals, color=[ORANGE, ORANGE, BLUE, GRAY], width=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.2f}%", ha="center", fontsize=10)
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylim(0, max(vals) * 1.25); ax.set_ylabel("受注率（%）")
    ax.set_title("同じ商談でも、数え方で受注率が違う（置き方を変えない、2〜12期の平均）")
    save(fig, "a1260_steady.png", SRC + "。本当の受注の確率25%、取れる商談は平均45日・取れない商談は平均75日で決まる。200回", y=-0.09)

    # 図2・3：置き方を変えたときの期ごとの動き
    def lines(sdf, title, name, note):
        fig, ax = plt.subplots(figsize=(7.2, 4))
        x = sdf.q
        ax.plot(x, sdf["true"], color=GRAY, lw=2.5, label="本当（始まった商談が最後に取れた割合）")
        ax.plot(x, sdf["C"], color=BLUE, marker="o", label="C その期に決まった商談")
        ax.fill_between(x, sdf["C_p10"], sdf["C_p90"], color=LIGHT, alpha=0.5, lw=0)
        ax.plot(x, sdf["B"], color=ORANGE, marker="s", label="B 始まった商談（期末までに決まった分）")
        ax.plot(x, sdf["A"], color=ORANGE, marker="^", ls="--", label="A 始まった商談（始まった数で割る）")
        ax.axvline(CHANGE_Q + 0.5, color=INK, lw=0.8, ls=":")
        ax.set_xticks(range(1, NQ + 1)); ax.set_xlabel("期"); ax.set_ylabel("受注率（%）")
        ax.set_ylim(0, 50); ax.set_title(title)
        ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
        save(fig, name, SRC + "。" + note + "。200回の平均（Cの帯は10〜90%の範囲）", y=-0.13)

    lines(s_pch, "6期目から本当の受注の確率が25%→35%に上がったとき", "a1260_p_change.png",
          "6期目に始まった商談から受注の確率を35%に変えた")
    lines(s_lch, "6期目から始まる商談が倍に増えたとき（受注の確率は25%のまま）", "a1260_inflow_change.png",
          "6期目から1日に始まる商談を2件→4件に変えた")

    print("run_sec", round(time.time() - t0, 1))
    json.dump(out, open(RES / "a1260_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(grid.to_string())


if __name__ == "__main__":
    main()
