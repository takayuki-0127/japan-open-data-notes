"""872 前年と質問文を変えた年の比較は、どこまでできるのか？（架空のデータ）

架空の会社の社員アンケート（8部署×300人）。社員ごとの「本当の気持ち」（見えない値）を作成者が置き、
5段階の答えは気持ちが区切りを超えたかで決まる。2年目に質問文を変え、言い回しが厳しくなった分だけ
気持ちが低く出る（言い回しのずれ）と置く。本当の変化（前年と同じ質問文で聞いたら出たはずの変化）と比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 872
SRC = "架空の会社の社員アンケート（作成者が乱数で作成、seed 872）"
N_DEPT, PER_DEPT, RESP_RATE = 8, 300, 0.70
CUTS = np.array([-1.5, -0.6, 0.2, 1.0])   # 5段階の区切り。0.2を超えると「4以上（満足）」
DEPT_SD, CHANGE, CHANGE_SD, PERSON_SD = 0.30, 0.10, 0.15, 0.30
WORD, WORD_SD = -0.30, 0.0                 # 新しい質問文の言い回しのずれ（全部署共通）と、部署ごとの違い
REPS = 1000


def answer(lat):
    return 1 + (lat[:, None] > CUTS[None, :]).sum(1)


def make_company(rng, change=CHANGE, word=WORD, word_sd=WORD_SD):
    dept = np.repeat(np.arange(N_DEPT), PER_DEPT)
    m = rng.normal(0, DEPT_SD, N_DEPT)
    c = change + rng.normal(0, CHANGE_SD, N_DEPT)        # 部署ごとの本当の変化（気持ちの単位）
    u = word + rng.normal(0, word_sd, N_DEPT)            # 部署ごとの言い回しのずれ
    z1 = m[dept] + rng.normal(0, 1, len(dept))
    z2 = z1 + c[dept] + rng.normal(0, PERSON_SD, len(dept))
    return dept, z1, z2, u


def one_rep(rng, change=CHANGE, word=WORD, word_sd=WORD_SD):
    dept, z1, z2, u = make_company(rng, change, word, word_sd)
    n = len(dept)
    sat1_old = answer(z1) >= 4
    sat2_old = answer(z2) >= 4                     # 前年と同じ質問文なら（本当）
    sat2_new = answer(z2 + u[dept]) >= 4           # 新しい質問文
    r1 = rng.random(n) < RESP_RATE
    r2 = rng.random(n) < RESP_RATE
    half = rng.random(n) < 0.5                     # 2年目に半分ずつ聞き分ける場合（True=前年の質問文）
    true_change = (sat2_old.mean() - sat1_old.mean()) * 100
    y1 = sat1_old[r1].mean()
    naive = (sat2_new[r2].mean() - y1) * 100
    split = (sat2_old[r2 & half].mean() - y1) * 100
    word_est = (sat2_new[r2 & ~half].mean() - sat2_old[r2 & half].mean()) * 100
    word_true = (sat2_new.mean() - sat2_old.mean()) * 100
    # 部署ごと
    d1 = np.array([sat1_old[r1 & (dept == k)].mean() for k in range(N_DEPT)])
    d2n = np.array([sat2_new[r2 & (dept == k)].mean() for k in range(N_DEPT)])
    d2o_resp = np.array([sat2_old[r2 & (dept == k)].mean() for k in range(N_DEPT)])
    t1 = np.array([sat1_old[dept == k].mean() for k in range(N_DEPT)])
    t2 = np.array([sat2_old[dept == k].mean() for k in range(N_DEPT)])
    return {"true_change": true_change, "naive": naive, "split": split, "word_est": word_est, "word_true": word_true,
            "rank_within_new": spearmanr(d2n, t2)[0],               # 2年目の部署の順位（新しい質問文）
            "rank_within_same": spearmanr(d2o_resp, t2)[0],         # 同じ質問文なら（回答者の数による揺れだけ）
            "rank_change_naive": spearmanr(d2n - d1, t2 - t1)[0],   # 部署の伸びの順位（質問文を変えたまま）
            "rank_change_same": spearmanr(d2o_resp - d1, t2 - t1)[0],
            "dept_naive_down": float((d2n - d1 < 0).mean()), "dept_true_down": float((t2 - t1 < 0).mean())}


def main():
    rng = np.random.default_rng(SEED)

    # 1回分（data/employees.csv）
    dept, z1, z2, u = make_company(rng)
    n = len(dept)
    r1, r2, half = rng.random(n) < RESP_RATE, rng.random(n) < RESP_RATE, rng.random(n) < 0.5
    df = pd.DataFrame({"emp_id": np.arange(1, n + 1), "dept": np.array(list("ABCDEFGH"))[dept],
                       "y1_answer_old": answer(z1), "y2_answer_old": answer(z2), "y2_answer_new": answer(z2 + u[dept]),
                       "y1_responded": r1.astype(int), "y2_responded": r2.astype(int), "y2_split_old_half": half.astype(int)})
    df.to_csv(DATA / "employees.csv", index=False)
    one = {"true_y1_sat": round(float((df.y1_answer_old >= 4).mean()), 4),
           "true_y2_sat_old": round(float((df.y2_answer_old >= 4).mean()), 4),
           "y1_sat_resp": round(float((df[df.y1_responded == 1].y1_answer_old >= 4).mean()), 4),
           "y2_sat_new_resp": round(float((df[df.y2_responded == 1].y2_answer_new >= 4).mean()), 4)}

    # 2) 基本の置き方で1,000回
    sim = pd.DataFrame([one_rep(np.random.default_rng(SEED * 1000 + r)) for r in range(REPS)])
    q = lambda col, p: round(float(sim[col].quantile(p)), 2)
    main_res = {k: round(float(sim[k].mean()), 3) for k in sim.columns}
    for col in ["true_change", "naive", "split", "word_est"]:
        main_res[col + "_p05"], main_res[col + "_p95"] = q(col, .05), q(col, .95)
    main_res["naive_negative"] = round(float((sim.naive < 0).mean()), 3)
    main_res["split_negative"] = round(float((sim.split < 0).mean()), 3)
    main_res["true_negative"] = round(float((sim.true_change < 0).mean()), 3)
    sim.round(4).to_csv(RES / "reps_base.csv", index=False)

    # 3) 確かめ：言い回しのずれの大きさ × 部署ごとの違い（各300回）
    sens = []
    for w in [0.0, -0.1, -0.3, -0.5]:
        for wsd in [0.0, 0.15, 0.3]:
            s = pd.DataFrame([one_rep(np.random.default_rng(SEED * 77 + r + int(-w * 10) * 1000 + int(wsd * 100) * 100000),
                                      CHANGE, w, wsd) for r in range(300)])
            sens.append({"word": w, "word_sd": wsd, "true_change": round(float(s.true_change.mean()), 2),
                         "naive": round(float(s.naive.mean()), 2), "naive_negative": round(float((s.naive < 0).mean()), 3),
                         "rank_within_new": round(float(s.rank_within_new.mean()), 3),
                         "rank_change_naive": round(float(s.rank_change_naive.mean()), 3),
                         "rank_change_same": round(float(s.rank_change_same.mean()), 3)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_wording.csv", index=False)
    # 本当の変化の大きさを変えると（言い回し−0.3、各300回）
    sens2 = []
    for ch in [0.0, 0.1, 0.2]:
        s = pd.DataFrame([one_rep(np.random.default_rng(SEED * 55 + r + int(ch * 100) * 1000), ch) for r in range(300)])
        sens2.append({"change": ch, "true_change": round(float(s.true_change.mean()), 2),
                      "naive": round(float(s.naive.mean()), 2), "naive_negative": round(float((s.naive < 0).mean()), 3),
                      "split": round(float(s.split.mean()), 2), "split_p05": round(float(s.split.quantile(.05)), 2),
                      "split_p95": round(float(s.split.quantile(.95)), 2),
                      "split_negative": round(float((s.split < 0).mean()), 3)})
    sens2 = pd.DataFrame(sens2)
    sens2.to_csv(RES / "sensitivity_change.csv", index=False)

    out = {"settings": {"cuts": CUTS.tolist(), "dept_sd": DEPT_SD, "change": CHANGE, "change_sd": CHANGE_SD,
                        "person_sd": PERSON_SD, "word": WORD, "word_sd": WORD_SD, "resp_rate": RESP_RATE, "reps": REPS},
           "base_1000reps": main_res, "sensitivity_wording": sens.to_dict("records"),
           "sensitivity_change": sens2.to_dict("records"), "one_draw": one}
    json.dump(out, open(RES / "a872_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：前年比の見え方
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    items = [("本当の変化\n（同じ質問文なら）", "true_change", GRAY), ("そのまま前年と比べる\n（質問文を変えた）", "naive", ORANGE),
             ("2年目に半分ずつ聞き分け\n前年の質問文の半分で比べる", "split", BLUE)]
    for i, (lab, col, c) in enumerate(items):
        m, lo, hi = main_res[col], main_res[col + "_p05"], main_res[col + "_p95"]
        ax.barh(2 - i, m, color=c, height=0.55)
        ax.errorbar(m, 2 - i, xerr=[[m - lo], [hi - m]], fmt="none", ecolor=INK, lw=0.8, capsize=3)
        ax.text(hi + 0.4 if m >= 0 else lo - 0.4, 2 - i, f"{m:+.1f}", va="center", ha="left" if m >= 0 else "right", fontsize=10)
    ax.set_yticks([2, 1, 0]); ax.set_yticklabels([x[0] for x in items], fontsize=9.5)
    ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-17, 10)
    ax.set_xlabel("「満足（4以上）」の割合の前年からの変化（ポイント、棒は1,000回の平均、線は5〜95%）")
    ax.set_title("言い回しを厳しく置くと、本当は上がったのに前年比は下がって見える")
    save(fig, "a872_yoy.png", SRC, y=-0.06)

    # 図2：何の比べ方が残るか（部署ごとの違い 0・0.15・0.3）
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    d = sens[sens.word == -0.3].reset_index(drop=True)
    x = np.arange(len(d)); wd = 0.26
    ax.bar(x - wd, d.rank_within_new, wd, color=BLUE, label="2年目の部署の順位")
    ax.bar(x, d.rank_change_naive, wd, color=ORANGE, label="部署の伸びの順位（質問文を変えたまま）")
    ax.bar(x + wd, d.rank_change_same, wd, color=GRAY, label="部署の伸びの順位（同じ質問文なら）")
    for xs, col in [(x - wd, "rank_within_new"), (x, "rank_change_naive"), (x + wd, "rank_change_same")]:
        for xx, v in zip(xs, d[col]):
            ax.text(xx, v + 0.02, f"{v:.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"言い回しのずれの部署差 {v}" + ("（基本）" if v == 0 else "") for v in d.word_sd], fontsize=9)
    ax.set_ylim(0, 1.15); ax.set_ylabel("本当の順位との順位相関（300回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    ax.set_title("言い回しのずれが部署で違うと、部署の順位も伸びの順位も崩れる")
    save(fig, "a872_dept.png", SRC, y=-0.2)

    # 図3：言い回しのずれの大きさと、前年比
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    d = sens[sens.word_sd == 0.0]
    ax.plot(-d.word, d.naive, marker="o", color=ORANGE, label="そのまま前年と比べた変化")
    ax.plot(-d.word, d.true_change, marker="o", color=GRAY, label="本当の変化")
    for xx, yy in zip(-d.word, d.naive):
        ax.text(xx + 0.012, yy + 0.5, f"{yy:+.1f}", ha="left", fontsize=9, color=ORANGE)
    ax.axhline(0, color=INK, lw=0.8); ax.set_ylim(-15, 6.5); ax.set_xlim(-0.03, 0.56)
    ax.set_xticks([0, 0.1, 0.3, 0.5]); ax.set_xticklabels(["0（同じ）", "0.1", "0.3（基本）", "0.5"])
    ax.set_xlabel("新しい質問文の厳しさ（気持ちが低く出る大きさ）"); ax.set_ylabel("満足の割合の変化（ポイント）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("言い回しのずれが0.1でも、本当の上がり幅の大半が消える")
    save(fig, "a872_shift.png", SRC, y=-0.06)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3500])


if __name__ == "__main__":
    main()
