"""819 移動平均の幅で、山と谷はどれだけ動くのか？（架空のデータ）

架空の店の毎日の来店数（2年＝728日）。本当の来店数の流れ（1年の山と谷・2週間の催しの山）を作成者が置き、
曜日の差と日々の散らばりを足したものを「見える来店数」とする。移動平均の幅と、後ろ向き（直近 w 日）か
中心（前後 w 日）かで、山と谷の日付・高さ・山の数がどれだけ動くかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 819
SRC = "架空の店の来店数（作成者が乱数で作成、seed 819）"
N_DAY = 728          # 2年（364日×2）
PERIOD = 364
PEAK_DAY, TROUGH_DAY = 200, 382      # 本当の1年の山（1年目）と谷（2年目のはじめ）
BASE, AMP = 300, 60                  # 平均の来店数と1年の波の大きさ
WEEKEND = 0.20                       # 土日は2割多い
CAMP_START, CAMP_LEN, CAMP_H = 450, 14, 80   # 2週間の催し（1日80人多い）
NOISE = 30                           # 日々の散らばり（標準偏差、人）
WIDTHS = [1, 7, 14, 28, 56, 91]
N_REP = 200


def true_level(camp_len=CAMP_LEN):
    t = np.arange(N_DAY)
    lv = BASE + AMP * np.cos(2 * np.pi * (t - PEAK_DAY) / PERIOD)
    camp = np.zeros(N_DAY)
    camp[CAMP_START:CAMP_START + camp_len] = CAMP_H
    return lv, camp


def make_series(rng, noise=NOISE, camp_len=CAMP_LEN):
    t = np.arange(N_DAY)
    lv, camp = true_level(camp_len)
    wk = np.where(t % 7 >= 5, 1 + WEEKEND, 1 - WEEKEND * 2 / 5)   # 1週間の平均は変えない
    y = (lv + camp) * wk + rng.normal(0, noise, N_DAY)
    return np.clip(np.round(y), 0, None)


def ma(y, w, kind):
    s = pd.Series(y)
    if w == 1:
        return s.values.astype(float)
    return s.rolling(w, center=(kind == "center")).mean().values


PROM = 10   # 山として数える高さ：前後とも10人以上下がるところ


def n_peaks(s, h=PROM):
    """上がって h 以上下がったら1つの山と数える（ジグザグの数え方）"""
    x = s[~np.isnan(s)]
    n, mode, hi, lo = 0, 0, x[0], x[0]   # mode 0:未定 1:上り 2:下り
    for v in x[1:]:
        if mode != 1 and v >= lo + h:
            mode, hi = 1, v
        elif mode == 1:
            if v > hi:
                hi = v
            elif v <= hi - h:
                n += 1; mode, lo = 2, v
        if mode != 1:
            lo = min(lo, v)
    return n


def measure(y, w, kind, camp_len=CAMP_LEN):
    s = ma(y, w, kind)
    lv, _ = true_level(camp_len)
    pk = 80 + int(np.nanargmax(s[80:321]))
    tr = 290 + int(np.nanargmin(s[290:441]))
    return {"peak_shift": pk - PEAK_DAY, "trough_shift": tr - TROUGH_DAY,
            "amp": float(s[pk] - s[tr]) / 2, "n_peaks": n_peaks(s)}


def camp_kept(w, kind, camp_len=CAMP_LEN):
    """催しの分だけを移動平均したときの高さ（散らばりに関係なく決まる、理屈の値）"""
    t = np.arange(N_DAY)
    _, camp = true_level(camp_len)
    wk = np.where(t % 7 >= 5, 1 + WEEKEND, 1 - WEEKEND * 2 / 5)
    c = ma(camp * wk, w, kind)
    return (round(float(np.nanmax(c)) / CAMP_H, 3),)


def main():
    rng = np.random.default_rng(SEED)
    y0 = make_series(rng)
    lv, camp = true_level()
    df = pd.DataFrame({"day": np.arange(N_DAY), "true_level": np.round(lv + camp, 2), "visits": y0.astype(int)})
    for w in [7, 28, 91]:
        df[f"ma{w}_trailing"] = np.round(ma(y0, w, "trailing"), 2)
        df[f"ma{w}_center"] = np.round(ma(y0, w, "center"), 2)
    df.to_csv(DATA / "visits.csv", index=False)

    # 1) 幅と向きごとの測り（200回）
    rows = []
    for r in range(N_REP):
        y = make_series(np.random.default_rng(SEED * 1000 + r))
        for kind in ["trailing", "center"]:
            for w in WIDTHS:
                m = measure(y, w, kind)
                m.update(rep=r, kind=kind, width=w)
                rows.append(m)
    sim = pd.DataFrame(rows)
    g = sim.groupby(["kind", "width"], sort=False)
    summ = g[["peak_shift", "trough_shift", "amp", "n_peaks"]].mean().round(3)
    summ["peak_shift_p10"] = g.peak_shift.quantile(.1)
    summ["peak_shift_p90"] = g.peak_shift.quantile(.9)
    summ["amp_ratio"] = (summ["amp"] / AMP).round(3)
    summ = summ.reset_index()
    ck = [camp_kept(w, k) for k, w in zip(summ.kind, summ.width)]
    summ["camp_ratio"] = [c[0] for c in ck]
    summ.to_csv(RES / "by_width.csv", index=False)

    # 2) 確かめ：日々の散らばりの大きさ、催しの長さ（後ろ向き）
    sens_noise, sens_camp = {}, {}
    for nz in [15, 30, 60]:
        rr = []
        for r in range(100):
            y = make_series(np.random.default_rng(SEED * 31 + r + nz * 1000), noise=nz)
            for w in [7, 28]:
                m = measure(y, w, "trailing"); m["width"] = w; rr.append(m)
        t = pd.DataFrame(rr).groupby("width")[["peak_shift", "n_peaks"]].mean().round(3)
        t["peak_shift_sd"] = pd.DataFrame(rr).groupby("width").peak_shift.std().round(2)
        sens_noise[str(nz)] = t.reset_index().to_dict("records")
    for cl in [7, 14, 28]:
        sens_camp[str(cl)] = {str(w): camp_kept(w, "trailing", cl)[0] for w in [7, 14, 28, 91]}
    sens_prom = {}
    for h in [5, 10, 20]:
        rr = []
        for r in range(100):
            y = make_series(np.random.default_rng(SEED * 41 + r))
            rr.append({str(w): n_peaks(ma(y, w, "trailing"), h) for w in WIDTHS})
        sens_prom[str(h)] = pd.DataFrame(rr).mean().round(2).to_dict()

    out = {"setting": {"days": N_DAY, "base": BASE, "amp": AMP, "peak_day": PEAK_DAY, "trough_day": TROUGH_DAY,
                       "weekend": WEEKEND, "camp_start": CAMP_START, "camp_len": CAMP_LEN, "camp_h": CAMP_H,
                       "noise_sd": NOISE, "reps": N_REP, "true_n_peaks": 3},
           "by_width_200reps": summ.to_dict("records"),
           "sens_noise_trailing_100reps": sens_noise, "camp_kept_by_len_trailing": sens_camp,
           "n_peaks_by_threshold_trailing_100reps": sens_prom, "peak_threshold": PROM}
    json.dump(out, open(RES / "a819_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分（1年目の後半〜2年目）
    fig, ax = plt.subplots(figsize=(8.0, 4.3))
    sl = slice(120, 600)
    ax.plot(df.day[sl], df.visits[sl], color=GRAY, lw=.5, alpha=.6, label="毎日の来店数")
    ax.plot(df.day[sl], df.true_level[sl], color=INK, lw=1, ls=":", label="本当の流れ（作成者が置いた）")
    ax.plot(df.day[sl], df.ma7_trailing[sl], color=LIGHT, lw=1.2, label="直近7日の平均")
    ax.plot(df.day[sl], df.ma28_trailing[sl], color=BLUE, lw=1.6, label="直近28日の平均")
    ax.plot(df.day[sl], df.ma91_trailing[sl], color=ORANGE, lw=1.8, label="直近91日の平均")
    ax.axvline(PEAK_DAY, color=INK, lw=.6); ax.text(PEAK_DAY + 3, 455, "本当の山", fontsize=8)
    ax.axvline(TROUGH_DAY, color=INK, lw=.6); ax.text(TROUGH_DAY + 3, 455, "本当の谷", fontsize=8)
    ax.text(CAMP_START + 16, 430, "2週間の催し", fontsize=8)
    ax.set_xlabel("日（0日目から数えて）"); ax.set_ylabel("来店数（人）"); ax.set_ylim(150, 470)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="lower left")
    ax.set_title("幅の広い「直近の平均」ほど、山と谷が遅れ、短い山はつぶれる（1回分）")
    save(fig, "a819_series.png", SRC)

    # 図2：山の日付のずれ
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for kind, col, lab in [("trailing", ORANGE, "直近 w 日の平均（後ろ向き）"), ("center", BLUE, "前後 w 日の平均（中心）")]:
        s = summ[summ.kind == kind]
        ax.plot(s.width, s.peak_shift, "o-", color=col, label=lab)
        ax.fill_between(s.width, s.peak_shift_p10, s.peak_shift_p90, color=col, alpha=.15, lw=0)
        dy = 3 if kind == "trailing" else -5
        for x, v in zip(s.width, s.peak_shift):
            if x == 1 and kind == "center":
                continue
            ax.text(x - (1.5 if kind == "trailing" else 0), v + dy, f"{v:+.0f}" if abs(v) >= .5 else "0",
                    color=col, fontsize=8, ha="center")
    ax.axhline(0, color=GRAY, lw=.8)
    ax.set_xticks(WIDTHS); ax.set_xlabel("移動平均の幅 w（日）"); ax.set_ylabel("山の日付のずれ（日、+は遅れ）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("後ろ向きの平均は、幅のおよそ半分だけ山を遅らせる（200回、帯は10〜90%）")
    save(fig, "a819_peak_shift.png", SRC)

    # 図3：催しの山の高さと山の数
    s = summ[summ.kind == "trailing"]
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.6))
    axs[0].bar([str(w) for w in s.width], s.camp_ratio * 100, color=BLUE)
    for i, v in enumerate(s.camp_ratio * 100):
        axs[0].text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=8)
    axs[0].axhline(100, color=GRAY, lw=.8, ls="--")
    axs[0].set_xlabel("幅 w（日）（1は毎日の数。土日は1.2倍）"); axs[0].set_ylabel("本当の高さ80人に対する%")
    axs[0].set_title("2週間の催しの山の高さ（理屈の値）", fontsize=11)
    axs[1].bar([str(w) for w in s.width], s.n_peaks, color=ORANGE)
    for i, v in enumerate(s.n_peaks):
        axs[1].text(i, v * 1.15, f"{v:.0f}", ha="center", fontsize=8)
    axs[1].set_yscale("log"); axs[1].set_ylim(1, 300)
    axs[1].set_yticks([1, 3, 10, 30, 100]); axs[1].set_yticklabels(["1", "3", "10", "30", "100"])
    axs[1].axhline(3, color=GRAY, lw=.8, ls="--"); axs[1].text(5.45, 3.3, "本当は3", fontsize=8, ha="right")
    axs[1].set_xlabel("幅 w（日）"); axs[1].set_ylabel("2年間の山の数（対数の目盛り）")
    axs[1].set_title("線の山の数（10人以上の上下、200回の平均）", fontsize=11)
    fig.suptitle("直近 w 日の平均：幅を広げると細かい山は減るが、短い山の高さも消える", fontsize=12)
    fig.tight_layout()
    save(fig, "a819_width_tradeoff.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
