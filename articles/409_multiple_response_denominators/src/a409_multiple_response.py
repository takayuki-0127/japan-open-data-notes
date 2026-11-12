"""409 複数回答の設問は、分母の取り方で割合が何ポイント変わるのか
架空のアンケート（複数回答・無回答あり）で、4つの分母を比べる。乱数の種は409。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 409
AGES = ["20代", "30代", "40代", "50代", "60代", "70代"]
N_AGE = [450, 500, 550, 550, 500, 450]                                   # 回答者 3,000人
OPT = ["動画配信", "ネット通販", "フードデリバリー", "キャッシュレス決済", "ポイントサービス", "テレビ通販", "宅配クリーニング", "食材宅配"]
BASE = np.array([0.42, 0.62, 0.20, 0.55, 0.50, 0.12, 0.06, 0.15])        # 40代の人が選ぶ確率
TILT = np.array([-0.45, -0.15, -0.50, -0.20, 0.00, 0.60, 0.10, 0.25])     # 年齢での傾き（プラスは年上ほど選ぶ）
SKIP = [0.02, 0.03, 0.04, 0.06, 0.09, 0.13]                               # この設問に答えない人の割合


def make(seed, boost=None):
    """回答者の表と、選んだ選択肢の表（1人が何行も持つ）を作る。boost は選択肢ごとの、選びやすさの倍率"""
    boost = np.ones(len(OPT)) if boost is None else np.asarray(boost, float)
    r = np.random.default_rng(seed); people = []; picks = []
    pid = 0
    for a, (age, n) in enumerate(zip(AGES, N_AGE)):
        z = (a - 2.5) / 2.5                                               # −1（20代）〜 +1（70代）
        p = np.clip(BASE * np.exp(TILT * z) * (1 - 0.18 * z), 0.01, 0.95)  # 年上ほど、選ぶ数が全体に少ない
        pb = np.minimum(p * boost, 0.97)
        for _ in range(n):
            pid += 1; skip = r.random() < SKIP[a]
            sel = [] if skip else [j for j in range(len(OPT)) if r.random() < pb[j]]
            state = "無回答" if skip else ("特になし" if not sel else "選んだ")
            people.append({"回答者ID": pid, "年齢": age, "状態": state, "選んだ数": len(sel)})
            picks += [{"回答者ID": pid, "選択肢": OPT[j]} for j in sel]
    return pd.DataFrame(people), pd.DataFrame(picks)


def shares(P, A):
    """選択肢ごとの割合を、4つの分母で出す"""
    n_all = len(P); n_valid = int((P["状態"] != "無回答").sum()); n_sel = int((P["状態"] == "選んだ").sum()); n_resp = len(A)
    c = A["選択肢"].value_counts().reindex(OPT).fillna(0)
    return pd.DataFrame({"選んだ人": c.astype(int), "①回答者全体": 100 * c / n_all, "②無回答を除く": 100 * c / n_valid,
                         "③1つ以上選んだ人": 100 * c / n_sel, "④回答の数": 100 * c / n_resp}), \
        {"回答者全体": n_all, "無回答を除く": n_valid, "1つ以上選んだ人": n_sel, "回答の数": n_resp}


DEN = ["①回答者全体", "②無回答を除く", "③1つ以上選んだ人", "④回答の数"]
P, A = make(SEED)
P.to_csv(DATA / "respondents.csv", index=False); A.to_csv(DATA / "answers.csv", index=False)
S, den = shares(P, A)
S["最大−最小（ポイント）"] = S[DEN].max(1) - S[DEN].min(1); S["人が分母の3つの差"] = S[DEN[:3]].max(1) - S[DEN[:3]].min(1)
S.round(2).to_csv(RES / "shares_total.csv")

# ---- SQL（DuckDB）：分母ごとの割合。pandas と一致するか ----
con = duckdb.connect(); con.register("respondents", P); con.register("answers", A)
q = """
WITH d AS (
  SELECT COUNT(*)                                            AS n_all,      -- ① 回答者全体
         SUM(CASE WHEN 状態 <> '無回答' THEN 1 ELSE 0 END)   AS n_valid,    -- ② 無回答を除く
         SUM(CASE WHEN 状態 = '選んだ' THEN 1 ELSE 0 END)    AS n_sel       -- ③ 1つ以上選んだ人
  FROM respondents
), r AS (SELECT COUNT(*) AS n_resp FROM answers)                            -- ④ 回答の数
SELECT a.選択肢, COUNT(*) AS 選んだ人,
       100.0 * COUNT(*) / MAX(d.n_all)   AS p1, 100.0 * COUNT(*) / MAX(d.n_valid) AS p2,
       100.0 * COUNT(*) / MAX(d.n_sel)   AS p3, 100.0 * COUNT(*) / MAX(r.n_resp)  AS p4
FROM answers AS a CROSS JOIN d CROSS JOIN r
GROUP BY a.選択肢"""
sq = con.sql(q).df().set_index("選択肢").reindex(OPT)
assert np.allclose(sq[["p1", "p2", "p3", "p4"]].to_numpy(), S[DEN].to_numpy())
# よくある書き方：回答の表だけで分母を数える（1つも選ばなかった人が分母から落ちる）
q_bad = "SELECT 選択肢, 100.0 * COUNT(*) / (SELECT COUNT(DISTINCT 回答者ID) FROM answers) AS p FROM answers GROUP BY 選択肢"
bad = con.sql(q_bad).df().set_index("選択肢").reindex(OPT)
assert np.allclose(bad["p"].to_numpy(), S["③1つ以上選んだ人"].to_numpy())
sq.round(3).to_csv(RES / "sql_check_duckdb.csv")

# ---- 年齢ごと ----
rows = []; per = {}
for age in AGES:
    Pa = P[P["年齢"] == age]; Aa = A[A["回答者ID"].isin(Pa["回答者ID"])]
    s, d = shares(Pa, Aa); per[age] = s
    rows.append({"年齢": age, **d, "無回答(%)": round(100 * (Pa["状態"] == "無回答").mean(), 1), "特になし(%)": round(100 * (Pa["状態"] == "特になし").mean(), 1),
                 "1人あたりの回答の数": round(d["回答の数"] / d["1つ以上選んだ人"], 2), "割合の合計_②": round(s["②無回答を除く"].sum(), 1), "割合の合計_④": round(s["④回答の数"].sum(), 1)})
BYAGE = pd.DataFrame(rows); BYAGE.to_csv(RES / "by_age_denominators.csv", index=False)
pd.concat({a: per[a][DEN].round(2) for a in AGES}).to_csv(RES / "shares_by_age.csv")

# 年齢の間の比べ：分母で「どちらが高いか」が入れ替わる組
flips = []; n_pairs = 0
for j, o in enumerate(OPT):
    for i1 in range(len(AGES)):
        for i2 in range(i1 + 1, len(AGES)):
            a1, a2 = AGES[i1], AGES[i2]; n_pairs += 1
            d2 = per[a1].loc[o, "②無回答を除く"] - per[a2].loc[o, "②無回答を除く"]; d4 = per[a1].loc[o, "④回答の数"] - per[a2].loc[o, "④回答の数"]
            d1 = per[a1].loc[o, "①回答者全体"] - per[a2].loc[o, "①回答者全体"]
            flips.append({"選択肢": o, "年齢A": a1, "年齢B": a2, "差_①": round(d1, 2), "差_②": round(d2, 2), "差_④": round(d4, 2),
                          "②と④で向きが逆": bool(d2 * d4 < 0), "①と②で向きが逆": bool(d1 * d2 < 0)})
FL = pd.DataFrame(flips); FL.to_csv(RES / "age_pair_direction.csv", index=False)
# 選択肢ごとに「いちばん高い年齢」が変わるか
top = pd.DataFrame({d: [max(AGES, key=lambda a: per[a].loc[o, d]) for o in OPT] for d in DEN}, index=OPT)
top.to_csv(RES / "top_age_by_denominator.csv")
# 年齢の中での順位（④と②は同じ）と、20代と70代の差
y, o_ = per["20代"], per["70代"]
CMP = pd.DataFrame({"20代_②": y["②無回答を除く"], "70代_②": o_["②無回答を除く"], "差_②": y["②無回答を除く"] - o_["②無回答を除く"],
                    "20代_④": y["④回答の数"], "70代_④": o_["④回答の数"], "差_④": y["④回答の数"] - o_["④回答の数"]}).round(1)
CMP.to_csv(RES / "young_vs_old.csv")

# ---- 2回の調査を比べる：同じ回答者に1年後にもう一度聞いた、と置く。どの選択肢も選ぶ人は増えるが、増え方が違う ----
BOOST = [1.40, 1.04, 1.50, 1.25, 1.06, 1.05, 1.30, 1.10]
P2, A2 = make(SEED, boost=BOOST)                                          # 乱数は1回目と同じ（同じ人の、選びやすさだけが変わる）
S2, den2 = shares(P2, A2)
W = pd.DataFrame({"1回目_②": S["②無回答を除く"], "2回目_②": S2["②無回答を除く"], "変化_②": S2["②無回答を除く"] - S["②無回答を除く"],
                  "1回目_④": S["④回答の数"], "2回目_④": S2["④回答の数"], "変化_④": S2["④回答の数"] - S["④回答の数"]})
W["向きが逆"] = (W["変化_②"] * W["変化_④"] < 0); W.round(2).to_csv(RES / "two_waves.csv")

# 200回くり返す：向きが逆になる数
rep = []
for k in range(200):
    Pk, Ak = make(SEED + 1000 + k); sk, _ = shares(Pk, Ak); pk = {}
    for age in AGES:
        Pa = Pk[Pk["年齢"] == age]; pk[age], _ = shares(Pa, Ak[Ak["回答者ID"].isin(Pa["回答者ID"])])
    f = 0
    for o in OPT:
        for i1 in range(6):
            for i2 in range(i1 + 1, 6):
                d2 = pk[AGES[i1]].loc[o, "②無回答を除く"] - pk[AGES[i2]].loc[o, "②無回答を除く"]; d4 = pk[AGES[i1]].loc[o, "④回答の数"] - pk[AGES[i2]].loc[o, "④回答の数"]
                f += d2 * d4 < 0
    rep.append({"回": k, "②と④で向きが逆の組": int(f), "最大−最小の最大": float((sk[DEN].max(1) - sk[DEN].min(1)).max()), "①と③の差の最大": float((sk["③1つ以上選んだ人"] - sk["①回答者全体"]).max())})
REP = pd.DataFrame(rep); REP.to_csv(RES / "repeat_200.csv", index=False)

main = {"分母": den, "1人あたりの回答の数（選んだ人）": round(den["回答の数"] / den["1つ以上選んだ人"], 2),
        "割合の合計": {d: round(float(S[d].sum()), 1) for d in DEN},
        "選択肢ごと": S.round(1).to_dict("index"),
        "最大−最小の平均": round(float(S["最大−最小（ポイント）"].mean()), 1), "最大−最小の最大": round(float(S["最大−最小（ポイント）"].max()), 1),
        "人が分母の3つの差の最大": round(float(S["人が分母の3つの差"].max()), 1),
        "年齢ごと": BYAGE.set_index("年齢").to_dict("index"),
        "年齢の組": {"組の数": n_pairs, "②と④で向きが逆": int(FL["②と④で向きが逆"].sum()), "①と②で向きが逆": int(FL["①と②で向きが逆"].sum()),
                  "200回の平均": round(float(REP["②と④で向きが逆の組"].mean()), 1), "200回の範囲": [int(REP["②と④で向きが逆の組"].min()), int(REP["②と④で向きが逆の組"].max())]},
        "いちばん高い年齢が分母で変わる選択肢": int((top.nunique(axis=1) > 1).sum()),
        "2回の調査": {"1人あたりの回答の数": [round(den["回答の数"] / den["1つ以上選んだ人"], 2), round(den2["回答の数"] / den2["1つ以上選んだ人"], 2)],
                  "向きが逆の選択肢": W.index[W["向きが逆"]].tolist(), "表": W.round(1).to_dict("index")}}
json.dump(main, open(RES / "a409_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図 ----
SRC = "架空のアンケート（作成者が乱数で作成、seed 409）"
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(OPT)); w = 0.2
for k, (d, c) in enumerate(zip(DEN, [GRAY, BLUE, LIGHT, ORANGE])):
    ax.bar(x + (k - 1.5) * w, S[d], w, color=c, label=d)
for i, o in enumerate(OPT):
    ax.text(i, S.loc[o, DEN].max() + 1.5, f"差{S.loc[o, '最大−最小（ポイント）']:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(OPT, fontsize=8.5, rotation=15); ax.set_ylabel("割合（%）"); ax.legend(frameon=False, fontsize=9, ncol=2)
ax.set_title("同じ回答でも、分母で割合が変わる（回答者3,000人）")
save(fig, "a409_shares_by_denominator.png", SRC + "。棒の上は、4つの分母の最大と最小の差（ポイント）", y=-0.04)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
ax = axes[0]; x = np.arange(len(OPT)); w = 0.38
ax.bar(x - w / 2, CMP["差_②"], w, color=BLUE, label="②無回答を除く人が分母"); ax.bar(x + w / 2, CMP["差_④"], w, color=ORANGE, label="④回答の数が分母")
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(OPT, fontsize=7.5, rotation=30, ha="right")
ax.set_ylabel("20代 − 70代（ポイント）"); ax.legend(frameon=False, fontsize=8.5); ax.set_title("20代と70代の差", fontsize=11)
ax = axes[1]
ax.bar(range(6), BYAGE["1人あたりの回答の数"], color=GRAY)
for i, v in enumerate(BYAGE["1人あたりの回答の数"]): ax.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=9)
ax.set_xticks(range(6)); ax.set_xticklabels(AGES); ax.set_ylabel("選んだ人1人あたりの回答の数"); ax.set_title("年齢ごとの、選んだ数", fontsize=11)
save(fig, "a409_age_direction.png", SRC, y=-0.06)

fig, ax = plt.subplots(figsize=(9, 4.3)); x = np.arange(len(OPT)); w = 0.38
ax.bar(x - w / 2, W["変化_②"], w, color=BLUE, label="②無回答を除く人が分母"); ax.bar(x + w / 2, W["変化_④"], w, color=ORANGE, label="④回答の数が分母")
for i, o in enumerate(OPT):
    ax.text(i - w / 2, W.loc[o, "変化_②"] + (0.3 if W.loc[o, "変化_②"] >= 0 else -1.0), f"{W.loc[o, '変化_②']:+.1f}", ha="center", fontsize=8)
    ax.text(i + w / 2, W.loc[o, "変化_④"] + (0.3 if W.loc[o, "変化_④"] >= 0 else -1.0), f"{W.loc[o, '変化_④']:+.1f}", ha="center", fontsize=8)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(OPT, fontsize=8.5, rotation=15); ax.set_ylim(W[["変化_②", "変化_④"]].min().min() - 2, W[["変化_②", "変化_④"]].max().max() + 2); ax.set_ylabel("2回目 − 1回目（ポイント）")
ax.legend(frameon=False, fontsize=9); ax.set_title("2回の調査の変化：選ぶ人が増えても、回答の数が分母の割合は下がる選択肢がある")
save(fig, "a409_two_waves.png", SRC + "。2回目は、選ぶ確率を選択肢ごとに1.04〜1.5倍にした（どの選択肢も、選ぶ人は増えている）", y=-0.04)
print(json.dumps({k: v for k, v in main.items() if k not in ("選択肢ごと", "年齢ごと")}, ensure_ascii=False, indent=1)); print(S.round(1).to_string()); print(BYAGE.to_string()); print(CMP.to_string()); print(top.to_string()); print(W.round(1).to_string())
