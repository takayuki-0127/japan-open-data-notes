"""984 3つの扉のどれかを選び直すと、当たりやすくなるのか？（架空のデータ）

架空のゲーム。3つの扉の1つに景品があり、参加者が1つ選ぶ。司会者が残りの扉を1つ開けて見せ、
「選び直しますか」と聞く。司会者がどんな決まりで扉を開け、どんなときに選び直しを聞くかを作成者が置き、
選び直したとき・そのままのときに当たる割合を、乱数で作ったゲームで数える。式の値とも比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 984
SRC = "架空のゲーム（作成者が乱数で作成、seed 984）"
N = 1_000_000


def r4(x):
    return round(float(x), 4)


def base_games(rng, n=N):
    prize = rng.integers(0, 3, n)
    pick = rng.integers(0, 3, n)
    return prize, pick


def rule_always_goat(rng, n=N, q=0.5):
    """決まりA：司会者は必ず外れの扉を開け、必ず選び直しを聞く。
    外れが2つあるとき（参加者が当たりを選んでいるとき）は、番号の小さい扉を確率 q で開ける。"""
    prize, pick = base_games(rng, n)
    others = np.array([[1, 2], [0, 2], [0, 1]])[pick]          # 選ばれていない2つ（小さい順）
    lo, hi = others[:, 0], others[:, 1]
    both_goat = prize == pick
    take_lo = rng.random(n) < q
    opened = np.where(both_goat, np.where(take_lo, lo, hi), np.where(lo == prize, hi, lo))
    switch_to = 3 - pick - opened
    return prize, pick, opened, switch_to


def rule_random_open(rng, n=N):
    """決まりB：司会者は選ばれていない2つから、でたらめに1つ開ける（当たりが出たらその回は終わり）"""
    prize, pick = base_games(rng, n)
    others = np.array([[1, 2], [0, 2], [0, 1]])[pick]
    opened = others[np.arange(n), rng.integers(0, 2, n)]
    switch_to = 3 - pick - opened
    return prize, pick, opened, switch_to


def main():
    out = {}
    # --- 決まりA（q=0.5）---
    rng = np.random.default_rng(SEED)
    prize, pick, opened, sw = rule_always_goat(rng)
    stay_a, switch_a = (pick == prize).mean(), (sw == prize).mean()
    pd.DataFrame({"game_id": np.arange(1, 1001), "prize_door": prize[:1000] + 1, "pick_door": pick[:1000] + 1,
                  "opened_door": opened[:1000] + 1, "switch_door": sw[:1000] + 1,
                  "stay_win": (pick == prize)[:1000].astype(int), "switch_win": (sw == prize)[:1000].astype(int)}
                 ).to_csv(DATA / "games_rule_a.csv", index=False)

    # --- 決まりB ---
    rng = np.random.default_rng(SEED + 1)
    prizeb, pickb, openedb, swb = rule_random_open(rng)
    goat = openedb != prizeb
    stay_b, switch_b = (pickb == prizeb)[goat].mean(), (swb == prizeb)[goat].mean()
    ended_b = 1 - goat.mean()

    # --- 決まりC：外れが2つのとき、番号の小さい扉を好む（q）---
    rows_q = []
    for i, q in enumerate([0.5, 0.75, 0.9, 1.0]):
        rng = np.random.default_rng(SEED * 10 + i)
        pr, pk, op, s = rule_always_goat(rng, q=q)
        others = np.array([[1, 2], [0, 2], [0, 1]])[pk]
        opened_lo = op == others[:, 0]
        for lab, m, f in [("番号の小さい扉が開いた", opened_lo, 1 / (1 + q)),
                          ("番号の大きい扉が開いた", ~opened_lo, 1 / (2 - q))]:
            rows_q.append({"q": q, "case": lab, "share_of_games": r4(m.mean()),
                           "switch_win": r4((s == pr)[m].mean()), "formula": r4(f)})
        rows_q.append({"q": q, "case": "全部", "share_of_games": 1.0, "switch_win": r4((s == pr).mean()),
                       "formula": r4(2 / 3)})
    host_q = pd.DataFrame(rows_q)
    host_q.to_csv(RES / "host_pref_q.csv", index=False)

    # --- 決まりD：選び直しを聞く確率が、参加者が当てているかどうかで違う ---
    rows_d = []
    grid = [0, 0.25, 0.5, 0.75, 1.0]
    for i, r1 in enumerate(grid):          # 当てているときに聞く確率
        for j, r0 in enumerate(grid):      # 外しているときに聞く確率
            if r1 == 0 and r0 == 0:
                continue
            rng = np.random.default_rng(SEED * 100 + i * 10 + j)
            pr, pk, op, s = rule_always_goat(rng, n=200_000)
            correct = pk == pr
            offered = rng.random(len(pr)) < np.where(correct, r1, r0)
            rows_d.append({"offer_if_correct": r1, "offer_if_wrong": r0, "offered_share": r4(offered.mean()),
                           "switch_win_if_offered": r4((s == pr)[offered].mean()),
                           "formula": r4(2 * r0 / (2 * r0 + r1))})
    offer = pd.DataFrame(rows_d)
    offer.to_csv(RES / "offer_grid.csv", index=False)

    # --- 混ざった司会者：回のうち w は「当てた人にだけ聞く」、残りは決まりA ---
    rows_w = []
    for i, w in enumerate(np.round(np.arange(0, 1.01, 0.1), 1)):
        rng = np.random.default_rng(SEED * 1000 + i)
        pr, pk, op, s = rule_always_goat(rng, n=500_000)
        correct = pk == pr
        mean_host = rng.random(len(pr)) < w
        offered = np.where(mean_host, correct, True)
        rows_w.append({"w_mean_host": float(w), "switch_win_if_offered": r4((s == pr)[offered].mean()),
                       "stay_win_if_offered": r4((pk == pr)[offered].mean()),
                       "formula_switch": r4(2 * (1 - w) / (3 - 2 * w))})
    mix = pd.DataFrame(rows_w)
    mix.to_csv(RES / "mix_w.csv", index=False)

    # --- 扉の数 n：司会者が外れを n−2 枚開ける／1枚だけ開ける ---
    rows_n = []
    for i, n_d in enumerate([3, 4, 5, 10]):
        rng = np.random.default_rng(SEED * 7 + i)
        g = 500_000
        pr = rng.integers(0, n_d, g); pk = rng.integers(0, n_d, g)
        idx = np.arange(g)
        key = rng.random((g, n_d)); key[idx, pk] = 2; key[idx, pr] = 2
        op1 = key.argmin(1)                                # 司会者が開ける外れ（1枚）
        key2 = rng.random((g, n_d)); key2[idx, pk] = 2; key2[idx, op1] = 2
        sw1 = key2.argmin(1)                               # 残りからでたらめに選び直す
        rows_n.append({"doors": n_d, "stay_win": r4((pk == pr).mean()), "stay_formula": r4(1 / n_d),
                       "switch_win_open_all_but_one": r4((pk != pr).mean()),
                       "formula_all_but_one": r4((n_d - 1) / n_d),
                       "switch_win_open_one": r4((sw1 == pr).mean()),
                       "formula_open_one": r4((n_d - 1) / (n_d * (n_d - 2)))})
    ndoors = pd.DataFrame(rows_n)
    ndoors.to_csv(RES / "n_doors.csv", index=False)

    # --- 少ない回数の記録：決まりAで、毎回半々で選び直す・そのままを決めた記録 ---
    rows_s = []
    for i, m in enumerate([10, 30, 100, 300, 1000]):
        rng = np.random.default_rng(SEED * 3 + i)
        rec = 4000
        pr, pk, op, s = rule_always_goat(rng, n=rec * m)
        do_sw = rng.random(rec * m) < 0.5
        win = np.where(do_sw, s == pr, pk == pr).reshape(rec, m)
        do_sw = do_sw.reshape(rec, m)
        n_sw, n_st = do_sw.sum(1), (~do_sw).sum(1)
        ok = (n_sw > 0) & (n_st > 0)
        rate_sw = np.where(ok, (win & do_sw).sum(1) / np.maximum(n_sw, 1), np.nan)
        rate_st = np.where(ok, (win & ~do_sw).sum(1) / np.maximum(n_st, 1), np.nan)
        rows_s.append({"games": m, "records": rec, "records_with_both": int(ok.sum()),
                       "share_switch_not_better": r4((rate_sw[ok] <= rate_st[ok]).mean()),
                       "share_switch_lower": r4((rate_sw[ok] < rate_st[ok]).mean()),
                       "switch_rate_p10": r4(np.nanquantile(rate_sw, .1)),
                       "switch_rate_p90": r4(np.nanquantile(rate_sw, .9))})
    small = pd.DataFrame(rows_s)
    small.to_csv(RES / "small_record.csv", index=False)

    rules = pd.DataFrame([
        {"rule": "A 必ず外れを開け、必ず聞く", "stay_win": r4(stay_a), "switch_win": r4(switch_a),
         "switch_formula": r4(2 / 3), "note": "全部の回"},
        {"rule": "B でたらめに開け、外れが出た回", "stay_win": r4(stay_b), "switch_win": r4(switch_b),
         "switch_formula": 0.5, "note": f"当たりが開いて終わった回 {ended_b:.4f} を除く"},
        {"rule": "C 小さい番号を必ず開ける決まりで、小さい番号が開いた回", "stay_win": r4(1 - host_q.query("q==1.0 and case=='番号の小さい扉が開いた'").switch_win.iloc[0]),
         "switch_win": host_q.query("q==1.0 and case=='番号の小さい扉が開いた'").switch_win.iloc[0],
         "switch_formula": 0.5, "note": "q=1"},
        {"rule": "C 同じ決まりで、大きい番号が開いた回", "stay_win": r4(1 - host_q.query("q==1.0 and case=='番号の大きい扉が開いた'").switch_win.iloc[0]),
         "switch_win": host_q.query("q==1.0 and case=='番号の大きい扉が開いた'").switch_win.iloc[0],
         "switch_formula": 1.0, "note": "q=1"},
        {"rule": "D 当てた人にだけ聞く", "stay_win": r4(1 - offer.query("offer_if_correct==1.0 and offer_if_wrong==0").switch_win_if_offered.iloc[0]),
         "switch_win": offer.query("offer_if_correct==1.0 and offer_if_wrong==0").switch_win_if_offered.iloc[0],
         "switch_formula": 0.0, "note": "聞かれた回"},
        {"rule": "D 外した人にだけ聞く", "stay_win": r4(1 - offer.query("offer_if_correct==0 and offer_if_wrong==1.0").switch_win_if_offered.iloc[0]),
         "switch_win": offer.query("offer_if_correct==0 and offer_if_wrong==1.0").switch_win_if_offered.iloc[0],
         "switch_formula": 1.0, "note": "聞かれた回"},
    ])
    rules.to_csv(RES / "rules.csv", index=False)

    out = {"n_games_per_rule": N,
           "rule_a": {"stay_win": r4(stay_a), "switch_win": r4(switch_a), "formula": r4(2 / 3)},
           "rule_b": {"stay_win": r4(stay_b), "switch_win": r4(switch_b), "ended_share": r4(ended_b),
                      "formula": 0.5},
           "rules": rules.to_dict("records"),
           "host_pref_q": host_q.to_dict("records"),
           "offer_grid": {"switch_win_min": float(offer.switch_win_if_offered.min()),
                          "switch_win_max": float(offer.switch_win_if_offered.max()),
                          "max_abs_diff_from_formula": r4((offer.switch_win_if_offered - offer.formula).abs().max()),
                          "n_cases": int(len(offer)),
                          "n_switch_better_formula": int((offer.formula > 0.5 + 1e-9).sum()),
                          "n_equal_formula": int(((offer.formula - 0.5).abs() < 1e-9).sum()),
                          "n_switch_worse_formula": int((offer.formula < 0.5 - 1e-9).sum())},
           "mix_w": mix.to_dict("records"),
           "n_doors": ndoors.to_dict("records"),
           "small_record": small.to_dict("records"),
           "max_abs_diff_from_formula_all": r4(max(
               abs(switch_a - 2 / 3), abs(switch_b - 0.5),
               (host_q.switch_win - host_q.formula).abs().max(),
               (offer.switch_win_if_offered - offer.formula).abs().max(),
               (mix.switch_win_if_offered - mix.formula_switch).abs().max(),
               (ndoors.switch_win_open_all_but_one - ndoors.formula_all_but_one).abs().max(),
               (ndoors.switch_win_open_one - ndoors.formula_open_one).abs().max()))}
    json.dump(out, open(RES / "a984_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：司会者の決まりごとの、選び直したときの当たり
    lab = ["A 必ず外れを開け、\n必ず聞く", "B でたらめに開け、\n外れが出た回", "C 小さい番号を必ず開ける\n決まりで、小さい番号が開いた",
           "C 同じ決まりで、\n大きい番号が開いた", "D 当てた人に\nだけ聞く", "D 外した人に\nだけ聞く"]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    v = rules.switch_win.values * 100
    y = np.arange(len(v))[::-1]
    ax.barh(y, v, color=[BLUE, GRAY, GRAY, GRAY, ORANGE, GRAY], height=.6)
    ax.barh(y, rules.stay_win.values * 100, color="none", edgecolor=INK, height=.6, lw=.8, ls=":")
    for yy, vv in zip(y, v):
        ax.text(min(vv, 88) + 1.5, yy, f"{vv:.1f}%", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=8.5)
    ax.set_xlim(0, 105); ax.set_xlabel("選び直したときに当たった割合（%、色の棒）。点線の枠はそのままのとき")
    ax.set_title("同じ「外れを1つ見せてから選び直す」でも、司会者の決まりで0〜100%")
    save(fig, "a984_rules.png", SRC)

    # 図2：混ざった司会者
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(mix.w_mean_host * 100, mix.switch_win_if_offered * 100, "o-", color=BLUE, label="選び直す")
    ax.plot(mix.w_mean_host * 100, mix.stay_win_if_offered * 100, "o-", color=ORANGE, label="そのまま")
    ax.axhline(50, color=GRAY, lw=.8, ls="--")
    ax.set_xlabel("回のうち、司会者が「当てた人にだけ聞く」回の割合（%）")
    ax.set_ylabel("聞かれた回で当たった割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False)
    ax.set_title("「当てた人にだけ聞く」回が半分あると、選び直しの得はなくなる")
    save(fig, "a984_mixed_host.png", SRC)

    # 図3：少ない記録
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xs = np.arange(len(small))
    ax.bar(xs, small.share_switch_not_better * 100, color=BLUE, width=.6)
    for x, vv in zip(xs, small.share_switch_not_better * 100):
        ax.text(x, vv + 0.4, f"{vv:.2f}%", ha="center", fontsize=9)
    ax.set_ylim(0, small.share_switch_not_better.max() * 100 * 1.2)
    ax.set_xticks(xs); ax.set_xticklabels([f"{m:,}回" for m in small.games])
    ax.set_xlabel("記録のゲームの回数（決まりA、毎回半々で選び直すかを決めた）")
    ax.set_ylabel("得が見えなかった記録（%）")
    ax.set_title(f"10回の記録では{small.share_switch_not_better.iloc[0]*100:.2f}%で、選び直しの得が見えなかった\n（選び直した回の当たりが、そのままの回の当たり以下）", fontsize=11.5)
    save(fig, "a984_small_record.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
