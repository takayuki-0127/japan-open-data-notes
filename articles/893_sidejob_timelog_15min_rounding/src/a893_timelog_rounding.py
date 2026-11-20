"""893 作業時間の記録を15分単位で切ると、何%消えるのか？（架空のデータ）

架空の副業の人1人の作業の記録。1回ごとの作業時間を、短いやり取り（連絡・確認）と
まとまった作業の2種類で置き、記録の丸め方ごとに、本当の時間との差を数える。数え方だけを扱う。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 893
SRC = "架空の副業の人の作業の記録（作成者が乱数で作成、seed 893）"
rng = np.random.default_rng(SEED)

BASE = {"days": 20, "short_per_day": 6.0, "short_median": 5.0, "short_sd": 0.6,
        "work_per_day": 3.0, "work_median": 45.0, "work_sd": 0.6, "unit": 15}
N_MONTH = 1000
RULES = ["1回ごとに切り捨て", "1回ごとに四捨五入", "1回ごとに切り上げ", "1日の合計を切り捨て"]


def make_month(rng, days=20, short_per_day=6.0, short_median=5.0, short_sd=0.6, work_per_day=3.0,
               work_median=45.0, work_sd=0.6, **_):
    rows = []
    for d in range(days):
        for kind, lam, med, sd in [("やり取り", short_per_day, short_median, short_sd),
                                   ("作業", work_per_day, work_median, work_sd)]:
            k = rng.poisson(lam)
            if k:
                mins = med * np.exp(rng.normal(0, sd, k))
                rows += [(d + 1, kind, float(m)) for m in mins]
    return pd.DataFrame(rows, columns=["day", "kind", "minutes"])


def record(df, unit=15):
    """丸め方ごとの記録の合計（分）"""
    m = df.minutes.values
    out = {"本当の時間": m.sum(),
           "1回ごとに切り捨て": (np.floor(m / unit) * unit).sum(),
           "1回ごとに四捨五入": (np.floor(m / unit + 0.5) * unit).sum(),
           "1回ごとに切り上げ": (np.ceil(m / unit) * unit).sum()}
    daily = df.groupby("day").minutes.sum().values
    out["1日の合計を切り捨て"] = (np.floor(daily / unit) * unit).sum()
    return out


def change(rec):
    t = rec["本当の時間"]
    return {r: rec[r] / t - 1 for r in RULES}


def main():
    # 1) 例の1か月（data に置く）
    ex = make_month(rng, **BASE)
    ex.insert(0, "session_id", np.arange(1, len(ex) + 1))
    ex["minutes"] = ex.minutes.round(2)
    ex.to_csv(DATA / "sessions_example_month.csv", index=False)
    ex = pd.read_csv(DATA / "sessions_example_month.csv")
    rec = record(ex, BASE["unit"])
    ch = change(rec)
    by_kind = {}
    for kind, g in ex.groupby("kind", sort=False):
        r = record(g.assign(day=g.day), BASE["unit"])
        by_kind[kind] = {"n": int(len(g)), "true_hours": round(r["本当の時間"] / 60, 2),
                         "floor_hours": round(r["1回ごとに切り捨て"] / 60, 2),
                         "floor_change": round(r["1回ごとに切り捨て"] / r["本当の時間"] - 1, 4),
                         "round_change": round(r["1回ごとに四捨五入"] / r["本当の時間"] - 1, 4),
                         "ceil_change": round(r["1回ごとに切り上げ"] / r["本当の時間"] - 1, 4),
                         "share_under_unit": round(float((g.minutes < BASE["unit"]).mean()), 4)}
    n = len(ex)
    example = {"n_sessions": int(n), "true_hours": round(rec["本当の時間"] / 60, 2),
               "recorded_hours": {r: round(rec[r] / 60, 2) for r in RULES},
               "change": {r: round(v, 4) for r, v in ch.items()},
               "floor_lost_hours": round((rec["本当の時間"] - rec["1回ごとに切り捨て"]) / 60, 2),
               "floor_lost_from_short_share": round(
                   (by_kind["やり取り"]["true_hours"] - by_kind["やり取り"]["floor_hours"]) /
                   ((rec["本当の時間"] - rec["1回ごとに切り捨て"]) / 60), 4),
               "per_hour_inflation_floor": round(rec["本当の時間"] / rec["1回ごとに切り捨て"] - 1, 4),
               "formula_floor_guess": round(n * BASE["unit"] / 2 / rec["本当の時間"], 4),
               "by_kind": by_kind}

    # 2) 1,000か月で、丸め方ごとの差の幅
    sims = []
    for i in range(N_MONTH):
        g = make_month(np.random.default_rng(SEED * 1000 + i), **BASE)
        c = change(record(g, BASE["unit"]))
        sims.append({"month": i + 1, **c})
    sims = pd.DataFrame(sims)
    rule_sum = pd.DataFrame({"mean": sims[RULES].mean(), "p10": sims[RULES].quantile(.1),
                             "p90": sims[RULES].quantile(.9)}).round(4)
    rule_sum.index.name = "rule"
    rule_sum.to_csv(RES / "rules_1000months.csv")

    # 3) 置き方を変えると（各300か月の平均）：1回ごとに切り捨て・四捨五入
    rob = []
    grid = ([("やり取りの回数（1日）", "short_per_day", v) for v in [0, 3, 6, 12]] +
            [("記録の単位（分）", "unit", v) for v in [5, 10, 15, 30]] +
            [("やり取りの長さ（中央値・分）", "short_median", v) for v in [3, 5, 10]] +
            [("作業の長さ（中央値・分）", "work_median", v) for v in [20, 45, 90]] +
            [("作業の回数（1日）", "work_per_day", v) for v in [1.5, 3, 6]])
    for k, (lab, key, val) in enumerate(grid):
        p = dict(BASE); p[key] = val
        cs, guesses = [], []
        for i in range(300):
            g = make_month(np.random.default_rng(SEED * 100000 + k * 1000 + i), **p)
            rr = record(g, p["unit"])
            cs.append(change(rr))
            guesses.append(len(g) * p["unit"] / 2 / rr["本当の時間"])
        cs = pd.DataFrame(cs)
        rob.append({"factor": lab, "key": key, "value": val, "is_base": val == BASE[key],
                    **{r: round(float(cs[r].mean()), 4) for r in RULES},
                    "floor_p10": round(float(cs["1回ごとに切り捨て"].quantile(.1)), 4),
                    "floor_p90": round(float(cs["1回ごとに切り捨て"].quantile(.9)), 4),
                    "formula_floor_guess": round(-float(np.mean(guesses)), 4)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"settings_base": BASE, "example_month": example,
           "rules_1000months": rule_sum.reset_index().to_dict("records"),
           "robustness_floor_range": {"min": float(rob["1回ごとに切り捨て"].min()),
                                      "max": float(rob["1回ごとに切り捨て"].max())},
           "robustness_round_range": {"min": float(rob["1回ごとに四捨五入"].min()),
                                      "max": float(rob["1回ごとに四捨五入"].max())}}
    json.dump(out, open(RES / "a893_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回ごとの時間と15分の区切り
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.arange(0, 181, 2.5)
    for kind, c in [("やり取り", ORANGE), ("作業", BLUE)]:
        ax.hist(np.minimum(ex[ex.kind == kind].minutes, 179.9), bins=bins, color=c, alpha=.6,
                label=f"{kind}（{by_kind[kind]['n']}回、15分未満は{by_kind[kind]['share_under_unit'] * 100:.0f}%）")
    for x in range(15, 181, 15):
        ax.axvline(x, color=GRAY, lw=.6, ls=":")
    ax.set_xlabel("1回の時間（分）。点線は15分の区切り。180分以上は右端に入れた")
    ax.set_ylabel("回数（1か月）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"1回ごとに15分で切り捨てると、やり取りの{-by_kind['やり取り']['floor_change'] * 100:.0f}%が消えた（例の1か月）",
                 fontsize=11.5)
    save(fig, "a893_sessions.png", SRC)

    # 図2：丸め方ごとの差（1,000か月）
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    y = np.arange(len(RULES))[::-1]
    mv = rule_sum["mean"].values * 100
    lo, hi = rule_sum["p10"].values * 100, rule_sum["p90"].values * 100
    cols = [ORANGE if v < 0 else BLUE for v in mv]
    ax.barh(y, mv, color=cols, alpha=.8)
    ax.errorbar(mv, y, xerr=[mv - lo, hi - mv], fmt="none", ecolor=INK, lw=1, capsize=3)
    for yy, v, h, l in zip(y, mv, hi, lo):
        ax.text((h + 2) if v >= 0 else (l - 2), yy, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right",
                fontsize=9)
    ax.set_yticks(y, RULES)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_xlim(-55, 85)
    ax.set_xlabel("記録の合計 ÷ 本当の合計 − 1（%）\n棒は1,000か月の平均、線は10〜90%の範囲", fontsize=10)
    ax.set_title("同じ1か月でも、15分の丸め方で記録の合計が大きく変わる", fontsize=11.5)
    save(fig, "a893_rules.png", SRC, y=-0.08)

    # 図3：やり取りの回数と記録の単位（1回ごとに切り捨て）
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8), sharey=True)
    for a_, key, xl in [(axes[0], "short_per_day", "やり取りの回数（1日あたり）"),
                        (axes[1], "unit", "記録の単位（分）")]:
        g = rob[rob.key == key]
        a_.plot(g.value, g["1回ごとに切り捨て"] * 100, marker="o", color=ORANGE, label="1回ごとに切り捨て")
        a_.plot(g.value, g["1回ごとに四捨五入"] * 100, marker="o", color=BLUE, label="1回ごとに四捨五入")
        a_.plot(g.value, g["1日の合計を切り捨て"] * 100, marker="o", color=GRAY, label="1日の合計を切り捨て")
        for xv, yv in zip(g.value, g["1回ごとに切り捨て"] * 100):
            a_.text(xv + (0.35 if key == "short_per_day" else 0.8), yv - 4.5, f"{yv:.0f}%", ha="center", fontsize=8, color=ORANGE)
        a_.axhline(0, color=INK, lw=.8)
        a_.set_xticks(g.value.tolist())
        a_.set_xlabel(xl)
    axes[0].set_ylabel("記録の合計のずれ（%、各300か月の平均）")
    axes[0].set_ylim(-55, 20)
    axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    axes[0].set_title("やり取りが多いほど、切り捨てで消える", fontsize=11)
    axes[1].set_title("単位を細かくすると、消える分は小さくなる", fontsize=11)
    fig.tight_layout()
    save(fig, "a893_settings.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(rob.to_string())


if __name__ == "__main__":
    main()
