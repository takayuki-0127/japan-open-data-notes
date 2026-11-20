"""816 累積のグラフは、伸びが止まっても右肩上がりに見えるのか？（架空のデータ）

架空の会社の月ごとの売上（36か月）。1〜24か月目は100から1,000へ直線で伸び、
25か月目から「横ばい」「毎月3%減」「毎月8%減」の3つの型に分かれる（作成者が置いた正解）。
毎月の値には±5%ほどの揺れ（対数で標準偏差0.05）を足す。
同じ売上を「月ごとの線」と「累積の線」で描き、36か月目に作った図の上での線の傾き（角度）を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 816
SRC = "架空の会社の月ごとの売上（作成者が乱数で作成、seed 816）"
rng = np.random.default_rng(SEED)
T = 36
STOP = 24                      # この月までは伸びる
MONTHS = np.arange(1, T + 1)
PATTERNS = {"横ばい": 1.00, "毎月3%減": 0.97, "毎月8%減": 0.92}
N_REP = 500
ASPECT = 1.6                   # 図の描く部分の 横÷縦
NOISE = 0.05
THETA = 10                     # 角度がこれだけ下がったら「鈍った」と気づく（度）


def base(rate):
    b = 100 + 900 * (MONTHS - 1) / (STOP - 1)
    after = MONTHS > STOP
    b[after] = 1000 * rate ** (MONTHS[after] - STOP)
    return b


def draw(rate, rng, noise=NOISE):
    return base(rate) * np.exp(rng.normal(0, noise, T))


def angle(y, lo, hi, top, aspect):
    """lo〜hi か月目（両端を含む）の当てはめた直線の、図の上での角度（度）。
    図は横軸1〜36か月を幅 aspect、縦軸0〜top を高さ1に描く。"""
    x = MONTHS[lo - 1:hi]
    s = np.polyfit(x, y[lo - 1:hi], 1)[0]
    return float(np.degrees(np.arctan((s / top) / (aspect / (T - 1)))))


def notice(y, aspect, theta):
    """直近6か月の角度が、その前の6か月より theta 度以上下がった最初の月。
    25か月目以降で最初の月（なければ None）と、13〜24か月目に誤って気づいたか。"""
    top = y.max() * 1.05
    first, false_alarm = None, False
    for m in range(12, T + 1):
        drop = angle(y, m - 11, m - 6, top, aspect) - angle(y, m - 5, m, top, aspect)
        if drop >= theta:
            if m <= STOP:
                false_alarm = True
            elif first is None:
                first = m
    return first, false_alarm


def summarize(rng, aspect=ASPECT, noise=NOISE, theta=THETA, n_rep=N_REP):
    rows = []
    for name, rate in PATTERNS.items():
        rec = {"monthly": [], "cum": []}
        for _ in range(n_rep):
            m = draw(rate, rng, noise)
            c = m.cumsum()
            for kind, y in [("monthly", m), ("cum", c)]:
                top = y.max() * 1.05
                f, fa = notice(y, aspect, theta)
                rec[kind].append({"prev12": angle(y, 13, 24, top, aspect), "last12": angle(y, 25, 36, top, aspect),
                                  "last12_height": float((y[-1] - y[STOP - 1]) / top) if kind == "cum" else np.nan,
                                  "lag": np.nan if f is None else f - STOP, "found": f is not None, "false": fa})
        for kind in ["monthly", "cum"]:
            d = pd.DataFrame(rec[kind])
            rows.append({"pattern": name, "chart": "月ごと" if kind == "monthly" else "累積",
                         "angle_prev12": round(d.prev12.mean(), 1), "angle_last12": round(d.last12.mean(), 1),
                         "found_share": round(d.found.mean(), 3),
                         "lag_median": None if d.found.sum() == 0 else float(d.lag.median()),
                         "false_alarm_share": round(d["false"].mean(), 3),
                         "last12_height": None if kind == "monthly" else round(d.last12_height.mean(), 3)})
    return pd.DataFrame(rows)


def clean(o):
    """json に NaN を書かないよう None に直す"""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


def main():
    # 1回分のデータ
    one = []
    for name, rate in PATTERNS.items():
        m = draw(rate, rng)
        one.append(pd.DataFrame({"pattern": name, "month": MONTHS, "monthly": m.round(1), "cumulative": m.cumsum().round(1)}))
    one = pd.concat(one, ignore_index=True)
    one.to_csv(DATA / "monthly.csv", index=False)

    # 基本の置き方（500回）
    main_tab = summarize(np.random.default_rng(SEED * 10))
    main_tab.to_csv(RES / "angles.csv", index=False)

    # 正解のまま（揺れなし）の値：最後の月が伸びの止まった月の何割か
    truth = {name: {"last_vs_month24": round(float(base(r)[-1] / base(r)[STOP - 1]), 3),
                    "cum_month36_vs_24": round(float(base(r).cumsum()[-1] / base(r).cumsum()[STOP - 1]), 3)}
             for name, r in PATTERNS.items()}

    # 確かめ：気づく角度・図の縦横・揺れの大きさを変える
    sens = []
    for label, kw in [("基本（10度・横÷縦1.6・揺れ5%）", {}),
                      ("気づく角度 5度", {"theta": 5}), ("気づく角度 20度", {"theta": 20}),
                      ("横÷縦 1.0", {"aspect": 1.0}), ("横÷縦 2.5", {"aspect": 2.5}),
                      ("揺れなし", {"noise": 0.0}), ("揺れ15%", {"noise": 0.15})]:
        t = summarize(np.random.default_rng(SEED * 100 + len(sens)), n_rep=200, **kw)
        t.insert(0, "setting", label)
        sens.append(t)
    sens = pd.concat(sens, ignore_index=True)
    sens.to_csv(RES / "notice_sensitivity.csv", index=False)

    # 直近6か月の角度を月ごとに（500回の平均）
    rr = np.random.default_rng(SEED * 1000)
    rows = []
    for name, rate in PATTERNS.items():
        acc = {"月ごと": np.zeros(T - 5), "累積": np.zeros(T - 5)}
        for _ in range(N_REP):
            m = draw(rate, rr)
            for chart, y in [("月ごと", m), ("累積", m.cumsum())]:
                top = y.max() * 1.05
                acc[chart] += [angle(y, k - 5, k, top, ASPECT) for k in range(6, T + 1)]
        for chart in acc:
            for k, v in zip(range(6, T + 1), acc[chart] / N_REP):
                rows.append({"pattern": name, "chart": chart, "month": k, "angle6": round(float(v), 2)})
    roll = pd.DataFrame(rows)
    roll.to_csv(RES / "rolling_angle.csv", index=False)

    out = {"assumptions": {"months": T, "growth_until": STOP, "growth": "100→1000（直線）", "patterns": PATTERNS,
                           "noise_log_sd": NOISE, "aspect_w_over_h": ASPECT, "theta_deg": THETA, "reps": N_REP},
           "truth": truth, "main": main_tab.to_dict("records"), "sensitivity": sens.to_dict("records")}
    json.dump(clean(out), open(RES / "a816_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ売上を月ごとと累積で
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    cols = {"横ばい": BLUE, "毎月3%減": GREEN, "毎月8%減": ORANGE}
    for name in PATTERNS:
        g = one[one.pattern == name]
        axes[0].plot(g.month, g.monthly, color=cols[name], lw=1.8, label=name)
        axes[1].plot(g.month, g.cumulative / 1000, color=cols[name], lw=1.8, label=name)
    for ax, t in zip(axes, ["月ごとの売上", "累積の売上（千）"]):
        ax.axvline(STOP + 0.5, color=GRAY, ls="--", lw=1)
        ax.set_ylim(0, None); ax.set_xlabel("月"); ax.set_title(t)
    axes[0].text(STOP + 1, 80, "25か月目から\n伸びが止まる", color=GRAY, fontsize=9)
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("月ごとでは下がっている売上も、累積ではどれも右肩上がりのまま", y=1.02)
    save(fig, "a816_pair.png", SRC)

    # 図2：最後の12か月の角度（その前の12か月と比べて）
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, chart in zip(axes, ["月ごと", "累積"]):
        t = main_tab[main_tab.chart == chart]
        x = np.arange(len(t))
        ax.bar(x - 0.2, t.angle_prev12, 0.4, color=LIGHT, label="13〜24か月目（伸びている）")
        ax.bar(x + 0.2, t.angle_last12, 0.4, color=BLUE, label="25〜36か月目（止まった後）")
        for i, (a, b) in enumerate(zip(t.angle_prev12, t.angle_last12)):
            ax.text(i - 0.2, max(a, 0) + 1.5, f"{a:.0f}°".replace("-0°", "0°"), ha="center", fontsize=8.5)
            ax.text(i + 0.2, max(b, 0) + 1.5, f"{b:.0f}°".replace("-0°", "0°"), ha="center", fontsize=8.5)
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_xticks(x); ax.set_xticklabels(t.pattern); ax.set_title(f"{chart}の線")
    axes[0].set_ylabel("図の上での線の角度（度）"); axes[0].legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.suptitle("累積の線は、売上が毎月8%減っても上向きのまま（500回の平均・横÷縦1.6の図）", y=1.02)
    save(fig, "a816_angle.png", SRC)

    # 図3：直近6か月の線の角度を、月を追って（500回の平均）
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, chart in zip(axes, ["月ごと", "累積"]):
        for name in PATTERNS:
            g = roll[(roll.chart == chart) & (roll.pattern == name)]
            ax.plot(g.month, g.angle6, color=cols[name], lw=1.8, label=name)
        ax.axvline(STOP + 0.5, color=GRAY, ls="--", lw=1); ax.axhline(0, color=INK, lw=0.8)
        ax.set_xlabel("月（その月までの6か月で引いた線）"); ax.set_title(f"{chart}の線")
    axes[0].set_ylabel("図の上での線の角度（度）"); axes[0].legend(frameon=False, fontsize=9, loc="lower left")
    fig.suptitle("止まった直後、月ごとの線の角度はすぐ下がるが、累積の線はほとんど動かない", y=1.02)
    save(fig, "a816_rolling.png", SRC)
    print(json.dumps({"truth": truth, "main": out["main"]}, ensure_ascii=False, indent=1))
    print(sens.to_string())


if __name__ == "__main__":
    main()
