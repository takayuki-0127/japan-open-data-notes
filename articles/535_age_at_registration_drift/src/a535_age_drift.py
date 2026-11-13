"""535 顧客の年齢を「登録したときの年齢」のまま集計すると、年代別の構成は何年でどれだけずれるのか（実務の型）

架空の会員（2012〜2025年に登録、30,000人、生年月日つき）と2025年の購入の記録を作る。
年代別の構成を、登録時の年齢（登録したときに保存した値）・基準日（2026-03-31）の年齢・購入時の年齢の3通りで出して比べ、
ずれが登録からの年数とどう関係するかを見る。満年齢の計算は Python と SQL（DuckDB）の両方で行い、一致を確かめる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 535
SRC = "架空の会員と購入の記録（作成者が乱数で作成、seed 535）"
ASOF = pd.Timestamp("2026-03-31")
BANDS = ["10代", "20代", "30代", "40代", "50代", "60代", "70代以上"]


def age_at(birth, d):
    """満年齢（誕生日の前日の終わりに1つ加わる扱いではなく、誕生日当日に加わる扱い）"""
    b, d = pd.to_datetime(birth), pd.to_datetime(d)
    a = d.dt.year - b.dt.year if hasattr(d, "dt") else d.year - b.dt.year
    md_d = (d.dt.month * 100 + d.dt.day) if hasattr(d, "dt") else d.month * 100 + d.day
    return a - (md_d < b.dt.month * 100 + b.dt.day).astype(int)


def band(a):
    return pd.Series(pd.cut(a, [0, 20, 30, 40, 50, 60, 70, 200], right=False, labels=BANDS), index=getattr(a, "index", None))


def make(n=30000, seed=SEED):
    rng = np.random.default_rng(seed)
    years = np.arange(2012, 2026)
    w = np.linspace(1, 2.2, len(years))                       # 最近ほど登録が多い
    ry = rng.choice(years, n, p=w / w.sum())
    reg = pd.to_datetime([f"{y}-01-01" for y in ry]) + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
    reg = pd.DatetimeIndex(np.minimum(reg.values, np.datetime64("2025-12-31")))
    a0 = np.clip(np.round(rng.normal(36, 12, n)), 16, 82).astype(int)
    birth = reg - pd.to_timedelta(a0 * 365.25 + rng.integers(0, 365, n), unit="D")
    m = pd.DataFrame({"member_id": np.arange(1, n + 1), "birth_date": birth.normalize(), "registered_on": reg.normalize()})
    m["age_at_registration"] = age_at(m.birth_date, m.registered_on)   # 登録したときに保存した値
    # 2025年の購入：登録から年数が経つほど買わなくなる。若い層は回数が少し多い
    ten = (pd.Timestamp("2025-01-01") - m.registered_on).dt.days.clip(lower=0) / 365.25
    p_act = 0.75 * np.exp(-ten / 9)
    act = rng.random(n) < p_act
    lam = 2.5 + 1.5 * (m.age_at_registration < 35)
    k = np.where(act, rng.poisson(lam) + 1, 0)
    rows = []
    for i in np.where(k > 0)[0]:
        lo = max(pd.Timestamp("2025-01-01"), m.registered_on.iloc[i])
        span = (pd.Timestamp("2025-12-31") - lo).days
        for d in rng.integers(0, span + 1, k[i]):
            rows.append((i + 1, lo + pd.Timedelta(days=int(d))))
    p = pd.DataFrame(rows, columns=["member_id", "purchased_on"]).sort_values(["member_id", "purchased_on"], ignore_index=True)
    p.insert(0, "purchase_id", np.arange(1, len(p) + 1))
    return m, p


def comp(b):
    return (b.value_counts(normalize=True).reindex(BANDS).fillna(0) * 100)


def main():
    m, p = make()
    m.to_csv(DATA / "fictional_members.csv", index=False, date_format="%Y-%m-%d")
    p.to_csv(DATA / "fictional_purchases_2025.csv", index=False, date_format="%Y-%m-%d")
    m["age_asof"] = age_at(m.birth_date, ASOF)
    m["years_since_reg"] = age_at(m.registered_on, ASOF)          # 登録からの満年数（同じ計算で数える）
    pp = p.merge(m, on="member_id")
    pp["age_at_purchase"] = age_at(pp.birth_date, pp.purchased_on)
    # SQL（DuckDB）で満年齢を出し、Python と一致するか
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("members", m[["member_id", "birth_date", "registered_on"]]); con.register("purchases", p)
    q = open(SQL / "02_age_bases_duckdb.sql", encoding="utf-8").read().split(";")
    s1 = con.execute(q[0]).df().sort_values("member_id"); s2 = con.execute(q[1]).df().sort_values("purchase_id")
    sql_ok = bool((s1.age_at_registration.to_numpy() == m.age_at_registration.to_numpy()).all() and (s1.age_asof.to_numpy() == m.age_asof.to_numpy()).all()
                  and (s2.age_at_purchase.to_numpy() == pp.sort_values("purchase_id").age_at_purchase.to_numpy()).all())

    m["b_reg"], m["b_now"] = band(m.age_at_registration).values, band(m.age_asof).values
    pp["b_reg"], pp["b_buy"] = band(pp.age_at_registration).values, band(pp.age_at_purchase).values
    cm = pd.DataFrame({"年代": BANDS, "会員_登録時(%)": comp(m.b_reg).round(1).values, "会員_基準日(%)": comp(m.b_now).round(1).values,
                       "購入_登録時(%)": comp(pp.b_reg).round(1).values, "購入_購入時(%)": comp(pp.b_buy).round(1).values})
    cm["会員の差(pt)"] = (comp(m.b_now) - comp(m.b_reg)).round(1).values; cm["購入の差(pt)"] = (comp(pp.b_buy) - comp(pp.b_reg)).round(1).values
    cm.to_csv(RES / "composition_by_age_basis.csv", index=False)
    tv = lambda a, b: round(float((comp(b) - comp(a)).abs().sum() / 2), 1)        # 構成の入れ替わり（全変動距離、ポイント）
    by = []
    for y, g in m.groupby("years_since_reg"):
        by.append({"登録からの年数": int(y), "人数": len(g), "年代が変わった割合(%)": round(float((g.b_reg != g.b_now).mean() * 100), 1),
                   "平均の年齢差(歳)": round(float((g.age_asof - g.age_at_registration).mean()), 2), "構成のずれ(pt)": tv(g.b_reg, g.b_now)})
    bt = pd.DataFrame(by); bt.to_csv(RES / "drift_by_years_since_registration.csv", index=False)
    res = {"n_members": len(m), "n_purchases": len(p), "n_buyers_2025": int(p.member_id.nunique()), "asof": str(ASOF.date()), "sql_matches_python": sql_ok,
           "members_mean_age": {"登録時": round(float(m.age_at_registration.mean()), 1), "基準日": round(float(m.age_asof.mean()), 1)},
           "members_band_changed_pct": round(float((m.b_reg != m.b_now).mean() * 100), 1), "members_tv_pt": tv(m.b_reg, m.b_now),
           "purchases_band_changed_pct": round(float((pp.b_reg != pp.b_buy).mean() * 100), 1), "purchases_tv_pt": tv(pp.b_reg, pp.b_buy),
           "purchases_mean_age": {"登録時": round(float(pp.age_at_registration.mean()), 1), "購入時": round(float(pp.age_at_purchase.mean()), 1)},
           "composition": cm.to_dict(orient="records"), "by_years": by}
    json.dump(res, open(RES / "a535_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：会員の年代別構成（登録時の年齢 vs 基準日の年齢）
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    xs = np.arange(len(BANDS)); wd = 0.38
    ax.bar(xs - wd / 2, cm["会員_登録時(%)"], wd, color=GRAY, label="登録時の年齢のまま")
    ax.bar(xs + wd / 2, cm["会員_基準日(%)"], wd, color=BLUE, label="2026-03-31 時点の年齢")
    for x, d in zip(xs, cm["会員の差(pt)"]):
        ax.text(x, max(cm["会員_登録時(%)"].iloc[x], cm["会員_基準日(%)"].iloc[x]) + 0.6, f"{d:+.1f}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(xs, BANDS); ax.set_ylabel("会員の構成比（%）"); ax.legend(frameon=False)
    ax.set_title("会員30,000人の年代別構成：保存した年齢のままだと若く出る")
    save(fig, "a535_members_composition.png", SRC + "。数字は差（ポイント）")
    # 図2：登録からの年数とずれ
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(bt["登録からの年数"], bt["年代が変わった割合(%)"], "o-", color=ORANGE, label="年代が変わった人の割合（%）")
    ax.plot(bt["登録からの年数"], bt["構成のずれ(pt)"], "s-", color=BLUE, label="年代別構成のずれ（ポイント）")
    ax.set_xlabel("登録からの年数（基準日時点）"); ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=9)
    ax.set_title("登録から5年で半分強、10年でほぼ全員の年代が変わる")
    save(fig, "a535_drift_by_years.png", SRC + "。構成のずれ＝構成比の差の絶対値の和の半分")
    # 図3：2025年の購入の年代別構成
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.bar(xs - wd / 2, cm["購入_登録時(%)"], wd, color=GRAY, label="登録時の年齢のまま")
    ax.bar(xs + wd / 2, cm["購入_購入時(%)"], wd, color=GREEN, label="購入した日の年齢")
    for x, d in zip(xs, cm["購入の差(pt)"]):
        ax.text(x, max(cm["購入_登録時(%)"].iloc[x], cm["購入_購入時(%)"].iloc[x]) + 0.6, f"{d:+.1f}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(xs, BANDS); ax.set_ylabel("購入件数の構成比（%）"); ax.legend(frameon=False)
    ax.set_title(f"2025年の購入{len(p):,}件：最近の会員が多いぶん、ずれは小さめ")
    save(fig, "a535_purchases_composition.png", SRC + "。数字は差（ポイント）")
    print(json.dumps({k: v for k, v in res.items() if k not in ("composition",)}, ensure_ascii=False, indent=1)); print(cm.to_string())


if __name__ == "__main__":
    main()
