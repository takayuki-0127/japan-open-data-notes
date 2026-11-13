"""671 重複して登録した人を除かずに抽選すると、その人の当選確率は何倍になるのか

架空のキャンペーンの応募 1万人。88% は1回、7% は2回、3% は3回、2% は5回登録する（同じ人の重複登録）。
重複した登録では、メールアドレスに大文字・前後の空白が混ざることがある（40%）。電話番号はハイフンの有無が混ざる。
当選は 500 本。3通りで抽選する：
  N そのまま：登録 1件を1口として抽選
  E メールの完全一致で重複を除いてから抽選（表記ゆれは残る）
  K メールを小文字・空白除去でそろえてから重複を除いて抽選
2,000 回くり返し、登録回数ごとの1人あたりの当選確率と、同じ人が2本以上当たる数を数える。
重複の数え方は SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。数字は置いた重複の割合で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空のキャンペーンの応募（作成者が乱数で作成、seed 671）"
rng = np.random.default_rng(671)
NP, PRIZES, REPS = 10_000, 500, 2000
ent_n = rng.choice([1, 2, 3, 5], NP, p=[.88, .07, .03, .02])
rows = []
for pid, k in enumerate(ent_n):
    email = f"user{pid:05d}@example.com"
    phone = f"090{rng.integers(10**7, 10**8)}"
    for j in range(k):
        e = email
        if j > 0 and rng.random() < .4:
            e = rng.choice([email.upper(), email.capitalize(), " " + email, email + " "])
        p = phone if rng.random() < .5 else f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"
        rows.append((pid, e, p))
E = pd.DataFrame(rows, columns=["person_id", "email", "phone"])
E.insert(0, "entry_id", np.arange(1, len(E) + 1))
E = E.sample(frac=1, random_state=671).sort_values("entry_id").reset_index(drop=True)
DATA.mkdir(exist_ok=True)
E.to_csv(DATA / "entries.csv", index=False)
E["email_norm"] = E.email.str.strip().str.lower()

# 重複を除いた抽選の対象
pool = {"N": E.person_id.to_numpy(),
        "E": E.drop_duplicates("email").person_id.to_numpy(),
        "K": E.drop_duplicates("email_norm").person_id.to_numpy()}
cnt = {m: len(v) for m, v in pool.items()}

# SQL で数える
con = duckdb.connect(); con.execute("SET threads=1"); con.register("entries", E[["entry_id", "email", "phone"]])
q = (SQL / "02_dedup_count_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sq = con.execute(q).df().iloc[0]
assert int(sq.entries) == cnt["N"] and int(sq.exact_email) == cnt["E"] and int(sq.norm_email) == cnt["K"]

wins = {m: np.zeros(NP) for m in pool}; prizes_n = {m: np.zeros(NP) for m in pool}; multi = {m: [] for m in pool}
for r in range(REPS):
    for m, v in pool.items():
        w = rng.choice(v, PRIZES, replace=False)
        u, c = np.unique(w, return_counts=True)
        wins[m][u] += 1
        np.add.at(prizes_n[m], w, 1)
        multi[m].append(int((c - 1).sum()))
groups = [1, 2, 3, 5]
prob = {m: {g: float(wins[m][ent_n == g].mean() / REPS) for g in groups} for m in pool}
ratio = {m: {g: prob[m][g] / prob[m][1] for g in groups} for m in pool}
summ = []
for m in pool:
    for g in groups:
        summ.append({"method": m, "entries_per_person": g, "people": int((ent_n == g).sum()), "win_prob_pct": round(100 * prob[m][g], 3), "ratio_to_single": round(ratio[m][g], 3)})
pd.DataFrame(summ).to_csv(RES / "summary.csv", index=False)
multi_share = {g: float((ent_n == g).mean()) for g in groups}
ent_share = {g: float((ent_n == g).sum() * g / len(E)) for g in groups}
win_share_N = {g: float(prizes_n["N"][ent_n == g].sum() / (REPS * PRIZES)) for g in groups}
out = {"people": NP, "entries": cnt["N"], "after_exact_email_dedup": cnt["E"], "after_normalized_email_dedup": cnt["K"],
       "prizes": PRIZES, "reps": REPS,
       "win_prob_pct": {m: {str(g): round(100 * prob[m][g], 3) for g in groups} for m in pool},
       "ratio_to_single": {m: {str(g): round(ratio[m][g], 2) for g in groups} for m in pool},
       "extra_prizes_to_same_person_mean": {m: round(float(np.mean(multi[m])), 2) for m in pool},
       "people_share_pct": {str(g): round(100 * multi_share[g], 2) for g in groups},
       "entry_share_pct": {str(g): round(100 * ent_share[g], 2) for g in groups},
       "winner_share_pct_N": {str(g): round(100 * win_share_N[g], 2) for g in groups},
       "sql_counts": {k: int(v) for k, v in sq.items()}}
json.dump(out, open(RES / "a671_main.json", "w"), ensure_ascii=False, indent=1)

LAB = {"N": "そのまま抽選", "E": "メールの完全一致で除く", "K": "メールをそろえてから除く"}
COL = {"N": ORANGE, "E": LIGHT, "K": BLUE}
# 図1
fig, ax = plt.subplots(figsize=(8.5, 4.2))
x = np.arange(len(groups)); w = .27
for i, m in enumerate(["N", "E", "K"]):
    v = [ratio[m][g] for g in groups]
    ax.bar(x + (i - 1) * w, v, w, color=COL[m], label=LAB[m])
    for xx, vv in zip(x + (i - 1) * w, v): ax.text(xx, vv + .07, f"{vv:.1f}", ha="center", fontsize=8.5)
ax.axhline(1, color=GRAY, lw=.8, ls=":")
ax.set_xticks(x); ax.set_xticklabels([f"{g}回登録した人" for g in groups]); ax.set_ylabel("1回だけの人と比べた当選確率（倍）")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title(f"そのまま抽選すると、5回登録した人は{ratio['N'][5]:.1f}倍当たりやすい")
save(fig, "a671_ratio.png", SRC)
# 図2：登録・当選の占める割合
fig, ax = plt.subplots(figsize=(8.5, 4.2))
lab3 = ["応募した人", "登録の件数", "当選の本数（そのまま）"]
bottoms = np.zeros(3); cols = [LIGHT, BLUE, ORANGE, INK]
for g, c in zip(groups, cols):
    v = np.array([multi_share[g], ent_share[g], win_share_N[g]]) * 100
    ax.barh(lab3[::-1], v[::-1], left=bottoms[::-1], color=c, label=f"{g}回登録")
    bottoms += v
ax.set_xlabel("割合（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1.0, 1.0))
multi_people = 100 * (1 - multi_share[1]); multi_wins = 100 * (1 - win_share_N[1])
ax.set_title(f"重複登録した人は応募者の{multi_people:.0f}%だが、当選の{multi_wins:.0f}%を取る")
save(fig, "a671_shares.png", SRC)
# 図3：同じ人に重なる当選
fig, ax = plt.subplots(figsize=(8.5, 4))
v = [np.mean(multi[m]) for m in ["N", "E", "K"]]
ax.barh([LAB[m] for m in ["N", "E", "K"]][::-1], v[::-1], color=[COL[m] for m in ["N", "E", "K"]][::-1])
for i, vv in enumerate(v[::-1]): ax.text(vv, i, f" {vv:.1f}本", va="center", fontsize=9)
ax.set_xlabel("500本のうち、すでに当たった人にもう一度当たった本数（平均）"); ax.set_xlim(0, max(v) * 1.3)
ax.set_title("表記ゆれを残すと、同じ人への2本目以降の当選が残る")
save(fig, "a671_same_person.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
