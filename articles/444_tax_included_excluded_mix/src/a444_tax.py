"""444 税込みと税抜きの金額が混ざった表を足すと、売上はどれだけずれるか（架空の取引2万件）"""
import json, math
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 444
SRC = "架空の取引（作成者が乱数で作成、seed 444）"


def make(seed=SEED, n=20000, incl_share=0.45, null_share=0.30, round_price=True, null_incl_bias=None):
    """税抜きの金額（正解）から、税込み・税抜きが混ざった amount を作る。税は1円未満切り捨て"""
    r = np.random.default_rng(seed)
    d = pd.to_datetime("2019-04-01") + pd.to_timedelta(r.integers(0, 366, n), "D")
    cat = r.choice(["食品", "日用品", "サービス"], n, p=[0.35, 0.40, 0.25])
    if round_price:   # きりのよい値付け（10円単位）×数量
        excl = (r.choice([100, 150, 200, 300, 480, 500, 800, 980, 1200, 1500, 1980, 2500, 3000, 4800, 9800], n) * r.integers(1, 6, n)).astype(np.int64)
    else:             # 1円単位の値付け
        excl = np.round(r.lognormal(7.2, 0.9, n)).astype(np.int64) + 1
    rate = np.where(d < pd.Timestamp("2019-10-01"), 8, np.where(cat == "食品", 8, 10))
    tax = excl * rate // 100; incl = excl + tax
    is_incl = r.random(n) < incl_share
    known = r.random(n) >= null_share
    if null_incl_bias is not None:             # 税の列が空の行だけ、税込みの割合を変える
        is_incl = np.where(known, is_incl, r.random(n) < null_incl_bias)
    amount = np.where(is_incl, incl, excl)
    t = pd.DataFrame({"txn_id": np.arange(1, n + 1), "txn_date": d, "category": cat, "amount": amount, "tax_type": np.where(known, np.where(is_incl, "込", "抜"), None),
                      "true_excl": excl, "true_is_incl": is_incl, "rate": rate})
    return t.sort_values(["txn_date", "txn_id"]).reset_index(drop=True)


def back(amount, rate):
    """税込み（切り捨て）から税抜きに戻す：ceil(amount*100/(100+rate))"""
    return -((-amount * 100) // (100 + rate))


def guess_mod10(t): return t.amount % 10 != 0


def guess_step50(t):
    """値付けの刻みを知っている場合：戻した額が50円の倍数で、元の額が50円の倍数でなければ税込み。それ以外は10円の倍数かどうかで決める"""
    b = back(t.amount.values, t.rate.values); ok = (b + b * t.rate.values // 100) == t.amount.values
    return (ok & (b % 50 == 0) & (t.amount.values % 50 != 0)) | (t.amount.values % 10 != 0)


def evaluate(t, guess=guess_mod10):
    k = t.tax_type.notna().values; inc_flag = (t.tax_type == "込").values
    m1 = t.amount.values                                                    # ① そのまま足す
    m2 = np.where(inc_flag, back(t.amount.values, t.rate.values), t.amount.values)          # ② 列で戻す（空は税抜きとみなす）
    g = guess(t); inc3 = np.where(k, inc_flag, g)
    m3 = np.where(inc3, back(t.amount.values, t.rate.values), t.amount.values)              # ③ 空の行は端数から推し量る
    tr = t.true_excl.values
    acc = float((g[~k] == t.true_is_incl.values[~k]).mean() * 100) if (~k).any() else float("nan")
    tp = (g[~k] & t.true_is_incl.values[~k]).sum(); fn = (~g[~k] & t.true_is_incl.values[~k]).sum(); fp = (g[~k] & ~t.true_is_incl.values[~k]).sum()
    return dict(n=len(t), null_rows=int((~k).sum()), asis_pct=float((m1.sum() / tr.sum() - 1) * 100), flag_pct=float((m2.sum() / tr.sum() - 1) * 100), guess_pct=float((m3.sum() / tr.sum() - 1) * 100),
                guess_acc=acc, miss_incl=int(fn), false_incl=int(fp), exact_rows_flag=float((m2 == tr).mean() * 100), exact_rows_guess=float((m3 == tr).mean() * 100),
                back_exact=float((back(t.amount.values, t.rate.values)[t.true_is_incl.values] == tr[t.true_is_incl.values]).mean() * 100)), (m1, m2, m3)


t = make(); res, (m1, m2, m3) = evaluate(t); res50 = evaluate(t, guess_step50)[0]
kk = t.tax_type.isna().values; gg = guess_mod10(t)[kk]; tr_ = t.true_is_incl.values[kk]; po = (t.txn_date >= "2019-10-01").values[kk]
acc_pre = float((gg[~po] == tr_[~po]).mean() * 100); acc_post = float((gg[po] == tr_[po]).mean() * 100)
incl10 = float(((t.amount % 10 == 0) & t.true_is_incl).sum() / t.true_is_incl.sum() * 100)
t[["txn_id", "txn_date", "category", "amount", "tax_type"]].to_csv(DATA / "transactions_mixed.csv", index=False)
t[["txn_id", "true_excl", "true_is_incl", "rate"]].to_csv(DATA / "transactions_truth.csv", index=False)
t["ym"] = t.txn_date.dt.strftime("%Y-%m")
mon = t.assign(m1=m1, m2=m2, m3=m3).groupby("ym").agg(true=("true_excl", "sum"), asis=("m1", "sum"), flag=("m2", "sum"), guess=("m3", "sum"), n=("txn_id", "size"))
for c in ("asis", "flag", "guess"): mon[c + "_pct"] = (mon[c] / mon["true"] - 1) * 100
mon["yoy_like"] = np.nan; mon.round(3).to_csv(RES / "monthly_gap.csv")
bycat = t.assign(m1=m1, m3=m3).groupby(["category", t.txn_date >= "2019-10-01"]).apply(lambda x: pd.Series(dict(asis_pct=(x.m1.sum() / x.true_excl.sum() - 1) * 100, guess_pct=(x.m3.sum() / x.true_excl.sum() - 1) * 100, n=len(x)))).reset_index().rename(columns={"txn_date": "after_oct"})
bycat.round(3).to_csv(RES / "gap_by_category_period.csv", index=False)
# 前の月との比べ：税込みの割合が月によって違うと、前月比がずれる
r = np.random.default_rng(SEED + 1); rows = []
for k in range(200):
    shares = np.clip(r.normal(0.45, 0.10, 12), 0.05, 0.95); tt = make(seed=1000 + k)
    tt["ym"] = tt.txn_date.dt.strftime("%Y-%m"); u = np.random.default_rng(k).random(len(tt)); idx = tt.ym.map({m: s for m, s in zip(sorted(tt.ym.unique()), shares)}).values
    isin = u < idx; amt = np.where(isin, tt.true_excl + tt.true_excl * tt.rate // 100, tt.true_excl)
    g = tt.assign(a=amt).groupby("ym").agg(a=("a", "sum"), tr=("true_excl", "sum")); d = (g.a.pct_change() - g.tr.pct_change()).dropna() * 100
    rows.append(dict(mean_abs_mom_gap=float(d.abs().mean()), max_abs_mom_gap=float(d.abs().max()), sign_flip=int(((g.a.pct_change() * g.tr.pct_change()) < 0).sum())))
momt = pd.DataFrame(rows); momt.round(3).to_csv(RES / "mom_gap_when_mix_varies.csv", index=False)

# 条件を変える
rows = []
for lab, kw in [("基本（10円単位の値付け、税込み45%、列が空30%）", {}), ("1円単位の値付け", dict(round_price=False)), ("税込みが20%", dict(incl_share=0.20)), ("税込みが80%", dict(incl_share=0.80)), ("列が空10%", dict(null_share=0.10)),
                ("列が空60%", dict(null_share=0.60)), ("列がすべて空", dict(null_share=1.0)), ("列が空の行は税込みが90%", dict(null_incl_bias=0.90))]:
    for gname, gf in (("10円の倍数でなければ税込み", guess_mod10), ("戻した額が50円の倍数なら税込み（値付けの刻みを知っている場合）", guess_step50)):
        v = [evaluate(make(seed=2000 + k, **kw), gf)[0] for k in range(12)]
        rows.append(dict(case=lab, guess=gname, **{c: float(np.mean([x[c] for x in v])) for c in ("asis_pct", "flag_pct", "guess_pct", "guess_acc", "exact_rows_guess")}))
sw = pd.DataFrame(rows); sw.round(3).to_csv(RES / "by_condition.csv", index=False)
# 税込みの額として「ありえない」額の割合（1円単位の値付けでも使える手がかり）
am = np.arange(1, 100001); imp = {rt: float(((back(am, rt) + back(am, rt) * rt // 100) != am).mean() * 100) for rt in (8, 10)}

# SQL（DuckDB）で②と③を出して一致を確かめる
con = duckdb.connect(); con.execute("SET threads=1"); con.register("txn", t[["txn_id", "txn_date", "category", "amount", "tax_type"]])
q = """WITH r AS (SELECT t.*, CASE WHEN txn_date < DATE '2019-10-01' THEN 8 WHEN category = '食品' THEN 8 ELSE 10 END AS rate FROM txn t)
SELECT txn_id, CASE WHEN tax_type = '込' THEN CAST(CEIL(amount * 100.0 / (100 + rate) - 0.0000001) AS BIGINT) ELSE amount END AS excl_by_flag,
       CASE WHEN tax_type = '込' OR (tax_type IS NULL AND amount % 10 <> 0) THEN CAST(CEIL(amount * 100.0 / (100 + rate) - 0.0000001) AS BIGINT) ELSE amount END AS excl_by_guess
FROM r ORDER BY txn_id"""
s = con.execute(q).df().set_index("txn_id"); tt = t.set_index("txn_id")
assert (s.excl_by_flag.loc[tt.index].values == m2).all() and (s.excl_by_guess.loc[tt.index].values == m3).all()
pd.DataFrame([dict(rows=len(s), sum_flag=int(s.excl_by_flag.sum()), sum_guess=int(s.excl_by_guess.sum()), python_flag=int(m2.sum()), python_guess=int(m3.sum()))]).to_csv(RES / "sql_check_duckdb.csv", index=False)

pre = mon.loc[:"2019-09"]; post = mon.loc["2019-10":]
main = dict(n=len(t), true_total=int(t.true_excl.sum()), main=res, main_step50=res50, guess_acc_pre_oct=acc_pre, guess_acc_post_oct=acc_post, incl_amounts_multiple_of_10_pct=incl10, impossible_as_incl_pct=imp,
            pre_oct=dict(asis=float((pre.asis.sum() / pre["true"].sum() - 1) * 100), flag=float((pre.flag.sum() / pre["true"].sum() - 1) * 100), guess=float((pre.guess.sum() / pre["true"].sum() - 1) * 100)),
            post_oct=dict(asis=float((post.asis.sum() / post["true"].sum() - 1) * 100), flag=float((post.flag.sum() / post["true"].sum() - 1) * 100), guess=float((post.guess.sum() / post["true"].sum() - 1) * 100)),
            month_range_asis=[float(mon.asis_pct.min()), float(mon.asis_pct.max())], sep_oct_asis=[float(mon.loc["2019-09", "asis_pct"]), float(mon.loc["2019-10", "asis_pct"])],
            mom=dict(n=200, mean_abs=float(momt.mean_abs_mom_gap.mean()), max_median=float(momt.max_abs_mom_gap.median()), sign_flip_mean=float(momt.sign_flip.mean()), sign_flip_any=float((momt.sign_flip > 0).mean() * 100)),
            by_category=bycat.round(3).to_dict("records"), by_condition=sw.round(3).to_dict("records"))
json.dump(main, open(RES / "a444_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：月ごとのずれ（3つの方法）
fig, ax = plt.subplots(figsize=(10, 4.2)); x = np.arange(len(mon))
ax.plot(x, mon.asis_pct, "-o", color=ORANGE, label="①そのまま足す"); ax.plot(x, mon.flag_pct, "-o", color=BLUE, label="②税の列で戻す（空の行は税抜きとみなす）"); ax.plot(x, mon.guess_pct, "-o", color=INK, label="③空の行は端数から推し量る")
ax.axhline(0, color=GRAY, lw=0.8); ax.axvline(5.5, color=GRAY, ls=":", lw=1); ax.text(5.6, ax.get_ylim()[1] * 0.97, "2019年10月（税率が変わる）", fontsize=9, va="top")
ax.set_xticks(x); ax.set_xticklabels([m[2:] for m in mon.index], fontsize=8); ax.set_ylabel("税抜きの正しい売上とのずれ（%）"); ax.set_title("月ごとの売上のずれ"); ax.legend(frameon=False, fontsize=9, loc="center right")
save(fig, "a444_monthly_gap.png", SRC)
# 図2：条件ごとのずれ（推し量り方2つ）
fig, ax = plt.subplots(figsize=(10, 4.8)); cs = list(dict.fromkeys(sw.case)); y = np.arange(len(cs))[::-1]; h = 0.26
ax.barh(y + h, [sw[(sw.case == c)].asis_pct.iloc[0] for c in cs], h, color=ORANGE, label="①そのまま足す")
ax.barh(y, [sw[(sw.case == c)].flag_pct.iloc[0] for c in cs], h, color=BLUE, label="②税の列で戻す")
ax.barh(y - h, [sw[(sw.case == c) & (sw.guess == "10円の倍数でなければ税込み")].guess_pct.iloc[0] for c in cs], h, color=INK, label="③端数から推し量る（10円の倍数でなければ税込み）")
ax.axvline(0, color=GRAY, lw=0.8); ax.set_yticks(y); ax.set_yticklabels(cs, fontsize=9); ax.set_xlabel("税抜きの正しい売上とのずれ（%）"); ax.set_title("条件を変えたときのずれ（12回の平均）", pad=30); ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
save(fig, "a444_by_condition.png", SRC)
# 図3：推し量りが当たる割合
fig, ax = plt.subplots(figsize=(10, 4.4)); w = 0.38; xx = np.arange(len(cs))
for j, (gname, c) in enumerate((("10円の倍数でなければ税込み", BLUE), ("戻した額が50円の倍数なら税込み（値付けの刻みを知っている場合）", ORANGE))):
    ax.bar(xx + (j - 0.5) * w, [sw[(sw.case == cc) & (sw.guess == gname)].guess_acc.iloc[0] for cc in cs], w, color=c, label=gname)
ax.set_xticks(xx); ax.set_xticklabels([c.replace("（", "\n（").replace("、", "、\n").replace("行は", "行は\n") for c in cs], fontsize=7.5); ax.set_ylabel("列が空の行で当たった割合（%）"); ax.set_ylim(0, 105); ax.axhline(50, color=GRAY, lw=0.8, ls=":")
ax.set_title("端数から推し量る方法の当たる割合", pad=30); ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
save(fig, "a444_guess_accuracy.png", SRC)
print(json.dumps({k: main[k] for k in main if k not in ("by_condition",)}, ensure_ascii=False)[:2500]); print(sw.round(2).to_string()); print(mon[["asis_pct", "flag_pct", "guess_pct"]].round(2).to_string())
