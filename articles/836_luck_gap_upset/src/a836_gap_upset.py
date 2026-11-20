"""836 実力差がどれだけあれば、偶然の逆転は起きにくくなるのか？（架空のデータ）

架空の2チーム（強いA・弱いB）の試合。1試合は N 回の「点の機会」でできていて、1回ごとに A が点を取る確率を q と置く
（B が取る確率は 1−q）。点の多いほうが勝ち、同点はくじ（半々）で決める。
1回あたりの差 q が同じでも、点の機会 N が多い競技ほど、試合単位の逆転（Bの勝ち）は起きにくい。
試合数を増やしたシリーズ（3・5・7試合で先に過半数）と、試合ごとの調子の波も数える。
"""
import json
from math import comb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 836
SRC = "架空の2チームの試合（作成者が乱数で作成、seed 836）"
rng = np.random.default_rng(SEED)
NS = [10, 30, 100, 300]
QS = np.round(np.arange(0.50, 0.7001, 0.005), 3)


def upset_exact(n, q):
    """1試合で B が勝つ確率（同点は半々）"""
    p_b = 0.0
    for k in range(n + 1):  # k = A の点
        pk = comb(n, k) * q ** k * (1 - q) ** (n - k)
        if 2 * k < n:
            p_b += pk
        elif 2 * k == n:
            p_b += pk / 2
    return p_b


def series_upset(p_win, games):
    """1試合で A が勝つ確率 p_win のとき、games 試合で先に過半数を取るシリーズを B が取る確率"""
    need = games // 2 + 1
    # B が need 勝する前に A が need 勝しない確率＝ games 試合を全部やったと考えて B が need 勝以上
    pb = 1 - p_win
    return sum(comb(games, k) * pb ** k * p_win ** (games - k) for k in range(need, games + 1))


def need_q(n, target):
    """1試合の逆転が target 以下になる最小の q（0.001刻み）"""
    for q in np.round(np.arange(0.5, 0.9001, 0.001), 3):
        if upset_exact(n, q) <= target:
            return float(q)
    return None


def need_p(games, target):
    for p in np.round(np.arange(0.5, 0.9901, 0.001), 3):
        if series_upset(p, games) <= target:
            return float(p)
    return None


def sim_upset(rng, n, q, games=200000, form_sd=0.0):
    """乱数で試合をする。form_sd：試合ごとに q が上下する大きさ（調子の波）"""
    qq = np.clip(q + rng.normal(0, form_sd, games), 0.01, 0.99) if form_sd > 0 else np.full(games, q)
    a = rng.binomial(n, qq)
    b = n - a
    tie = a == b
    coin = rng.random(games) < 0.5
    b_win = (b > a) | (tie & coin)
    return float(b_win.mean()), a, b


def main():
    out = {}

    # 1) 1試合の逆転の確率（式で計算）：q × N
    rows = []
    for n in NS:
        for q in QS:
            rows.append({"N": n, "q": q, "upset": round(upset_exact(n, q), 4)})
    curve = pd.DataFrame(rows)
    curve.to_csv(RES / "upset_by_q_N.csv", index=False)
    tab = {}
    for n in NS:
        tab[str(n)] = {str(q): round(upset_exact(n, q), 3) for q in [0.52, 0.55, 0.60, 0.65]}
    out["upset_one_game"] = tab
    out["need_q_one_game"] = {str(n): {"le_20pct": need_q(n, 0.20), "le_10pct": need_q(n, 0.10),
                                       "le_5pct": need_q(n, 0.05)} for n in NS}

    # 1b) 乱数で試合をして、式と合うかを確かめる（各20万試合）
    chk = {}
    for n in NS:
        for q in [0.55, 0.60]:
            s, _, _ = sim_upset(np.random.default_rng(SEED * 10 + n + int(q * 100)), n, q)
            chk[f"N{n}_q{q}"] = {"sim": round(s, 4), "exact": round(upset_exact(n, q), 4)}
    out["sim_check"] = chk

    # 2) シリーズ（1・3・5・7・11試合で先に過半数）：1試合の勝率 p ごとの逆転
    ps = np.round(np.arange(0.5, 0.8501, 0.01), 2)
    srows = []
    for g in [1, 3, 5, 7, 11]:
        for p in ps:
            srows.append({"games": g, "p_win_one_game": p, "series_upset": round(series_upset(p, g), 4)})
    ser = pd.DataFrame(srows)
    ser.to_csv(RES / "series_upset.csv", index=False)
    out["series_upset"] = {str(g): {str(p): round(series_upset(p, g), 3) for p in [0.55, 0.6, 0.65, 0.7]}
                           for g in [1, 3, 5, 7, 11]}
    out["need_p_series"] = {str(g): {"le_10pct": need_p(g, 0.10), "le_5pct": need_p(g, 0.05)}
                            for g in [1, 3, 5, 7, 11]}

    # 3) 確かめ：試合ごとの調子の波（q が試合ごとに標準偏差 form_sd で上下する）
    frows = []
    for sd in [0.0, 0.03, 0.06]:
        for n in NS:
            s, _, _ = sim_upset(np.random.default_rng(SEED * 100 + n + int(sd * 1000)), n, 0.55, form_sd=sd)
            frows.append({"form_sd": sd, "N": n, "q": 0.55, "upset_sim": round(s, 4)})
    form = pd.DataFrame(frows)
    form.to_csv(RES / "form_noise.csv", index=False)
    out["form_noise_q055"] = frows

    # data：1回分の試合の記録（N=30、q=0.55、2,000試合）
    _, a, b = sim_upset(rng, 30, 0.55, games=2000)
    pd.DataFrame({"game": np.arange(1, 2001), "points_A": a, "points_B": b}).to_csv(DATA / "games_N30_q055.csv",
                                                                                   index=False)
    out["one_draw_N30_q055"] = {"games": 2000, "B_win": int((b > a).sum()), "tie": int((a == b).sum()),
                                "A_mean": round(float(a.mean()), 2), "B_mean": round(float(b.mean()), 2)}

    json.dump(out, open(RES / "a836_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回あたりの差 q と、1試合の逆転の確率（N ごと）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    col = {10: ORANGE, 30: LIGHT, 100: BLUE, 300: INK}
    for n in NS:
        d = curve[curve.N == n]
        ax.plot(d.q, d.upset * 100, color=col[n], lw=2, label=f"点の機会 {n}回の試合")
    ax.axhline(10, color=GRAY, lw=1, ls="--"); ax.text(0.502, 10.6, "10%", color=GRAY, fontsize=9, ha="left")
    ax.set_xlabel("点の機会1回で、強いAが点を取る確率 q"); ax.set_ylabel("弱いBが勝つ確率（%）")
    ax.set_ylim(0, 52); ax.set_xlim(0.5, 0.7)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("1回あたりの差が同じでも、点の機会が多い試合ほど逆転は起きにくい")
    save(fig, "a836_chances.png", SRC)

    # 図2：シリーズの長さと逆転
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    scol = {1: ORANGE, 3: LIGHT, 5: GREEN, 7: BLUE, 11: INK}
    for g in [1, 3, 5, 7, 11]:
        d = ser[ser.games == g]
        ax.plot(d.p_win_one_game * 100, d.series_upset * 100, color=scol[g], lw=2,
                label="1試合だけ" if g == 1 else f"{g}試合で先に{g // 2 + 1}勝")
    ax.axhline(10, color=GRAY, lw=1, ls="--"); ax.text(50.4, 10.6, "10%", color=GRAY, fontsize=9, ha="left")
    ax.set_xlabel("1試合で強いAが勝つ確率（%）"); ax.set_ylabel("弱いBがシリーズを取る確率（%）")
    ax.set_xlim(50, 85); ax.set_ylim(0, 52)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("試合数を増やすと逆転は減るが、1試合の差が小さいと減り方はゆっくり")
    save(fig, "a836_series.png", SRC)

    # 図3：調子の波があると、点の機会を増やしても逆転は残る
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    fcol = {0.0: BLUE, 0.03: LIGHT, 0.06: ORANGE}
    x = np.arange(len(NS)); wd = 0.26
    for i, sd in enumerate([0.0, 0.03, 0.06]):
        d = form[form.form_sd == sd]
        ax.bar(x + (i - 1) * wd, d.upset_sim * 100, width=wd, color=fcol[sd],
               label="調子の波なし" if sd == 0 else f"調子の波あり（q が試合ごとに標準偏差{sd:.2f}で上下）")
        for xi, v in zip(x, d.upset_sim * 100):
            ax.text(xi + (i - 1) * wd, v + .6, f"{v:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(range(len(NS))); ax.set_xticklabels([f"{n}回" for n in NS])
    ax.set_xlabel("1試合の点の機会の数"); ax.set_ylabel("弱いBが勝つ確率（%）"); ax.set_ylim(0, 48)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("試合ごとに調子が上下すると、点の機会を増やしても逆転は残る（q=0.55）")
    save(fig, "a836_form.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
