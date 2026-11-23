"""1001 招待券で増えた人数は、次の回も来るのか？（架空のデータ）

架空の催し（年2回の市、春の回と秋の回）。名簿の6万人に「関心の強さ」z（標準正規分布）を作成者が置く。
春の回に有料で来る確率は logistic(A + B*z)。名簿からでたらめに選んだ5,000人に招待券を配ると、
招待された人の来る確率は logistic(A + C + B*z) に上がる（招待がなくても来た人は、招待されても来る）。
秋の回（招待券なし）に来る確率は logistic(A + B*z + H*春に来たか)。H は「一度来ると次も来やすくなる」効き目。
同じ乱数で「招待券を配った世界」と「配らなかった世界」を作り、招待のおかげで増えた人数（本当の値）を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1001
SRC = "架空の催しの名簿と来場（作成者が乱数で作成、seed 1001）"
N, N_INV = 60000, 5000
A, B = -2.8, 1.2
BASE = {"C": 2.0, "H": 0.5, "target": "でたらめ"}


def sig(x):
    return 1 / (1 + np.exp(-x))


def run(rng, C=2.0, H=0.5, target="でたらめ", keep=False):
    z = rng.normal(size=N)
    u1, u2 = rng.uniform(size=N), rng.uniform(size=N)
    # 名簿から1万人を選び（でたらめ、または関心の強い人ほど選ばれやすく）、でたらめに半分ずつ
    # 「招待券を配る5,000人」と「比べる相手（配らない）5,000人」に分ける
    if target == "でたらめ":
        pick = rng.choice(N, 2 * N_INV, replace=False)
    else:  # 関心の強い人ほど選ばれやすい名簿（前に来た人の名簿などを思い描いたもの）
        w = sig(B * z); pick = rng.choice(N, 2 * N_INV, replace=False, p=w / w.sum())
    pick = rng.permutation(pick)
    inv = np.zeros(N, bool); inv[pick[:N_INV]] = True
    ctrl = np.zeros(N, bool); ctrl[pick[N_INV:]] = True

    p_paid = sig(A + B * z)
    p_inv = sig(A + C + B * z)
    att1_no = u1 < p_paid                         # 配らなかった世界
    att1 = np.where(inv, u1 < p_inv, att1_no)     # 配った世界
    att2_no = u2 < sig(A + B * z + H * att1_no)
    att2 = u2 < sig(A + B * z + H * att1)

    by_inv = inv & att1                     # 招待券で来た人
    anyway = inv & att1_no                  # そのうち招待がなくても来た人
    extra = inv & att1 & ~att1_no           # 招待で増えた人
    paid = ~inv & att1                      # 有料で来た人
    r = {
        "invite_used": int(by_inv.sum()),
        "would_come_anyway": int(anyway.sum()),
        "true_extra_round1": int(att1.sum() - att1_no.sum()),
        "paid_visitors": int(paid.sum()),
        "rate2_paid_pct": 100 * att2[paid].mean(),
        "rate2_invite_pct": 100 * att2[by_inv].mean(),
        "rate2_extra_pct": 100 * att2[extra].mean(),
        "rate2_anyway_pct": 100 * att2[anyway].mean(),
        "rate2_extra_without_pct": 100 * att2_no[extra].mean(),   # 招待で増えた人が、春に来なかった世界で秋に来た割合
        "invite_back_round2": int((by_inv & att2).sum()),
        "true_extra_round2": int(att2.sum() - att2_no.sum()),
        # 招待した5,000人と、同じ選び方の招待しなかった5,000人の秋の回の来場の差
        "ctrl_estimate_round2": int(att2[inv].sum() - att2[ctrl].sum()),
        "ctrl_estimate_round1": int(att1[inv].sum() - att1[ctrl].sum()),
    }
    r["naive_forecast_round2"] = r["invite_used"] * r["rate2_paid_pct"] / 100     # 招待券の来場×有料の人の再来率
    r["naive_forecast2_round2"] = r["true_extra_round1"] * r["rate2_paid_pct"] / 100
    r["keep_ratio_pct"] = 100 * r["true_extra_round2"] / r["true_extra_round1"]
    if keep:
        ticket = np.where(~att1, "来ない", np.where(inv, "招待券", "有料"))
        r["_df"] = pd.DataFrame({"person_id": np.arange(1, N + 1), "interest": z.round(4), "invited": inv.astype(int),
                                 "control": ctrl.astype(int), "spring": ticket,
                                 "spring_without_invite": att1_no.astype(int), "autumn": att2.astype(int),
                                 "autumn_without_invite": att2_no.astype(int)})
    return r


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    m = run(rng, keep=True)
    df = m.pop("_df")
    df[(df.invited == 1) | (df.control == 1)].to_csv(DATA / "invited_and_control.csv", index=False)
    main_r = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()}

    # 200回くり返し（名簿を作り直す）
    reps = pd.DataFrame([run(np.random.default_rng(SEED * 1000 + i)) for i in range(200)])
    reps_s = {"true_extra_round1_mean": round(reps.true_extra_round1.mean(), 1),
              "true_extra_round2_mean": round(reps.true_extra_round2.mean(), 1),
              "keep_ratio_pct_mean": round(reps.keep_ratio_pct.mean(), 2),
              "keep_ratio_pct_p10_p90": [round(float(np.percentile(reps.keep_ratio_pct, 10)), 2),
                                         round(float(np.percentile(reps.keep_ratio_pct, 90)), 2)],
              "ctrl_estimate_round2_mean": round(reps.ctrl_estimate_round2.mean(), 1),
              "ctrl_estimate_round2_p10_p90": [round(float(np.percentile(reps.ctrl_estimate_round2, 10)), 1),
                                               round(float(np.percentile(reps.ctrl_estimate_round2, 90)), 1)],
              "ctrl_estimate_round1_mean": round(reps.ctrl_estimate_round1.mean(), 1),
              "invite_back_round2_mean": round(reps.invite_back_round2.mean(), 1),
              "naive_forecast_round2_mean": round(reps.naive_forecast_round2.mean(), 1),
              "rate2_paid_pct_mean": round(reps.rate2_paid_pct.mean(), 2),
              "rate2_invite_pct_mean": round(reps.rate2_invite_pct.mean(), 2),
              "rate2_anyway_pct_mean": round(reps.rate2_anyway_pct.mean(), 2),
              "rate2_extra_pct_mean": round(reps.rate2_extra_pct.mean(), 2),
              "rate2_extra_without_pct_mean": round(reps.rate2_extra_without_pct.mean(), 2)}
    reps.round(3).to_csv(RES / "reps_base.csv", index=False)

    # 確かめ：招待の効き目 C、一度来た効き目 H、配り方（24通り、各40回）
    grid = []
    for target in ["でたらめ", "関心の強い人に寄る"]:
        for C in [1.0, 2.0, 3.0]:
            for H in [0.0, 0.25, 0.5, 1.0]:
                g = pd.DataFrame([run(np.random.default_rng(SEED * 100000 + 10000 * int(C) + 1000 * int(H * 4) + (500 if target != "でたらめ" else 0) + i),
                                      C=C, H=H, target=target) for i in range(40)])
                grid.append({"target": target, "C": C, "H": H,
                             "invite_used": round(g.invite_used.mean(), 1),
                             "anyway_share_pct": round(100 * (g.would_come_anyway / g.invite_used).mean(), 2),
                             "true_extra_round1": round(g.true_extra_round1.mean(), 1),
                             "invite_back_round2": round(g.invite_back_round2.mean(), 1),
                             "naive_forecast_round2": round(g.naive_forecast_round2.mean(), 1),
                             "true_extra_round2": round(g.true_extra_round2.mean(), 1),
                             "keep_ratio_pct": round(100 * g.true_extra_round2.mean() / g.true_extra_round1.mean(), 2),
                             "ctrl_estimate_round2": round(g.ctrl_estimate_round2.mean(), 1) + 0.0,
                             "rate2_paid_pct": round(g.rate2_paid_pct.mean(), 2),
                             "rate2_extra_pct": round(g.rate2_extra_pct.mean(), 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_c_h_target.csv", index=False)
    gpos = grid[grid.H > 0]
    out = {"setting": {"N": N, "invited": N_INV, "A": A, "B": B, **BASE},
           "main": main_r, "reps200": reps_s, "grid": grid.to_dict("records"),
           "grid_range": {"keep_ratio_pct_all": [float(grid.keep_ratio_pct.min()), float(grid.keep_ratio_pct.max())],
                          "keep_ratio_pct_H_pos": [float(gpos.keep_ratio_pct.min()), float(gpos.keep_ratio_pct.max())],
                          "ctrl_minus_true_round2": [round(float((grid.ctrl_estimate_round2 - grid.true_extra_round2).min()), 1),
                                                     round(float((grid.ctrl_estimate_round2 - grid.true_extra_round2).max()), 1)],
                          "anyway_share_pct": [float(grid.anyway_share_pct.min()), float(grid.anyway_share_pct.max())],
                          "naive_over_true_round2_H_pos": [round(float((gpos.naive_forecast_round2 / gpos.true_extra_round2).min()), 2),
                                                           round(float((gpos.naive_forecast_round2 / gpos.true_extra_round2).max()), 2)],
                          "back_over_true_round2_H_pos": [round(float((gpos.invite_back_round2 / gpos.true_extra_round2).min()), 2),
                                                          round(float((gpos.invite_back_round2 / gpos.true_extra_round2).max()), 2)]}}
    out["main"]["anyway_share_pct"] = round(100 * m["would_come_anyway"] / m["invite_used"], 2)
    out["main"]["naive_over_true_round2"] = round(m["naive_forecast_round2"] / m["true_extra_round2"], 2)
    out["main"]["back_over_true_round2"] = round(m["invite_back_round2"] / m["true_extra_round2"], 2)
    json.dump(out, open(RES / "a1001_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：招待券で来た人の内訳と、秋の回
    mm = out["main"]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    labels = ["春の回：\n招待券で来た人", "春の回：\n招待で増えた人", "秋の回：\n招待券で来た人のうち\nまた来た人",
              "秋の回：\n有料の人と同じ割合で\n戻ると見込んだ人数", "秋の回：\n招待のおかげで\n増えた人（本当）"]
    vals = [mm["invite_used"], mm["true_extra_round1"], mm["invite_back_round2"], mm["naive_forecast_round2"], mm["true_extra_round2"]]
    cols = [LIGHT, BLUE, LIGHT, GRAY, ORANGE]
    ax.bar(range(5), vals, color=cols, width=0.62)
    for i, v in enumerate(vals):
        ax.text(i, v + 25, f"{v:,.0f}人", ha="center", fontsize=9.5)
    ax.set_xticks(range(5)); ax.set_xticklabels(labels, fontsize=8.3)
    ax.set_ylabel("人数"); ax.set_ylim(0, max(vals) * 1.15)
    ax.set_title("招待券5,000枚を配った架空の催し：春に増えた人と、秋に残った人")
    save(fig, "a1001_flow.png", SRC)

    # 図2：秋の回に来た割合（グループ別）
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    gl = ["有料で来た人", "招待券で来た人（全体）", "うち招待がなくても来た人", "うち招待で増えた人"]
    rs = out["reps200"]
    gv = [rs["rate2_paid_pct_mean"], rs["rate2_invite_pct_mean"], rs["rate2_anyway_pct_mean"], rs["rate2_extra_pct_mean"]]
    ax.barh(range(4)[::-1], gv, color=[GRAY, LIGHT, BLUE, ORANGE], height=0.6)
    for i, v in zip(range(4)[::-1], gv):
        ax.text(v + 0.6, i, f"{v:.1f}%", va="center", fontsize=9.5)
    ax.set_yticks(range(4)[::-1]); ax.set_yticklabels(gl)
    ax.set_xlabel("秋の回にも来た割合（%）"); ax.set_xlim(0, max(gv) * 1.2)
    ax.set_title("春に来た人が秋の回にも来た割合（招待券は秋にはなし、200回の平均）", fontsize=12)
    save(fig, "a1001_rates.png", SRC)

    # 図3：秋に残った割合（秋に増えた人÷春に増えた人）の置き方による動き
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.6), sharey=True)
    vmax = grid.keep_ratio_pct.max() * 1.15
    for ax, tg in zip(axes, ["でたらめ", "関心の強い人に寄る"]):
        piv = grid[grid.target == tg].pivot(index="C", columns="H", values="keep_ratio_pct")
        ax.imshow(piv.values, cmap="Blues", aspect="auto", vmin=0, vmax=vmax)
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                v = piv.values[i, j]
                ax.text(j, i, f"{v:.1f}%", ha="center", va="center", fontsize=9.5, color="white" if v > vmax * 0.6 else INK)
        ax.set_xticks(range(piv.shape[1])); ax.set_xticklabels([f"{h:g}" for h in piv.columns])
        ax.set_yticks(range(piv.shape[0])); ax.set_yticklabels([f"{c:g}" for c in piv.index])
        ax.set_xlabel("一度来た効き目 H"); ax.set_title(f"配り方：{tg}", fontsize=11)
        ax.spines["left"].set_visible(False); ax.spines["bottom"].set_visible(False)
    axes[0].set_ylabel("招待の効き目 C")
    fig.suptitle("秋の回に増えた人は、春に増えた人の何%か（各40回の平均）", fontsize=12.5, y=1.02)
    save(fig, "a1001_grid.png", SRC)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps({k: out[k] for k in ["main", "reps200", "grid_range", "run_sec"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
