"""870 謝礼を付けると、回答者の構成はどう変わるのか？（架空のデータ）

架空のサービスの利用者2万人。利用の多さ（少ない・中くらい・多い）と、本当に満足しているかを作成者が置く。
4,000人に回答をお願いし、答えるかどうかは「もともと答える気持ち」と「謝礼につられて答える」の2つの道で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 870
SRC = "架空のサービスの利用者アンケート（作成者が乱数で作成、seed 870）"
N_USER, N_INVITE, REPS = 20000, 4000, 400
SEG = ["利用が少ない", "中くらい", "利用が多い"]
SEG_SHARE = np.array([0.40, 0.35, 0.25])
SAT = np.array([0.45, 0.60, 0.75])          # 区分ごとの本当に満足している割合
BASE = np.array([0.04, 0.08, 0.16])         # もともと答える確率（満足していない人）
SAT_OR = 1.6                                # 満足している人は答えるオッズが1.6倍
REWARD = {"謝礼なし": np.array([0.0, 0.0, 0.0]),
          "謝礼A（利用の少ない人に効く）": np.array([0.12, 0.08, 0.04]),
          "謝礼B（利用の多い人に効く）": np.array([0.02, 0.06, 0.24])}


def make_users(rng, n=N_USER):
    seg = rng.choice(3, size=n, p=SEG_SHARE)
    sat = rng.random(n) < SAT[seg]
    return seg, sat


def p_intrinsic(seg, sat, sat_or):
    b = BASE[seg]
    o = b / (1 - b) * np.where(sat, sat_or, 1.0)
    return o / (1 + o)


def survey(rng, seg, sat, reward, strength=1.0, sat_or=SAT_OR):
    idx = rng.choice(len(seg), N_INVITE, replace=False)
    s, t = seg[idx], sat[idx]
    p = 1 - (1 - p_intrinsic(s, t, sat_or)) * (1 - np.clip(reward[s] * strength, 0, 1))
    r = rng.random(N_INVITE) < p
    s, t = s[r], t[r]
    n = len(s)
    comp = np.array([(s == k).mean() for k in range(3)])
    raw = t.mean()
    seg_sat = np.array([t[s == k].mean() if (s == k).any() else np.nan for k in range(3)])
    w = float(np.nansum(SEG_SHARE * seg_sat))   # 利用の多さの区分で重み付け（区分の割合は利用記録で分かると置く）
    return {"n_resp": n, "rate": n / N_INVITE, "comp": comp, "raw": raw, "weighted": w, "seg_sat": seg_sat}


def main():
    rng = np.random.default_rng(SEED)
    true_pop = float((SEG_SHARE * SAT).sum())

    # 1回分のデータ（data/users.csv）
    seg, sat = make_users(rng)
    rows = {}
    df = pd.DataFrame({"user_id": np.arange(1, N_USER + 1), "segment": np.array(SEG)[seg], "satisfied": sat.astype(int)})
    inv = rng.choice(N_USER, N_INVITE, replace=False)
    df["invited"] = 0; df.loc[inv, "invited"] = 1
    u = rng.random(N_USER)
    for j, (name, rw) in enumerate(REWARD.items()):
        p = 1 - (1 - p_intrinsic(seg, sat, SAT_OR)) * (1 - rw[seg])
        df[f"answered_{j}"] = ((df.invited == 1) & (u < p)).astype(int)   # 同じ乱数で3つの条件を比べる
    df.to_csv(DATA / "users.csv", index=False)

    # 2) 3つの条件を400回（利用者を作り直す）
    rec = []
    for r in range(REPS):
        g = np.random.default_rng(SEED * 1000 + r)
        s0, t0 = make_users(g)
        tp = float(t0.mean())
        for name, rw in REWARD.items():
            o = survey(g, s0, t0, rw)
            rec.append({"rep": r, "cond": name, "true": tp, "n_resp": o["n_resp"], "rate": o["rate"],
                        "light": o["comp"][0], "mid": o["comp"][1], "heavy": o["comp"][2],
                        "raw": o["raw"], "weighted": o["weighted"],
                        "light_sat": o["seg_sat"][0], "heavy_sat": o["seg_sat"][2]})
    sim = pd.DataFrame(rec)
    sim["raw_err"] = (sim.raw - sim.true) * 100
    sim["w_err"] = (sim.weighted - sim.true) * 100
    summ = sim.groupby("cond", sort=False).agg(
        n_resp=("n_resp", "mean"), rate=("rate", "mean"), light=("light", "mean"), mid=("mid", "mean"),
        heavy=("heavy", "mean"), raw=("raw", "mean"), weighted=("weighted", "mean"),
        raw_err=("raw_err", "mean"), raw_err_p05=("raw_err", lambda x: x.quantile(.05)),
        raw_err_p95=("raw_err", lambda x: x.quantile(.95)), w_err=("w_err", "mean"),
        w_err_p05=("w_err", lambda x: x.quantile(.05)), w_err_p95=("w_err", lambda x: x.quantile(.95)),
        light_sat=("light_sat", "mean"), heavy_sat=("heavy_sat", "mean")).round(4)
    summ.to_csv(RES / "by_condition.csv")

    # 3) 確かめ：謝礼の効き方の強さ×満足とのつながり（各200回）
    sens = []
    for so in [1.0, 1.6, 2.5]:
        for st in [0.5, 1.0, 2.0]:
            for name, rw in REWARD.items():
                if name == "謝礼なし" and st != 1.0:
                    continue
                re_, we_, li = [], [], []
                for r in range(200):
                    g = np.random.default_rng(SEED * 77 + r + int(so * 10) * 1000 + int(st * 10) * 100000)
                    s0, t0 = make_users(g)
                    o = survey(g, s0, t0, rw, st, so)
                    re_.append((o["raw"] - t0.mean()) * 100); we_.append((o["weighted"] - t0.mean()) * 100)
                    li.append(o["comp"][0])
                sens.append({"sat_or": so, "strength": st if name != "謝礼なし" else 0.0, "cond": name,
                             "light_share": round(float(np.mean(li)), 4), "raw_err": round(float(np.mean(re_)), 2),
                             "w_err": round(float(np.mean(we_)), 2)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    one = {}
    for j, name in enumerate(REWARD):
        a = df[df[f"answered_{j}"] == 1]
        one[name] = {"n_resp": int(len(a)), "light_share": round(float((a.segment == SEG[0]).mean()), 4),
                     "raw": round(float(a.satisfied.mean()), 4)}
    one["true_this_draw"] = round(float(df.satisfied.mean()), 4)
    out = {"true_pop_expected": round(true_pop, 4), "by_condition": summ.reset_index().to_dict("records"),
           "sensitivity": sens.to_dict("records"), "one_draw": one}
    json.dump(out, open(RES / "a870_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：回答者の構成
    s = summ.reset_index()
    labels = ["利用者全体"] + ["回答者：" + c for c in s.cond]
    comp = np.vstack([SEG_SHARE, s[["light", "mid", "heavy"]].values]) * 100
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    left = np.zeros(len(labels)); cols = [ORANGE, LIGHT, BLUE]
    for k in range(3):
        ax.barh(labels[::-1], comp[::-1, k], left=left[::-1], color=cols[k], label=SEG[k])
        for i, (v, l0) in enumerate(zip(comp[::-1, k], left[::-1])):
            ax.text(l0 + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=9,
                    color="white" if k != 1 else INK)
        left += comp[:, k]
    ax.set_xlim(0, 100); ax.set_xlabel("割合（%、400回の平均）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.18))
    ax.set_title("謝礼が誰に効くかで、回答者の構成は逆の向きに動く")
    save(fig, "a870_composition.png", SRC, y=-0.2)

    # 図2：満足の割合の見積もりのずれ
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    y = np.arange(len(s))
    for off, col, key, lab in [(-0.17, GRAY, "raw", "回答者そのまま"), (0.17, BLUE, "w", "利用の多さで重み付け")]:
        m = s[f"{key}_err"].values
        lo, hi = s[f"{key}_err_p05"].values, s[f"{key}_err_p95"].values
        ax.barh(y[::-1] + off, m, height=0.32, color=col, label=lab)
        ax.errorbar(m, y[::-1] + off, xerr=[m - lo, hi - m], fmt="none", ecolor=INK, lw=0.8, capsize=2)
        for yy, v, h in zip(y[::-1] + off, m, hi):
            ax.text(h + 0.3, yy, f"+{v:.1f}", va="center", fontsize=9)
    ax.set_yticks(y[::-1]); ax.set_yticklabels(s.cond)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("満足の割合の見積もり − 本当の割合（ポイント、棒は400回の平均、線は5〜95%）")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper center", bbox_to_anchor=(0.45, -0.2))
    ax.set_title("満足の割合の見積もりは、どの条件でも本当より高く出た")
    save(fig, "a870_error.png", SRC, y=-0.2)

    # 図3：確かめ（満足とのつながり1.6の場合、謝礼の強さ）
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    base0 = sens[(sens.sat_or == 1.6) & (sens.cond == "謝礼なし")].raw_err.iloc[0]
    for name, col in [("謝礼A（利用の少ない人に効く）", ORANGE), ("謝礼B（利用の多い人に効く）", BLUE)]:
        d = sens[(sens.sat_or == 1.6) & (sens.cond == name)]
        xs = [0] + list(d.strength); ys = [base0] + list(d.raw_err)
        ax.plot(xs, ys, marker="o", color=col, label=name)
        for xx, yy in zip(xs[1:], ys[1:]):
            ax.text(xx, yy + 0.4, f"+{yy:.1f}", ha="center", fontsize=9, color=col)
    ax.text(0, base0 + 0.4, f"+{base0:.1f}", ha="center", fontsize=9)
    ax.set_xticks([0, 0.5, 1, 2]); ax.set_xticklabels(["謝礼なし", "効き方0.5倍", "1倍（基本）", "2倍"])
    ax.set_ylabel("ずれ（ポイント、回答者そのまま）"); ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("謝礼の効き方の強さを変えたときのずれ（満足した人の答えやすさ1.6倍）")
    save(fig, "a870_strength.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
