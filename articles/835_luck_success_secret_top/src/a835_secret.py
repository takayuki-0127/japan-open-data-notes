"""835 上位だけを見て「成功の秘訣」を決めると、何を読み違えるのか？（架空のデータ）

架空の営業担当1,000人。年間の成績＝100＋実力＋運。3割の人は「大きな案件を狙うやり方」（以下、大口狙い）で、
平均は同じだが運の振れが大きい（基本1.6倍）。上位20人だけを見ると、大口狙いの割合はどう見えるか、
下位や全員と比べると何が分かるかを数える。あわせて、成績と関係のない20個の習慣を上位20人で調べ、
「いちばん差の大きい習慣」が翌年の上位20人でも差を保つかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 835
SRC = "架空の営業担当の成績（作成者が乱数で作成、seed 835）"
rng = np.random.default_rng(SEED)
N = 1000
TOP = 20
SD_SKILL, SD_LUCK = 8.0, 12.0
SHARE_BIG = 0.3
N_TRAIT = 20
REPS = 200


def make_people(rng, n=N, ratio=1.6, effect=0.0, share=SHARE_BIG):
    """1年目・2年目の成績。大口狙いは運の振れが ratio 倍、平均が effect だけ違う。習慣は成績と無関係。"""
    big = rng.random(n) < share
    skill = rng.normal(0, SD_SKILL, n)
    k = np.where(big, ratio, 1.0)
    y1 = 100 + skill + effect * big + rng.normal(0, SD_LUCK, n) * k
    y2 = 100 + skill + effect * big + rng.normal(0, SD_LUCK, n) * k
    traits = rng.random((n, N_TRAIT)) < 0.5
    return big, skill, y1, y2, traits


def groups(y, big):
    """成績の順に並べた各グループでの大口狙いの割合"""
    o = np.argsort(-y)
    n = len(y)
    return {"上位20人": big[o[:20]].mean(), "上位100人": big[o[:100]].mean(), "全員": big.mean(),
            "下位100人": big[o[n - 100:]].mean(), "下位20人": big[o[n - 20:]].mean()}


def main():
    out = {}

    # 1回分（data）
    big, skill, y1, y2, traits = make_people(rng)
    df = pd.DataFrame({"person_id": np.arange(1, N + 1), "big_deal_style": big.astype(int),
                       "skill": skill.round(2), "score_y1": y1.round(2), "score_y2": y2.round(2)})
    for j in range(N_TRAIT):
        df[f"habit{j + 1:02d}"] = traits[:, j].astype(int)
    df.to_csv(DATA / "sales_people.csv", index=False)
    o = np.argsort(-y1)
    out["one_draw"] = {"share_big_top20": round(float(big[o[:TOP]].mean()), 3),
                       "share_big_all": round(float(big.mean()), 3),
                       "share_big_bottom20": round(float(big[o[-TOP:]].mean()), 3),
                       "mean_big": round(float(y1[big].mean()), 2), "mean_normal": round(float(y1[~big].mean()), 2),
                       "sd_big": round(float(y1[big].std()), 2), "sd_normal": round(float(y1[~big].std()), 2),
                       "top20_cut": round(float(np.sort(y1)[-TOP]), 2)}

    # 2) 大口狙いの割合：グループごと（200回の平均）、両方のやり方の平均の差
    g_rows, mdiff, top_y2 = [], [], []
    for r in range(REPS):
        b, s, a1, a2, _ = make_people(np.random.default_rng(SEED * 1000 + r))
        g_rows.append(groups(a1, b))
        mdiff.append(a1[b].mean() - a1[~b].mean())
        top_y2.append(b[np.argsort(-a2)[:TOP]].mean())
    gm = pd.DataFrame(g_rows).mean().round(3)
    out["share_big_by_group_200reps"] = gm.to_dict()
    out["mean_diff_big_minus_normal_200reps"] = round(float(np.mean(mdiff)), 2)
    out["share_big_top20_year2_200reps"] = round(float(np.mean(top_y2)), 3)
    gm.rename("share_big").to_csv(RES / "share_by_group.csv")

    # 3) 確かめ：運の振れの倍率 ratio と、平均の差 effect を変える（上位20人・下位20人の大口狙いの割合）
    rows = []
    for ratio in [1.0, 1.3, 1.6, 2.0]:
        for eff in [-5.0, 0.0, 5.0]:
            t, bt, md = [], [], []
            for r in range(REPS):
                b, s, a1, a2, _ = make_people(np.random.default_rng(SEED * 7 + r + int(ratio * 100) * 10 + int(eff + 10)),
                                              ratio=ratio, effect=eff)
                oo = np.argsort(-a1)
                t.append(b[oo[:TOP]].mean()); bt.append(b[oo[-TOP:]].mean()); md.append(a1[b].mean() - a1[~b].mean())
            rows.append({"ratio": ratio, "effect": eff, "share_big_top20": round(float(np.mean(t)), 3),
                         "share_big_bottom20": round(float(np.mean(bt)), 3), "mean_diff": round(float(np.mean(md)), 2)})
    sens = pd.DataFrame(rows)
    sens.to_csv(RES / "sensitivity_ratio_effect.csv", index=False)
    out["sensitivity"] = rows

    # 3b) 上位の切り方（上位10人・20人・50人・100人）で、大口狙いの割合（基本の置き方）
    cut = {}
    for k in [10, 20, 50, 100]:
        v = []
        for r in range(REPS):
            b, s, a1, a2, _ = make_people(np.random.default_rng(SEED * 1000 + r))
            v.append(b[np.argsort(-a1)[:k]].mean())
        cut[str(k)] = round(float(np.mean(v)), 3)
    out["share_big_by_topk"] = cut

    # 4) 成績と関係のない20個の習慣：上位20人で差がいちばん大きい習慣と、その翌年
    best1, best2, best_any = [], [], []
    for r in range(REPS):
        b, s, a1, a2, tr = make_people(np.random.default_rng(SEED * 3000 + r))
        base = tr.mean(0)
        top1 = tr[np.argsort(-a1)[:TOP]].mean(0)
        top2 = tr[np.argsort(-a2)[:TOP]].mean(0)
        j = int(np.argmax(top1 - base))
        best1.append(top1[j] - base[j]); best2.append(top2[j] - base[j])
        best_any.append(top1[j] - base[j] >= 0.2)
    out["habits_20"] = {"best_habit_gap_year1_pt": round(float(np.mean(best1)) * 100, 1),
                        "same_habit_gap_year2_pt": round(float(np.mean(best2)) * 100, 1),
                        "share_reps_best_gap_ge_20pt": round(float(np.mean(best_any)), 3)}
    pd.DataFrame({"rep": range(REPS), "gap_year1": np.round(best1, 3), "gap_year2": np.round(best2, 3)}).to_csv(
        RES / "habits_best_gap.csv", index=False)

    # 1回分の習慣の差（図用）
    base = traits.mean(0); t1 = traits[o[:TOP]].mean(0); t2 = traits[np.argsort(-y2)[:TOP]].mean(0)
    jb = int(np.argmax(t1 - base))
    out["one_draw_habits"] = {"best_habit": f"habit{jb + 1:02d}", "share_all": round(float(base[jb]), 3),
                              "share_top20_y1": round(float(t1[jb]), 3), "share_top20_y2": round(float(t2[jb]), 3)}

    json.dump(out, open(RES / "a835_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：グループごとの大口狙いの割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    labs = list(gm.index)
    col = [ORANGE, LIGHT, GRAY, LIGHT, ORANGE]
    ax.bar(labs, gm.values * 100, color=col, width=.6)
    for i, v in enumerate(gm.values * 100):
        ax.text(i, v + 1.2, f"{v:.0f}%", ha="center", fontsize=10)
    ax.set_ylim(0, 90); ax.set_ylabel("大口狙いの人の割合（%）")
    ax.set_title("上位20人の大口狙いは多い。でも下位20人にも同じくらい多い（200回の平均）")
    save(fig, "a835_groups.png", SRC)

    # 図2：成績の分布（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.linspace(min(y1) - 1, max(y1) + 1, 45)
    ax.hist(y1[~big], bins=bins, color=BLUE, alpha=.6, label=f"ふつうのやり方（{(~big).sum()}人）")
    ax.hist(y1[big], bins=bins, color=ORANGE, alpha=.6, label=f"大口狙い（{big.sum()}人）")
    c = out["one_draw"]["top20_cut"]
    ax.axvline(c, color=INK, lw=1, ls="--")
    ax.text(c + 1, ax.get_ylim()[1] * .9, "上位20人の線", fontsize=9)
    ax.set_xlabel("1年目の成績（全員の平均100）"); ax.set_ylabel("人数")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("平均は同じでも、振れの大きいやり方は上にも下にもはみ出す（1回分）")
    save(fig, "a835_dist.png", SRC)

    # 図3：関係のない習慣の「差」は翌年に消える
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    b1, b2 = np.array(best1) * 100, np.array(best2) * 100
    bins = np.arange(-50, 52.5, 5)
    ax.hist(b1, bins=bins, color=ORANGE, alpha=.65, label=f"1年目（選んだ年）平均 {np.mean(b1):+.1f}ポイント")
    ax.hist(b2, bins=bins, color=BLUE, alpha=.6, label=f"2年目（確かめ直し）平均 {np.mean(b2):+.1f}ポイント")
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_xlabel("上位20人での習慣の割合 − 全員での割合（ポイント）"); ax.set_ylabel("回数（200回中）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("関係のない20個の習慣から「いちばん上位に多い習慣」を選ぶと（200回）")
    save(fig, "a835_habits.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
