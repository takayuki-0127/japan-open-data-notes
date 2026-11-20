"""844 少ない週の次は、必ず伸びて見えるのか？（架空のデータ）

架空の動画アカウント2,000個の60週。アカウントごとの本当の再生の水準は基本では変わらず、
週ごとの再生数は、その水準のまわりでたまたま上下する（対数で標準偏差0.35）。
前の4週の平均の8割を下回った週を「少ない週」とし、その次の週がどれだけ伸びて見えるかを数える。
少ない週のあとに「テコ入れ」（効き目を作成者が置く）をしたとき、比べ方で効き目がどう見えるかも数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 844
SRC = "架空の動画アカウント（作成者が乱数で作成、seed 844）"
N_ACC, WEEKS, PRIOR = 2000, 60, 4
SD = 0.35          # 週ごとの再生数の揺れ（対数の標準偏差）
THRESH = 0.8       # 前の4週の平均の何割を下回ったら「少ない週」か


def make_views(rng, sd=SD, persist_share=0.0, rho=0.8, n=N_ACC, weeks=WEEKS):
    """対数の再生数＝アカウントの水準＋続く揺れ（AR(1)）＋その週だけの揺れ。揺れ全体の標準偏差は sd"""
    mu = rng.normal(np.log(10000), 0.8, n)
    s_a, s_e = sd * np.sqrt(persist_share), sd * np.sqrt(1 - persist_share)
    a = np.zeros((n, weeks))
    a[:, 0] = rng.normal(0, s_a, n)
    for t in range(1, weeks):
        a[:, t] = rho * a[:, t - 1] + rng.normal(0, s_a * np.sqrt(1 - rho ** 2), n)
    e = rng.normal(0, s_e, (n, weeks))
    return mu, mu[:, None] + a + e


def events(logv, thresh=THRESH, low=True):
    """少ない週（または多い週）と、その前4週の平均・次の週"""
    v = np.exp(logv)
    rows = []
    for t in range(PRIOR, v.shape[1] - 1):
        prior = v[:, t - PRIOR:t].mean(1)
        hit = v[:, t] < thresh * prior if low else v[:, t] > thresh * prior
        idx = np.flatnonzero(hit)
        rows.append(pd.DataFrame({"acc": idx, "week": t, "prior": prior[idx], "this": v[idx, t], "next": v[idx, t + 1]}))
    return pd.concat(rows, ignore_index=True)


def summarize(ev):
    r_this = ev["next"] / ev["this"] - 1
    r_prior = ev["next"] / ev["prior"] - 1
    return {"n_events": int(len(ev)), "share_up_vs_this": round(float((r_this > 0).mean()), 3),
            "median_vs_this": round(float(r_this.median()), 3), "median_vs_prior": round(float(r_prior.median()), 3),
            "share_up_vs_prior": round(float((r_prior > 0).mean()), 3)}


def apparent_effects(rng, ev, effect):
    """少ない週の半分にテコ入れ（次の週の再生が effect だけ増える）。3つの比べ方で見える効き目"""
    treat = rng.random(len(ev)) < 0.5
    nxt = ev["next"].values * np.where(treat, 1 + effect, 1.0)
    vs_this = nxt / ev["this"].values
    vs_prior = nxt / ev["prior"].values
    m_t, m_c = np.median(vs_this[treat]), np.median(vs_this[~treat])
    return {"前の週と比べる": round(float(m_t - 1), 3),
            "前の4週の平均と比べる": round(float(np.median(vs_prior[treat]) - 1), 3),
            "テコ入れしなかった少ない週と比べる": round(float(m_t / m_c - 1), 3)}


def main():
    rng = np.random.default_rng(SEED)
    mu, logv = make_views(rng)
    # data：はじめの20アカウントの60週
    v = np.exp(logv[:20])
    rows = []
    for i in range(20):
        prior = pd.Series(v[i]).rolling(PRIOR).mean().shift(1).values
        low = (v[i] < THRESH * prior)
        rows.append(pd.DataFrame({"account_id": i + 1, "week": np.arange(1, WEEKS + 1), "true_level": np.exp(mu[i]),
                                  "views": np.round(v[i]).astype(int), "prior4_mean": prior, "low_week": low.astype(int)}))
    pd.concat(rows).to_csv(DATA / "weekly.csv", index=False, float_format="%.1f")

    # 1) 基本：少ない週の次の週
    ev = events(logv)
    base = summarize(ev)
    hi = summarize(events(logv, 1.25, low=False))
    base["n_low_share_of_weeks"] = round(len(ev) / (N_ACC * (WEEKS - PRIOR - 1)), 3)

    # 2) テコ入れの見かけの効き目（本当の効き目 0・+10%）
    eff = {}
    for effect in [0.0, 0.10]:
        eff[f"{effect:.2f}"] = apparent_effects(np.random.default_rng(SEED + int(effect * 100)), ev, effect)
    pd.DataFrame(eff).T.to_csv(RES / "apparent_effect.csv")

    # 3) 確かめ：揺れの大きさ・続く揺れの割合・少ない週の線
    sens = []
    for sd in [0.2, 0.35, 0.5]:
        for ps in [0.0, 0.5, 0.8]:
            _, lv = make_views(np.random.default_rng(SEED * 10 + int(sd * 100) + int(ps * 1000)), sd, ps)
            for th in [0.9, 0.8, 0.7]:
                e = events(lv, th)
                if len(e) < 200:
                    continue
                s = summarize(e)
                ae = apparent_effects(np.random.default_rng(SEED + 7), e, 0.0)
                sens.append({"sd": sd, "persist_share": ps, "thresh": th, **s,
                             "apparent_vs_control": ae["テコ入れしなかった少ない週と比べる"]})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"setting": {"accounts": N_ACC, "weeks": WEEKS, "sd_log": SD, "low_week": "前の4週の平均の8割未満",
                       "persist_share": 0.0},
           "low_week_next": base, "high_week_next(1.25倍超)": hi, "apparent_effect": eff,
           "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a844_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1アカウントの60週
    d = pd.read_csv(DATA / "weekly.csv").query("account_id == 1")
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.plot(d.week, d.views / 1000, color=GRAY, lw=1.2, marker="o", ms=3)
    ax.axhline(d.true_level.iloc[0] / 1000, color=INK, lw=1, ls="--")
    ax.text(WEEKS + 0.5, d.true_level.iloc[0] / 1000, "本当の水準", va="center", fontsize=9)
    lw_ = d[d.low_week == 1]
    nx = d[d.week.isin(lw_.week + 1)]
    ax.plot(lw_.week, lw_.views / 1000, "o", color=ORANGE, ms=6, label="少ない週（前の4週の平均の8割未満）")
    ax.plot(nx.week, nx.views / 1000, "o", color=BLUE, ms=6, label="その次の週")
    ax.set_xlabel("週"); ax.set_ylabel("再生数（千回）"); ax.set_ylim(0, d.views.max() / 1000 * 1.25)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2)
    ax.set_title("水準は変わっていなくても、少ない週の次はたいてい戻る（1アカウント）")
    save(fig, "a844_account.png", SRC)

    # 図2：比べ方ごとの見かけの効き目
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    labels = list(eff["0.00"].keys())
    x = np.arange(len(labels))
    for k, (key, c) in enumerate([("0.00", GRAY), ("0.10", BLUE)]):
        vals = [eff[key][l] * 100 for l in labels]
        ax.bar(x + (k - .5) * .38, vals, .36, color=c, label=f"本当の効き目 {float(key)*100:+.0f}%")
        for xi, vv in zip(x + (k - .5) * .38, vals):
            ax.text(xi, vv + (1 if vv >= 0 else -4), f"{vv:+.0f}%", ha="center", fontsize=9)
    ax.axhline(0, color=INK, lw=.8); ax.set_ylim(-24, None)
    ax.set_xticks(x); ax.set_xticklabels(["前の週\n（少ない週）と比べる", "前の4週の平均\nと比べる", "テコ入れしなかった\n少ない週と比べる"])
    ax.set_ylabel("見かけの効き目（%、中央値）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("少ない週と比べると、効き目0のテコ入れでも大きく伸びて見える")
    save(fig, "a844_compare.png", SRC)

    # 図3：確かめ（揺れ0.35、線0.8・0.7・0.9）
    t = sens[sens.sd == 0.35]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for ps, c in [(0.0, GRAY), (0.5, BLUE), (0.8, ORANGE)]:
        tt = t[t.persist_share == ps].sort_values("thresh", ascending=False)
        ax.plot(tt.thresh, tt.median_vs_this * 100, marker="o", color=c,
                label=f"揺れのうち続く分 {ps*100:.0f}%")
    ax.invert_xaxis()
    ax.set_xticks([0.9, 0.8, 0.7]); ax.set_xticklabels(["9割未満", "8割未満（基本）", "7割未満"])
    ax.set_xlabel("「少ない週」の線（前の4週の平均に対して）"); ax.set_ylabel("次の週の伸び（%、中央値）")
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=9, title="揺れの大きさ0.35のとき", title_fontsize=9)
    ax.set_title("少ない週が深いほど、次の週は大きく戻る。揺れが続くと戻りは小さい")
    save(fig, "a844_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
