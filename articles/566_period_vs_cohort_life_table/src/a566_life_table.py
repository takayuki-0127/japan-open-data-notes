"""566 期間生命表とコーホート生命表：死亡率が下がり続けると、平均余命はどれだけ違うか（架空の死亡率）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "架空の死亡率（Gompertz–Makeham、作成者が設定）。記事566"
AGES = np.arange(0, 121)
A, B, C = 0.0002, 0.000012, 1.105          # mu(x)=A+B*C^x（架空）
BASE = 2025

def q_base():
    mu = A + B * C ** (AGES + 0.5)
    q = 1 - np.exp(-mu); q[-1] = 1.0
    return np.minimum(q, 1.0)

Q0 = q_base()

def rate(r, k, slow=None):
    """BASE から k 年後の改善の累積倍率。slow=年数なら、改善率がその年数で直線的に0まで下がる"""
    if slow is None:
        return (1 - r) ** k
    ks = np.arange(k)
    rr = r * np.clip(1 - ks / slow, 0, None)
    return float(np.prod(1 - rr))

def q_at(t, r, slow=None):
    q = Q0 * rate(r, t - BASE, slow); q[-1] = 1.0
    return np.minimum(q, 1.0)

def ex_from_q(q, x0=0):
    """x0歳の平均余命（各年の途中で亡くなる人は半年生きたとみなす）"""
    qq = q[x0:]; l = np.concatenate([[1.0], np.cumprod(1 - qq)])
    return float(l[1:].sum() + 0.5)

def period_ex(year, r, x0=0, slow=None):
    return ex_from_q(q_at(year, r, slow), x0)

def cohort_ex(year, r, x0=0, slow=None):
    """year に x0 歳の人の平均余命：x0+k 歳のときは year+k 年の死亡率"""
    q = np.array([q_at(year + (a - x0), r, slow)[a] if a < 120 else 1.0 for a in range(x0, 121)])
    full = np.ones(121); full[x0:] = q
    return ex_from_q(full, x0)

def main():
    rs = [0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
    rows = []
    for r in rs:
        for x0 in (0, 40, 65, 85):
            p = period_ex(BASE, r, x0); c = cohort_ex(BASE, r, x0)
            rows.append(dict(r=r, age=x0, period=p, cohort=c, diff=c - p))
    T = pd.DataFrame(rows); T.to_csv(RES / "period_vs_cohort.csv", index=False)

    # 改善が50年で止まっていく場合（年1.5%から直線で0へ）
    slow = []
    for x0 in (0, 65):
        slow.append(dict(case="年1.5%が続く", age=x0, period=period_ex(BASE, .015, x0), cohort=cohort_ex(BASE, .015, x0)))
        slow.append(dict(case="年1.5%から50年で0へ", age=x0, period=period_ex(BASE, .015, x0, 50), cohort=cohort_ex(BASE, .015, x0, 50)))
        slow.append(dict(case="年1.5%から20年で0へ", age=x0, period=period_ex(BASE, .015, x0, 20), cohort=cohort_ex(BASE, .015, x0, 20)))
    S = pd.DataFrame(slow); S["diff"] = S.cohort - S.period; S.to_csv(RES / "slowing_improvement.csv", index=False)

    # 期間の平均余命が毎年どれだけ伸びるか（r=1.5%）
    yrs = list(range(BASE, BASE + 41, 5))
    Y = pd.DataFrame([dict(year=y, period_e0=period_ex(y, .015), period_e65=period_ex(y, .015, 65),
                           cohort_e65=cohort_ex(y, .015, 65)) for y in yrs])
    Y.to_csv(RES / "period_by_year_r015.csv", index=False)

    # 年齢ごとの差（r=1%・2%）
    D = pd.DataFrame([dict(age=x, r=r, diff=cohort_ex(BASE, r, x) - period_ex(BASE, r, x))
                      for r in (.01, .02) for x in range(0, 101, 5)])
    D.to_csv(RES / "diff_by_age.csv", index=False)

    # SQL：r=1.5% の期間表から e0・e65 を DuckDB で計算し、Python と比べる
    q15 = q_at(BASE, .015)
    df = pd.DataFrame(dict(age=AGES, qx=q15))
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("qx_table", df)
    sql = (SQL / "a566_life_table.sql").read_text()
    out = con.execute(sql).df()
    py0, py65 = period_ex(BASE, .015, 0), period_ex(BASE, .015, 65)
    sq0 = float(out.loc[out.age == 0, "ex"].iloc[0]); sq65 = float(out.loc[out.age == 65, "ex"].iloc[0])
    out.to_csv(RES / "sql_period_table_r015.csv", index=False)

    base_l = np.concatenate([[1.0], np.cumprod(1 - Q0)])
    J = dict(q0_check=dict(q_at_0=float(Q0[0]), q_at_65=float(Q0[65]), q_at_90=float(Q0[90]),
                            e0_no_improvement=period_ex(BASE, 0), e65_no_improvement=period_ex(BASE, 0, 65),
                            median_age_death=int(np.argmax(base_l < .5)) - 1),
             sql_check=dict(python_e0=py0, sql_e0=sq0, python_e65=py65, sql_e65=sq65,
                            match=bool(abs(py0 - sq0) < 1e-9 and abs(py65 - sq65) < 1e-9)),
             main=T.round(4).to_dict("records"), slowing=S.round(4).to_dict("records"),
             by_year=Y.round(4).to_dict("records"))
    json.dump(J, open(RES / "a566_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：改善率ごとの e0・e65
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for i, x0 in enumerate((0, 65)):
        t = T[T.age == x0]
        ax[i].plot(t.r * 100, t.period, "o-", color=GRAY, label="期間生命表（2025年の死亡率だけ）")
        ax[i].plot(t.r * 100, t.cohort, "o-", color=BLUE, label="コーホート（実際に生きる年の死亡率）")
        for _, w in t.iterrows():
            if w.r in (0.01, 0.02, 0.03):
                ax[i].annotate(f"+{w['diff']:.1f}年", (w.r * 100, w.cohort), textcoords="offset points", xytext=(-14, 8), fontsize=9, color=BLUE)
        ax[i].set_title(f"2025年に{x0}歳の人の平均余命"); ax[i].set_xlabel("死亡率の改善（毎年、%）"); ax[i].set_ylabel("年")
    ax[0].legend(fontsize=8, loc="upper left")
    save(fig, "a566_by_improvement.png", SRC)

    # 図2：生存率の曲線（2025年生まれ、r=1.5%）
    lp = np.concatenate([[1.0], np.cumprod(1 - q_at(BASE, .015))])
    qc = np.array([q_at(BASE + a, .015)[a] if a < 120 else 1 for a in AGES]); lc = np.concatenate([[1.0], np.cumprod(1 - qc)])
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(np.arange(122), lp, color=GRAY, label=f"期間生命表（平均余命 {period_ex(BASE,.015):.1f}年）")
    ax.plot(np.arange(122), lc, color=BLUE, label=f"コーホート（平均余命 {cohort_ex(BASE,.015):.1f}年）")
    ax.fill_between(np.arange(122), lp, lc, color=LIGHT, alpha=.5)
    ax.set_xlim(40, 121); ax.set_xlabel("年齢"); ax.set_ylabel("生きている割合"); ax.legend(fontsize=9)
    ax.set_title("2025年生まれの生存の割合（死亡率が毎年1.5%下がる場合）")
    save(fig, "a566_survival.png", SRC)

    # 図3：改善が止まっていく場合
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    lab = S.case.unique(); w = .35; xs = np.arange(len(lab))
    for j, x0 in enumerate((0, 65)):
        v = [S[(S.case == c) & (S.age == x0)]["diff"].iloc[0] for c in lab]
        b = ax.bar(xs + (j - .5) * w, v, w, color=[BLUE, ORANGE][j], label=f"{x0}歳")
        ax.bar_label(b, fmt="+%.1f年", fontsize=9)
    ax.set_xticks(xs, lab); ax.set_ylabel("コーホート − 期間（年）")
    ax.set_title("改善が止まっていくと、差は小さくなる（2025年時点）"); ax.legend()
    save(fig, "a566_slowing.png", SRC)
    print(json.dumps(J["q0_check"], ensure_ascii=False)); print(J["sql_check"])
    print(T.round(2).to_string()); print(S.round(2).to_string()); print(Y.round(2).to_string())

if __name__ == "__main__":
    main()
