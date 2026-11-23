"""1124 ダメージの小数を毎回切り捨てて計算すると、小さな強化はどれだけ消えるのか？（架空のデータ）

架空のゲームのダメージを、作成者が置いた次の式で計算する。
  ① 攻撃力×技の倍率1.2×ばらつき（1の前後の一様な乱数）
  ② ×（1＋強化）
  ③ ×（1−敵の守りで減る割合0.25）
小数の扱い：毎回切り捨て（①②③のあとにそれぞれ切り捨て）／最後だけ切り捨て／切り捨てなし。
攻撃力5〜300の整数ごとに、強化なしと強化ありで同じ乱数を使って4,000回ずつ当て、ダメージの平均が何%増えたかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1124
SRC = "架空のゲームのダメージ計算（作成者が置いた式と乱数、seed 1124）"
SKILL, CUT = 1.2, 0.25
ATK = np.arange(5, 301)
BANDS = [("弱い（5〜30）", 5, 30), ("中くらい（31〜100）", 31, 100), ("強い（101〜300）", 101, 300)]
BUFFS = [0.01, 0.03, 0.05, 0.10]
SPREADS = [0.0, 0.05, 0.10]
RULES = [("each", "毎回切り捨て"), ("last", "最後だけ切り捨て"), ("none", "切り捨てなし")]
HITS = 4000
BASE_BUFF, BASE_SPREAD = 0.03, 0.05
EPS = 1e-9


def r(x, d=3):
    return round(float(x), d)


def damage(atk, u, buff, rule):
    """atk:(n,1) u:(1,m) ばらつきの倍率"""
    if rule == "each":
        x1 = np.floor(atk * SKILL * u + EPS)
        x2 = np.floor(x1 * (1 + buff) + EPS)
        return np.floor(x2 * (1 - CUT) + EPS)
    v = atk * SKILL * u * (1 + buff) * (1 - CUT)
    return np.floor(v + EPS) if rule == "last" else v


def realized(rng_u, buff, spread, rule):
    """攻撃力ごとの、ダメージの平均の増え（%）。強化なしと強化ありで同じ乱数"""
    u = rng_u if spread > 0 else np.ones((1, 1))
    a = ATK[:, None].astype(float)
    d0 = damage(a, u, 0.0, rule).mean(1); d1 = damage(a, u, buff, rule).mean(1)
    return 100 * (d1 - d0) / d0, d0, d1


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    U = {s: (1 - s + 2 * s * rng.random((1, HITS))) for s in SPREADS if s > 0}
    res = {"setup": {"skill": SKILL, "cut": CUT, "atk_range": [int(ATK[0]), int(ATK[-1])], "hits_per_atk": HITS,
                     "buffs": BUFFS, "spreads": SPREADS, "base_buff": BASE_BUFF, "base_spread": BASE_SPREAD}}
    rows = []; per_atk = {}
    for spread in SPREADS:
        for buff in BUFFS:
            for key, name in RULES:
                inc, d0, d1 = realized(U.get(spread), buff, spread, key)
                per_atk[(spread, buff, key)] = (inc, d0, d1)
                row = {"spread": spread, "buff_pct": r(100 * buff, 0), "rule": key}
                for (bn, lo, hi), tag in zip(BANDS, ("weak", "mid", "strong")):
                    m = (ATK >= lo) & (ATK <= hi)
                    row[f"{tag}_inc_pct"] = r(inc[m].mean(), 3)
                    row[f"{tag}_kept_pct"] = r(inc[m].mean() / buff, 1)
                    row[f"{tag}_zero_share_pct"] = r(100 * (inc[m] <= 1e-9).mean(), 1)
                row["all_inc_pct"] = r(inc.mean(), 3)
                row["all_zero_share_pct"] = r(100 * (inc <= 1e-9).mean(), 1)
                rows.append(row)
    tab = pd.DataFrame(rows); tab.to_csv(RES / "bands.csv", index=False)

    def pick(spread, buff, key):
        d = tab[(tab.spread == spread) & (tab.buff_pct == round(100 * buff)) & (tab.rule == key)].iloc[0]
        return {c: (d[c] if not isinstance(d[c], (np.floating, np.integer)) else float(d[c])) for c in tab.columns}
    res["base"] = {f"{key}_spread{s}": pick(s, BASE_BUFF, key) for s in (0.0, BASE_SPREAD) for key, _ in RULES}

    # 強化が丸ごと消える攻撃力の上限（ばらつきなし、毎回切り捨て）
    lim = {}
    for buff in BUFFS:
        inc = per_atk[(0.0, buff, "each")][0]
        z = ATK[inc <= 1e-9]
        lim[f"{int(round(100 * buff))}"] = {"max_atk_zero": int(z.max()) if len(z) else None,
                                            "zero_count": int(len(z)),
                                            "first_atk_positive": int(ATK[np.where(inc > 1e-9)[0]][0]) if (inc > 1e-9).any() else None}
        # 式：①のあとの値 x1 が x1×buff < 1 なら②で強化が消える → x1 < 1/buff
        lim[f"{int(round(100 * buff))}"]["formula_x1_below"] = r(1 / buff, 2)
    res["zero_limits_each_nospread"] = lim

    # 例の攻撃力（ばらつきなし、強化3%）
    ex = []
    for a in (10, 20, 27, 28, 40, 60, 100, 200):
        i = int(a - ATK[0])
        for key, name in RULES:
            inc, d0, d1 = per_atk[(0.0, BASE_BUFF, key)]
            ex.append({"atk": a, "rule": key, "dmg_no_buff": r(d0[i], 3), "dmg_buff": r(d1[i], 3), "inc_pct": r(inc[i], 2)})
    res["examples_nospread_buff3"] = ex
    pd.DataFrame(ex).to_csv(RES / "examples.csv", index=False)

    # 攻撃力ごとの値（データ）
    out = {"atk": ATK}
    for s in (0.0, BASE_SPREAD):
        for key, _ in RULES:
            inc, d0, d1 = per_atk[(s, BASE_BUFF, key)]
            out[f"spread{s}_{key}_dmg0"] = np.round(d0, 4); out[f"spread{s}_{key}_dmg3"] = np.round(d1, 4)
            out[f"spread{s}_{key}_inc_pct"] = np.round(inc, 4)
    pd.DataFrame(out).to_csv(DATA / "damage_by_attack.csv", index=False)

    # 置き方を変えた範囲（弱い攻撃力・毎回切り捨ての残る割合）
    sub = tab[tab.rule == "each"]
    res["range_each_weak_kept"] = {f"spread{s}": [r(sub[sub.spread == s]["weak_kept_pct"].min()), r(sub[sub.spread == s]["weak_kept_pct"].max())] for s in SPREADS}
    res["range_each_strong_kept"] = {f"spread{s}": [r(sub[sub.spread == s]["strong_kept_pct"].min()), r(sub[sub.spread == s]["strong_kept_pct"].max())] for s in SPREADS}
    sl = tab[tab.rule == "last"]
    res["range_last_weak_kept"] = {f"spread{s}": [r(sl[sl.spread == s]["weak_kept_pct"].min()), r(sl[sl.spread == s]["weak_kept_pct"].max())] for s in SPREADS}
    res["range_last_strong_kept"] = {f"spread{s}": [r(sl[sl.spread == s]["strong_kept_pct"].min()), r(sl[sl.spread == s]["strong_kept_pct"].max())] for s in SPREADS}

    # 図1：攻撃力ごとの増え（強化3%、ばらつきなし）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for key, name, col in [("each", "毎回切り捨て", BLUE), ("last", "最後だけ切り捨て", ORANGE)]:
        ax.plot(ATK, per_atk[(0.0, BASE_BUFF, key)][0], color=col, lw=1.4, label=name)
    ax.axhline(100 * BASE_BUFF, color=GRAY, lw=1.0, ls="--", label="切り捨てなし（3%、式どおり）")
    ax.set_xlim(0, 300); ax.set_ylim(0, None)
    ax.set_xlabel("攻撃力"); ax.set_ylabel("強化3%でダメージが増えた割合（%）")
    ax.set_title("ばらつきなし：攻撃力が小さいと、3%の強化は0%になったり跳ねたりする")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "a1124_by_attack.png", SRC)

    # 図2：攻撃力の帯ごとに残った割合（強化3%、ばらつき0と±5%）
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.3), sharey=True)
    for ax, s in zip(axes, (0.0, BASE_SPREAD)):
        x = np.arange(3); w = 0.38
        for j, (key, name, col) in enumerate([("each", "毎回切り捨て", BLUE), ("last", "最後だけ切り捨て", ORANGE)]):
            d = pick(s, BASE_BUFF, key)
            vals = [d["weak_inc_pct"], d["mid_inc_pct"], d["strong_inc_pct"]]
            ax.bar(x + (j - 0.5) * w, vals, width=w, color=col, label=name)
            for xi, v in zip(x + (j - 0.5) * w, vals):
                ax.text(xi, v + 0.05, f"{v:.3f}", ha="center", fontsize=7.5)
        ax.axhline(100 * BASE_BUFF, color=GRAY, lw=0.8, ls="--")
        ax.set_xticks(x); ax.set_xticklabels([b[0].replace("（", "\n（") for b in BANDS], fontsize=9)
        ax.set_title("ダメージのばらつきなし" if s == 0 else f"ダメージのばらつき ±{int(s * 100)}%")
        ax.set_ylim(0, 4.2)
    axes[0].set_ylabel("ダメージの平均の増え（%、攻撃力の帯で平均）"); axes[0].legend(frameon=False, loc="upper left", fontsize=9)
    fig.suptitle("強化3%のうち、表に出た増え（点線が3%）", y=1.02)
    save(fig, "a1124_bands.png", SRC)

    # 図3：強化の大きさごとに、弱い攻撃力で残った割合（毎回切り捨て）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    x = np.arange(len(BUFFS)); w = 0.26
    for j, (s, col) in enumerate(zip(SPREADS, (GRAY, BLUE, GREEN))):
        vals = [pick(s, b, "each")["weak_kept_pct"] for b in BUFFS]
        ax.bar(x + (j - 1) * w, vals, width=w, color=col, label=("ばらつきなし" if s == 0 else f"ばらつき ±{int(s * 100)}%"))
        for xi, v in zip(x + (j - 1) * w, vals):
            ax.text(xi, v + 1.5, f"{v:.1f}", ha="center", fontsize=7.5)
    ax.axhline(100, color=GRAY, lw=0.8, ls="--")
    ax.set_xticks(x); ax.set_xticklabels([f"強化 {int(round(100 * b))}%" for b in BUFFS])
    ax.set_ylim(0, 125); ax.set_ylabel("表に出た増え ÷ 強化の大きさ（%）")
    ax.set_title("弱い攻撃力（5〜30）・毎回切り捨てで、強化のうち表に出た割合")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    save(fig, "a1124_buff_size.png", SRC)

    (RES / "a1124_main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1)[:5000])
    print(tab.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
