"""501 入金と請求を金額だけで突き合わせると、何件がまちがった請求に消し込まれるのか（実務の型）

架空の請求と入金を作り、4通りの消込（入金を請求に当てること）を比べる。
正解（どの入金がどの請求の支払いか）が分かっているので、誤った消込を1件ずつ数えられる。
"""
import json, unicodedata, re
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 501
SRC = "架空の請求・入金データ（作成者が乱数で作成、seed 501）"
PLAN = [11000, 22000, 33000, 55000, 110000, 165000, 220000]   # 定額の契約でよく出る金額
FEES = [440, 660, 770]                                          # 振込手数料として差し引かれる額
KANA = list("アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワ")
SMALL = {"ヤ": "ャ", "ユ": "ュ", "ヨ": "ョ", "ツ": "ッ"}


def make_data(n_cust=600, fixed_share=0.4, months=6, seed=SEED):
    rng = np.random.default_rng(seed)
    cust = []
    for c in range(n_cust):
        name = "".join(rng.choice(KANA, rng.integers(4, 8)))
        cust.append({"cust": c, "kana": name, "fixed": rng.random() < fixed_share,
                     "plan": int(rng.choice(PLAN)), "per_month": int(rng.choice([1, 1, 1, 2, 3]))})
    inv, pay = [], []
    iid = 0
    for c in cust:
        for m in range(1, months + 1):
            for k in range(c["per_month"]):
                amt = c["plan"] if c["fixed"] else int(round(rng.lognormal(10.6, 0.8), -1))
                issue = pd.Timestamp(2026, m, 1) + pd.offsets.MonthEnd(0)
                due = issue + pd.offsets.MonthEnd(1)
                no = f"INV{2026:04d}{m:02d}{iid:05d}"
                inv.append({"inv": iid, "inv_no": no, "cust": c["cust"], "amount": amt, "issue": issue, "due": due})
                u = rng.random()
                day = due + pd.Timedelta(days=int(rng.integers(-12, 6)))
                payer = payer_name(c["kana"], rng)
                with_no = rng.random() < 0.4
                if u < 0.82:
                    pay.append(dict(true_inv=iid, kind="全額", amount=amt, date=day, payer=payer, ref=no if with_no else ""))
                elif u < 0.91:
                    fee = int(rng.choice(FEES))
                    pay.append(dict(true_inv=iid, kind="手数料差引", amount=amt - fee, date=day, payer=payer, ref=no if with_no else ""))
                elif u < 0.96:
                    a1 = int(round(amt * rng.uniform(0.3, 0.7), -3))
                    pay.append(dict(true_inv=iid, kind="分割", amount=a1, date=day - pd.Timedelta(days=10), payer=payer, ref=""))
                    pay.append(dict(true_inv=iid, kind="分割", amount=amt - a1, date=day, payer=payer, ref=""))
                # 残り4%は締めの時点で未入金
                iid += 1
    inv = pd.DataFrame(inv)
    pay = pd.DataFrame(pay).sort_values(["date", "true_inv"]).reset_index(drop=True)
    pay["pay"] = range(len(pay))
    return pd.DataFrame(cust), inv, pay


def payer_name(kana, rng):
    """振込の名義：半角カナ、会社の略号（ｶ) など）、小さい字の違い、まれに別の会社（親会社など）から"""
    s = kana
    if rng.random() < 0.3:
        s = "".join(SMALL.get(ch, ch) if rng.random() < 0.5 else ch for ch in s)
    if rng.random() < 0.06:
        s = "".join(rng.choice(KANA, 5))            # 名義が別（親会社・代理の支払い）
    pre = rng.choice(["ｶ)", "ｶﾌﾞｼｷｶﾞｲｼﾔ ", "ﾕ)", ""])
    s = unicodedata.normalize("NFKC", s)               # 全角→そのまま（下で半角に）
    s = to_half(s)
    return (pre + s) if rng.random() < 0.7 else (s + " " + pre.strip())


def to_half(s):
    import unicodedata as u
    out = []
    for ch in s:
        try:
            out.append(u.lookup("HALFWIDTH KATAKANA LETTER " + u.name(ch).split("LETTER ")[1]))
        except Exception:
            out.append(ch)
    return "".join(out)


def norm(s):
    """名義の正規化：全角にそろえ、会社の略号と空白を外し、小さい字を大きい字に"""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"INV\d+", "", s)
    s = re.sub(r"(カ\)|ユ\)|カブシキガイシヤ|カブシキガイシャ)", "", s)
    s = s.replace(" ", "").replace("　", "")
    return s.translate(str.maketrans("ャュョッ", "ヤユヨツ"))


def match(inv, pay, cust, method):
    """入金を日付の順に1件ずつ請求に当てる（いちばん素朴な消込の流れ）。戻り値：入金ごとの当てた請求"""
    import bisect
    kana = cust.set_index("cust")["kana"].to_dict()
    iv = inv.sort_values(["due", "inv"])
    closed = set()
    by_amt, by_ka, due_of, amt_of = {}, {}, {}, {}
    for r in iv.itertuples():
        by_amt.setdefault(r.amount, []).append(r.inv)
        by_ka.setdefault((kana[r.cust], r.amount), []).append(r.inv)
        due_of[r.inv] = r.due; amt_of[r.inv] = r.amount
    dues = {a: [due_of[k] for k in ks] for a, ks in by_amt.items()}
    by_no = dict(zip(inv["inv_no"], inv["inv"]))
    first_open = lambda ks: next((k for k in ks if k not in closed), None)
    res = []
    for r in pay.itertuples():
        hit = None
        if method == "D" and r.ref:
            k = by_no.get(r.ref)
            if k is not None and k not in closed:
                hit = k
        if hit is None:
            if method == "A":
                hit = first_open(by_amt.get(r.amount, []))
            elif method == "B":
                ks = by_amt.get(r.amount, []); ds = dues.get(r.amount, [])
                lo = bisect.bisect_left(ds, r.date - pd.Timedelta(days=15)); hi = bisect.bisect_right(ds, r.date + pd.Timedelta(days=30))
                c = [k for k in ks[lo:hi] if k not in closed]
                hit = min(c, key=lambda k: abs((r.date - due_of[k]).days)) if c else None
            else:
                nm = norm(r.payer)
                for a in [r.amount] + [r.amount + f for f in FEES]:
                    hit = first_open(by_ka.get((nm, a), []))
                    if hit is not None:
                        break
        if hit is not None:
            closed.add(hit)
        res.append(hit)
    out = pay[["pay", "true_inv", "kind", "amount"]].copy()
    out["matched"] = pd.array(res, dtype="Int64")
    return out


KEY = {}


def score(m, inv=None):
    """正しい：正解の請求、または同じ会社・同じ金額・同じ期日の請求（入れ替えても中身は同じ）"""
    if inv is not None:
        KEY.clear(); KEY.update({r.inv: (r.cust, r.amount, r.due) for r in inv.itertuples()})
    has = m["matched"].notna()
    same = [has_ and (KEY[int(mt)] == KEY[int(tr)]) for has_, mt, tr in zip(has, m["matched"].fillna(-1), m["true_inv"])]
    right = has & pd.Series(same, index=m.index)
    wrong = has & ~right
    return dict(pay=len(m), right=int(right.sum()), wrong=int(wrong.sum()), unmatched=int((~has).sum()),
                unmatched_amount=int(m.loc[~has, "amount"].sum()), wrong_amount=int(m.loc[wrong, "amount"].sum()),
                strict_wrong=int((has & (m["matched"] != m["true_inv"])).sum()))


def sql_rownumber(inv, pay):
    """SQL でよく書く形：同じ金額の請求と入金を、それぞれ日付の順に番号を振って番号どうしでつなぐ"""
    con = duckdb.connect()
    con.register("inv", inv[["inv", "amount", "due"]])
    con.register("pay", pay[["pay", "amount", "date", "true_inv"]])
    q = open(SQL / "02_rownumber_match_duckdb.sql", encoding="utf-8").read()
    return con.sql(q).df()


def main():
    cust, inv, pay = make_data()
    inv.to_csv(DATA / "fictional_invoices.csv", index=False)
    pay.to_csv(DATA / "fictional_payments.csv", index=False)
    cust.to_csv(DATA / "fictional_customers.csv", index=False)
    labels = {"A": "①金額だけ", "B": "②金額＋日付の近さ", "C": "③金額＋名義の正規化\n（手数料差引も許す）", "D": "④請求番号→なければ③"}
    out, ms = {}, {}
    for k in "ABCD":
        ms[k] = match(inv, pay, cust, k)
        out[k] = score(ms[k], inv)
    sq = sql_rownumber(inv, pay)
    has = sq["inv"].notna()
    sqm = sq.rename(columns={"inv": "matched"}).merge(pay[["pay", "kind", "amount"]], on="pay")
    sqm["matched"] = sqm["matched"].astype("Int64")
    score(ms["A"], inv)
    out["SQL"] = score(sqm)
    out["SQL_equals_A"] = bool((sqm.sort_values("pay")["matched"].fillna(-1).values == ms["A"]["matched"].fillna(-1).values).all())
    # 同じ金額の請求がどれだけあるか
    dup = inv.groupby("amount")["inv"].transform("size")
    out["same_amount_share"] = float((dup > 1).mean())
    out["n_invoices"] = len(inv); out["n_payments"] = len(pay)
    out["kinds"] = pay["kind"].value_counts().to_dict()
    out["unpaid_invoices"] = int((~inv["inv"].isin(pay["true_inv"])).sum())
    # ①の誤りの内訳
    a = ms["A"].merge(inv[["inv", "cust"]].rename(columns={"inv": "matched", "cust": "m_cust"}), on="matched", how="left")
    a = a.merge(inv[["inv", "cust"]].rename(columns={"inv": "true_inv", "cust": "t_cust"}), on="true_inv", how="left")
    a = a.merge(inv[["inv", "due"]].rename(columns={"inv": "matched", "due": "m_due"}), on="matched", how="left")
    a = a.merge(inv[["inv", "due"]].rename(columns={"inv": "true_inv", "due": "t_due"}), on="true_inv", how="left")
    w = a[a["matched"].notna() & (a["matched"] != a["true_inv"])]
    out["A_wrong_breakdown"] = {"別の会社の同じ金額": int((w["m_cust"] != w["t_cust"]).sum()),
                                "同じ会社の別の月": int(((w["m_cust"] == w["t_cust"]) & (w["m_due"] != w["t_due"])).sum()),
                                "同じ会社・同じ月（入れ替えても同じ）": int(((w["m_cust"] == w["t_cust"]) & (w["m_due"] == w["t_due"])).sum())}
    out["A_wrong_split"] = int((w["kind"] == "分割").sum())
    # 定額の会社の割合を変える
    rows = []
    for fs in [0.0, 0.2, 0.4, 0.6, 0.8]:
        for rep in range(3):
            c2, i2, p2 = make_data(fixed_share=fs, seed=SEED + 100 * rep + int(fs * 10))
            row = {"fixed_share": fs, "rep": rep, "same_amount_share": float((i2.groupby("amount")["inv"].transform("size") > 1).mean())}
            for k in "ABCD":
                s = score(match(i2, p2, c2, k), i2); row[k] = s["wrong"] / s["pay"]; row[k + "_un"] = s["unmatched"] / s["pay"]
            rows.append(row)
    sw = pd.DataFrame(rows); sw.to_csv(RES / "sweep_fixed_share.csv", index=False)
    swm = sw.groupby("fixed_share").mean(numeric_only=True)
    out["sweep"] = swm.round(4).to_dict(orient="index")
    pd.DataFrame(out_rows(out, labels)).to_csv(RES / "methods.csv", index=False)
    json.dump(out, open(RES / "a501_main.json", "w"), ensure_ascii=False, indent=1, default=str)
    figs(out, labels, swm)
    print(json.dumps({k: out[k] for k in ["A", "B", "C", "D", "SQL", "same_amount_share", "A_wrong_breakdown", "A_wrong_split", "kinds", "unpaid_invoices"]}, ensure_ascii=False))


def out_rows(out, labels):
    return [{"method": labels[k].replace("\n", ""), **out[k]} for k in "ABCD"]


def figs(out, labels, swm):
    # 図1：4通りの結果
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ks = list("ABCD"); n = out["A"]["pay"]
    r = [out[k]["right"] / n * 100 for k in ks]; w = [out[k]["wrong"] / n * 100 for k in ks]; u = [out[k]["unmatched"] / n * 100 for k in ks]
    y = np.arange(4)[::-1]
    ax.barh(y, r, color=LIGHT, label="正しい請求に消込")
    ax.barh(y, w, left=r, color=ORANGE, label="まちがった請求に消込")
    ax.barh(y, u, left=np.array(r) + np.array(w), color=GRAY, label="消し込めず残った")
    for yi, k in zip(y, ks):
        ax.text(101, yi, f"誤り {out[k]['wrong']:,}件　残り {out[k]['unmatched']:,}件", va="center", fontsize=9.5)
    ax.set_yticks(y, [labels[k] for k in ks]); ax.set_xlim(0, 100); ax.set_xlabel("入金に占める割合（%）")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False, fontsize=9.5)
    ax.set_title(f"入金{n:,}件を4通りで消し込むと", pad=26)
    save(fig, "a501_methods.png", SRC)
    # 図2：①の誤りの内訳
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    bd = {k: v for k, v in out["A_wrong_breakdown"].items() if "入れ替え" not in k}
    bd["分割入金の片方を\n別の請求に"] = out["A_wrong_split"]
    ks2 = list(bd); vs = [bd[k] for k in ks2]
    ax.barh(ks2[::-1], vs[::-1], color=[GRAY, BLUE, ORANGE])
    for i, v in enumerate(vs[::-1]):
        ax.text(v + 10, i, f"{v:,}件", va="center")
    ax.set_xlabel("件数"); ax.set_xlim(0, max(vs) * 1.25)
    ax.set_title("①金額だけの消込で、まちがえた相手")
    save(fig, "a501_breakdown.png", SRC)
    # 図3：定額の会社の割合と誤り
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x = swm.index * 100
    for k, c in zip("ABCD", [ORANGE, GRAY, BLUE, GREEN]):
        ax.plot(x, swm[k] * 100, marker="o", color=c, label=labels[k].replace("\n", ""))
    ax.set_xlabel("毎月同じ金額を請求する会社の割合（%）"); ax.set_ylabel("まちがった請求に消し込んだ入金（%）")
    ax.legend(frameon=False, fontsize=9); ax.set_ylim(bottom=0)
    ax.set_title("同じ金額の請求が多いほど、金額だけの消込は誤る")
    save(fig, "a501_sweep.png", SRC)


if __name__ == "__main__":
    main()
