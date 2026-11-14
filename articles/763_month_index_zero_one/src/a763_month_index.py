"""763 継続月数を0から数えるか1から数えるかで、継続率の表はどれだけずれて読まれるのか

架空の定期購入。2024-01〜2025-06 の18か月に毎月400人ずつ加入し、2025-12 まで観察する。
解約は加入して最初の月がいちばん多く、だんだん減る。継続率の表を
  0始まり（加入した月が「0か月目」）、1始まり（加入した月が「1か月目」）
で作り、同じ「Nか月目」の数字がどれだけ違うか、取り違えて読むとどれだけずれるかを数える。
目標「3か月目の継続率60%以上」を、2つの表で判定した結果も比べる。DuckDB（1スレッド）と pandas で一致を確かめる。seed 763。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の定期購入の加入と解約（作成者が乱数で作成、seed 763）"
rng = np.random.default_rng(763)
cohorts = pd.date_range("2024-01-01", "2025-06-01", freq="MS")
END = pd.Timestamp("2025-12-01")
# k か月在籍したあと解約する確率（k=1 は加入した月のうちに解約）
haz = np.array([0.22, 0.14, 0.09] + [0.06] * 3 + [0.045] * 30)
rows = []; cid = 0
for c in cohorts:
    q = 1 + rng.normal(0, 0.12)  # 加入月ごとの違い
    for _ in range(400):
        cid += 1
        L = 1
        while L < len(haz) and rng.random() > min(haz[L - 1] * q, 0.95):
            L += 1
        last = c + pd.DateOffset(months=L - 1)
        rows.append((cid, c, None if last >= END else last))
S = pd.DataFrame(rows, columns=["customer_id", "signup_month", "last_month"])
S.assign(signup_month=S.signup_month.dt.strftime("%Y-%m-%d"), last_month=pd.to_datetime(S.last_month).dt.strftime("%Y-%m-%d")).to_csv(DATA / "subs.csv", index=False)
S["last_month"] = pd.to_datetime(S.last_month)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("subs", S)
T = con.execute((SQL / "02_retention_duckdb.sql").read_text(encoding="utf-8").rstrip().rstrip(";")).df()
T["signup_month"] = pd.to_datetime(T.signup_month)
# pandas で同じ表
lastm = S.last_month.fillna(END)
months_active = ((lastm.dt.year - S.signup_month.dt.year) * 12 + (lastm.dt.month - S.signup_month.dt.month)).astype(int)  # 0始まりの最後の月
P = []
for c, g in pd.DataFrame({"c": S.signup_month, "m": months_active}).groupby("c"):
    maxk = (END.year - c.year) * 12 + (END.month - c.month)
    for k in range(maxk + 1):
        P.append((c, k, int((g.m >= k).sum()), len(g)))
P = pd.DataFrame(P, columns=["signup_month", "month0", "active", "n"])
chk = P.merge(T, on=["signup_month", "month0"], suffixes=("", "_db"))
assert len(chk) == len(P) == len(T) and (chk.active == chk.active_db).all()
# 全体の継続率（観察できる加入月だけで平均）
W = T.groupby("month0").agg(active=("active", "sum"), n=("n", "sum")).reset_index()
W["ret"] = W.active / W.n * 100
ret0 = dict(zip(W.month0, W.ret))           # 0始まり：キーが month0
ret1 = {k + 1: v for k, v in ret0.items()}  # 1始まり：同じ値に、見出しだけ +1
ks = [1, 2, 3, 6, 12]
diff = {k: ret0[k] - ret1[k] for k in ks}  # 同じ「kか月目」の数字の違い（0始まり − 1始まり）
# 目標「3か月目の継続率60%以上」を加入月ごとに判定
co = T.pivot_table(index="signup_month", columns="month0", values="retention_pct")
pass0 = int((co[3] >= 60).sum()); pass1 = int((co[2] >= 60).sum())   # 1始まりの「3か月目」= month0 の2
n_co = int(co[3].notna().sum())
out = {"cohorts": len(cohorts), "per_cohort": 400, "observe_until": "2025-12",
       "retention_0based_pct": {str(k): round(ret0[k], 1) for k in [0] + ks},
       "retention_1based_pct": {str(k): round(ret1[k], 1) for k in ks},
       "same_label_diff_pt": {str(k): round(diff[k], 1) for k in ks},
       "misread_month1_pt": round(ret1[1] - ret0[1], 1),
       "target": "3か月目の継続率60%以上", "cohorts_judged": n_co,
       "cohorts_pass_0based": pass0, "cohorts_pass_1based": pass1,
       "month12_0based": round(ret0[12], 1), "month12_1based": round(ret1[12], 1)}
json.dump(out, open(RES / "a763_main.json", "w"), ensure_ascii=False, indent=1)
co.round(1).to_csv(RES / "cohort_table_0based.csv")

# 図1：同じ見出しで並べた2つの継続率
fig, ax = plt.subplots(figsize=(8.5, 3.8))
kk = list(range(0, 13))
ax.plot(kk, [ret0[k] for k in kk], marker="o", color=BLUE, label="0始まり（加入した月＝0か月目）")
ax.plot(kk[1:], [ret1[k] for k in kk[1:]], marker="s", color=ORANGE, label="1始まり（加入した月＝1か月目）")
for k in [1, 3, 6]:
    ax.annotate("", xy=(k, ret0[k]), xytext=(k, ret1[k]), arrowprops=dict(arrowstyle="<->", color=GRAY))
    ax.text(k + 0.15, (ret0[k] + ret1[k]) / 2, f"{ret1[k] - ret0[k]:.1f}pt", fontsize=9, color=GRAY)
ax.set_xticks(kk); ax.set_xlabel("表の見出しの「何か月目」"); ax.set_ylabel("継続率（%）"); ax.legend(frameon=False)
ax.set_title(f"同じ「1か月目」でも、0始まりと1始まりでは{ret1[1] - ret0[1]:.0f}ポイント違う")
save(fig, "a763_curves.png", SRC)
# 図2：同じ見出しの数字の違い
fig, ax = plt.subplots(figsize=(7.5, 3.6))
v = [ret1[k] - ret0[k] for k in ks]
ax.bar([f"{k}か月目" for k in ks], v, color=ORANGE)
for i, val in enumerate(v):
    ax.text(i, val + 0.4, f"{val:.1f}", ha="center")
ax.set_ylabel("1始まり − 0始まり（ポイント）")
ax.set_title("取り違えたときのずれは、解約の多い最初の数か月ほど大きい")
save(fig, "a763_diff.png", SRC)
# 図3：目標の判定
fig, ax = plt.subplots(figsize=(8.5, 3.6))
x = np.arange(n_co); cs = co.index[co[3].notna()]
ax.plot(x, co.loc[cs, 3], marker="o", color=BLUE, label="0始まりの表の「3か月目」")
ax.plot(x, co.loc[cs, 2], marker="s", color=ORANGE, label="1始まりの表の「3か月目」")
ax.axhline(60, color=GRAY, ls="--"); ax.text(n_co - 0.5, 60.6, "目標60%", ha="right", color=GRAY, fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([c.strftime("%y/%m") for c in cs], fontsize=8, rotation=45)
ax.set_xlabel("加入した月"); ax.set_ylabel("継続率（%）"); ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_title(f"同じ顧客でも、目標を達成した加入月は{pass0}か月と{pass1}か月に分かれる（{n_co}か月中）")
save(fig, "a763_target.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
