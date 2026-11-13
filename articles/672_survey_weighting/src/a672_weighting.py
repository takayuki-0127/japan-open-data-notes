"""672 回答者の年代の偏りを重み付けで直すと、アンケートの結果はどれだけ動き、ばらつきはどれだけ増えるのか

架空の会員全体（年代の構成：20代18%・30代18%・40代20%・50代22%・60代以上22%）にアンケートを送り、1,000件の回答を集める。
年代で回答率が違う（20代が最も答えにくい）ので、回答者の年代の構成は会員全体とずれる。
「満足」と答える割合は年代で違う（20代40%〜60代以上70%）。会員全体の本当の満足の割合と比べ、3通りで出す：
  そのまま（重みなし）／年代の重み（会員全体の構成÷回答者の構成）／重みの上限2（大きすぎる重みを2で切って合計をそろえ直す）
有効な件数（Kish の式：重みの合計²÷重みの2乗の合計）も出す。
場面 A：同じ年代の中では、答えた人と答えなかった人の満足は同じ
場面 B：同じ年代の中でも、満足している人ほど答えやすい（重みでは直らない）
各 2,000 回。1回分の回答は data/survey.csv に置き、重み付きの割合を SQL（DuckDB、1スレッド）でも出して一致を確かめる。
数字は置いた構成・回答率・満足の割合で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の会員アンケート（作成者が乱数で作成、seed 672）"
rng = np.random.default_rng(672)
AGES = ["20代", "30代", "40代", "50代", "60代以上"]
POP = np.array([.18, .18, .20, .22, .22])
RESP = np.array([.05, .08, .12, .18, .25])       # 回答率
SAT = np.array([.40, .48, .55, .63, .70])        # 満足の割合
N_RESP, REPS, CAP = 1000, 2000, 2.0
TRUE = float((POP * SAT).sum())
share_resp = POP * RESP / (POP * RESP).sum()      # 回答者の年代の構成（期待値）


def draw(scene):
    age = rng.choice(5, N_RESP, p=share_resp)
    p = SAT[age].copy()
    if scene == "B":   # 答えた人は同じ年代の中でも満足しやすい：満足の割合を 8ポイント上げる
        p = np.clip(p + .08, 0, 1)
    y = (rng.random(N_RESP) < p).astype(int)
    return age, y


def weights(age, cap=None):
    cnt = np.bincount(age, minlength=5) / len(age)
    w = (POP / np.where(cnt > 0, cnt, np.nan))[age]
    if cap is not None:
        for _ in range(50):          # 切って合計をそろえ直す（くり返し）
            w = np.minimum(w, cap); w = w * len(w) / w.sum()
            if w.max() <= cap + 1e-9: break
    return w


def est(age, y):
    w1 = weights(age); w2 = weights(age, CAP)
    kish = lambda w: w.sum() ** 2 / (w ** 2).sum()
    return {"none": y.mean(), "weight": np.average(y, weights=w1), "cap": np.average(y, weights=w2),
            "neff_weight": kish(w1), "neff_cap": kish(w2), "wmax": w1.max()}


rows = []
for scene in ["A", "B"]:
    for r in range(REPS):
        age, y = draw(scene)
        rows.append({"scene": scene, "rep": r, **est(age, y)})
D = pd.DataFrame(rows)
S = D.groupby("scene").agg(none=("none", "mean"), weight=("weight", "mean"), cap=("cap", "mean"),
                           none_sd=("none", "std"), weight_sd=("weight", "std"), cap_sd=("cap", "std"),
                           neff_weight=("neff_weight", "mean"), neff_cap=("neff_cap", "mean"), wmax=("wmax", "mean")).reset_index()
S["true"] = TRUE
S.round(5).to_csv(RES / "summary.csv", index=False)

# 1回分のデータと SQL
age, y = draw("A")
DATA.mkdir(exist_ok=True)
sv = pd.DataFrame({"resp_id": np.arange(1, N_RESP + 1), "age_group": [AGES[a] for a in age], "satisfied": y})
sv.to_csv(DATA / "survey.csv", index=False)
pop = pd.DataFrame({"age_group": AGES, "pop_share": POP})
con = duckdb.connect(); con.execute("SET threads=1"); con.register("survey", sv); con.register("pop", pop)
q = (SQL / "02_weighting_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sq = con.execute(q).df().iloc[0]
e1 = est(age, y)
assert abs(sq.unweighted - e1["none"]) < 1e-12 and abs(sq.weighted - e1["weight"]) < 1e-12

sa, sb = S[S.scene == "A"].iloc[0], S[S.scene == "B"].iloc[0]
out = {"respondents": N_RESP, "reps": REPS, "true_satisfied_pct": round(100 * TRUE, 2),
       "pop_share_pct": dict(zip(AGES, (100 * POP).round(1).tolist())),
       "respondent_share_pct": dict(zip(AGES, (100 * share_resp).round(1).tolist())),
       "A": {k: round(100 * float(sa[k]), 2) for k in ["none", "weight", "cap", "none_sd", "weight_sd", "cap_sd"]},
       "B": {k: round(100 * float(sb[k]), 2) for k in ["none", "weight", "cap", "none_sd", "weight_sd", "cap_sd"]},
       "neff_weight": round(float(sa.neff_weight), 1), "neff_cap": round(float(sa.neff_cap), 1), "max_weight_mean": round(float(sa.wmax), 2),
       "sd_ratio_weight_vs_none": round(float(sa.weight_sd / sa.none_sd), 3),
       "sql_example": {"unweighted": round(float(sq.unweighted), 5), "weighted": round(float(sq.weighted), 5)}}
json.dump(out, open(RES / "a672_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：構成
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.arange(5); w = .38
ax.bar(x - w / 2, 100 * POP, w, color=GRAY, label="会員全体")
ax.bar(x + w / 2, 100 * share_resp, w, color=BLUE, label="回答者")
for xx, v in zip(x + w / 2, 100 * share_resp): ax.text(xx, v + .5, f"{v:.0f}%", ha="center", fontsize=8.5)
for xx, v, s_ in zip(x, SAT, POP / share_resp): ax.text(xx, -6.5, f"満足{100*v:.0f}%\n重み{s_:.2f}", ha="center", fontsize=8, color=INK)
ax.set_xticks(x); ax.set_xticklabels(AGES); ax.set_ylabel("構成（%）"); ax.set_ylim(-9, 42)
ax.legend(frameon=False, fontsize=9); ax.set_title(f"回答者は60代以上に偏り、20代は会員の18%なのに回答の{100*share_resp[0]:.0f}%")
save(fig, "a672_composition.png", SRC, y=-.04)
# 図2：A の推定の散らばり
fig, ax = plt.subplots(figsize=(8.5, 4.2))
da = D[D.scene == "A"]
bp = ax.boxplot([100 * da.none, 100 * da.weight, 100 * da.cap], vert=False, widths=.5, patch_artist=True, showfliers=False)
for p_, c in zip(bp["boxes"], [ORANGE, BLUE, GREEN]): p_.set_facecolor(c); p_.set_alpha(.6)
ax.axvline(100 * TRUE, color=INK, ls=":", lw=1.2); ax.text(100 * TRUE, 3.45, f"本当 {100*TRUE:.1f}%", ha="center", fontsize=9)
ax.set_yticks([1, 2, 3]); ax.set_yticklabels(["重みなし", "年代の重み", f"重み（上限{CAP:.0f}）"])
ax.set_xlabel("満足の割合の推定（%）、2,000回")
ax.set_title(f"重みで偏りは消えるが、有効な件数は1,000件から{sa.neff_weight:.0f}件に減る")
save(fig, "a672_estimates.png", SRC)
# 図3：場面 A と B
fig, ax = plt.subplots(figsize=(8.5, 4))
labs = ["重みなし", "年代の重み", f"重み（上限{CAP:.0f}）"]
x = np.arange(3); w = .38
va = [100 * (sa[k] - TRUE) for k in ["none", "weight", "cap"]]; vb = [100 * (sb[k] - TRUE) for k in ["none", "weight", "cap"]]
ax.bar(x - w / 2, va, w, color=BLUE, label="A 年代の中では答える人と答えない人が同じ")
ax.bar(x + w / 2, vb, w, color=ORANGE, label="B 満足している人ほど答えやすい")
for xx, v in zip(x - w / 2, va): ax.text(xx, v + .2, f"{v:+.1f}", ha="center", fontsize=9)
for xx, v in zip(x + w / 2, vb): ax.text(xx, v + .2, f"{v:+.1f}", ha="center", fontsize=9)
ax.axhline(0, color=GRAY, lw=.8); ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylabel("本当の値とのずれ（ポイント）")
ax.legend(frameon=False, fontsize=9, loc="upper right"); ax.set_ylim(-1, 14)
ax.set_title("年代の中の偏り（B）は、年代の重みでは直らない")
save(fig, "a672_scenes.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
