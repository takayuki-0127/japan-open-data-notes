"""03 分析：日銀の保有割合の推移、頂点、頂点からの変化、取引と調整への分解、部門別の割合の変化、頑健性。
出力：results/shares_quarterly.csv、results/sector_change.csv、results/boj_decomp.csv、results/robustness.csv、results/main.json
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
t = pd.read_csv(D / "ff_quarterly.csv", index_col="period")
b = pd.read_csv(D / "bs01_quarterly.csv", index_col="period")
nm = pd.read_csv(D / "series_names.csv").set_index("code")["name"]

# 部門の名前は系列の名称の「／部門／」の文字から付ける（コードの並びに頼らない）
def sector_of(code):
    parts = nm[code].split("／")
    return parts[1]

MAIN = ["中央銀行", "預金取扱機関", "保険・年金基金", "公的金融機関", "一般政府", "家計", "海外"]   # 互いに重ならない大きな部門
SUB = ["銀行等", "郵便貯金", "国内銀行", "中小企業金融機関等", "農林水産金融機関", "生命保険", "非生命保険", "年金基金",
       "社会保障基金", "うち公的年金", "証券投資信託", "ディーラー・ブローカー", "非金融法人企業", "対家計民間非営利団体"]


def stock_codes(asset):
    """asset: A311（国債・財投債）または A310（国庫短期証券）。部門名→コード。"""
    out = {}
    for c in t.columns:
        if c.startswith("FOF_FFAS") and c.endswith(asset):
            out[sector_of(c)] = c
    return out


def shares(include_tb=False):
    s311 = stock_codes("A311")
    tot = t["FOF_FFAS420L311"] + t["FOF_FFAS181L311"]
    hold = {k: t[v].copy() for k, v in s311.items()}
    if include_tb:
        s310 = stock_codes("A310")
        tot = tot + t["FOF_FFAS420L310"] + t["FOF_FFAS181L310"]
        for k, v in s310.items():
            hold[k] = hold.get(k, 0) + t[v]
    df = pd.DataFrame({k: hold[k] for k in MAIN + SUB if k in hold})
    df["その他"] = tot - df[MAIN].sum(axis=1)
    sh = df.div(tot, axis=0) * 100
    sh["発行残高（兆円）"] = tot / 1e4
    return sh


def peak(series):
    p = series.idxmax()
    return p, float(series.max())


def main():
    sh = shares(False)
    sh.round(4).to_csv(R / "shares_quarterly.csv")
    boj = sh["中央銀行"]
    pk, pv = peak(boj)
    last = sh.index[-1]
    first50 = next(p for p in sh.index if boj[p] > 50)
    above50 = [p for p in sh.index if boj[p] > 50]
    m = {"first_period": sh.index[0], "last_period": last,
         "boj_share_first": round(float(boj.iloc[0]), 2),
         "boj_share_2013Q1": round(float(boj["2013Q1"]), 2),
         "boj_share_peak": round(pv, 2), "boj_share_peak_period": pk,
         "boj_share_last": round(float(boj[last]), 2),
         "boj_share_drop_pt": round(pv - float(boj[last]), 2),
         "first_above50": first50, "last_above50": above50[-1], "n_quarters_above50": len(above50),
         "boj_share_first_above50": round(float(boj[first50]), 2),
         "boj_share_last_above50": round(float(boj[above50[-1]]), 2),
         "boj_share_min": round(float(boj.min()), 2), "boj_share_min_period": boj.idxmin(),
         "boj_share_2025Q3": round(float(boj["2025Q3"]), 2),
         "total_outstanding_last_tn": round(float(sh.loc[last, "発行残高（兆円）"]), 1),
         "total_outstanding_peak_tn": round(float(sh.loc[pk, "発行残高（兆円）"]), 1)}
    # 日銀の残高（時価）
    bj = t["FOF_FFAS110A311"]
    m["boj_stock_peak_tn"] = round(float(bj.max()) / 1e4, 1)
    m["boj_stock_peak_period"] = bj.idxmax()
    m["boj_stock_at_sharepeak_tn"] = round(float(bj[pk]) / 1e4, 1)
    m["boj_stock_last_tn"] = round(float(bj[last]) / 1e4, 1)

    # H3：頂点の次の期から最新までの、日銀の残高の変化＝取引＋調整
    idx = list(t.index)
    after = idx[idx.index(pk) + 1:]
    flow = float(t.loc[after, "FOF_FFAF110A311"].sum())
    adj = float(t.loc[after, "FOF_FFAR110A311"].sum())
    dS = float(bj[last] - bj[pk])
    m.update({"boj_change_since_peak_tn": round(dS / 1e4, 1), "boj_flow_since_peak_tn": round(flow / 1e4, 1),
              "boj_adj_since_peak_tn": round(adj / 1e4, 1),
              "boj_identity_gap_tn": round((dS - flow - adj) / 1e4, 2),
              "boj_flow_share_of_drop_pct": round(flow / dS * 100, 1) if dS < 0 else None})
    dec = pd.DataFrame({"period": idx[1:], "stock_change": bj.diff().iloc[1:].values,
                        "flow": t["FOF_FFAF110A311"].iloc[1:].values, "adjustment": t["FOF_FFAR110A311"].iloc[1:].values})
    dec["gap"] = dec["stock_change"] - dec["flow"] - dec["adjustment"]
    dec.round(1).to_csv(R / "boj_decomp.csv", index=False)
    m["identity_max_abs_gap_oku"] = round(float(dec["gap"].abs().max()), 1)

    # H4：頂点→最新の、部門別の割合の変化
    ch = pd.DataFrame({"share_peak": sh.loc[pk, MAIN + ["その他"] + SUB], "share_last": sh.loc[last, MAIN + ["その他"] + SUB]})
    ch["change_pt"] = ch["share_last"] - ch["share_peak"]
    ch["level"] = ["main"] * (len(MAIN) + 1) + ["sub"] * len(SUB)
    ch.index.name = "sector"
    ch.round(3).to_csv(R / "sector_change.csv")
    mainch = ch[ch["level"] == "main"].drop(index="中央銀行")
    m["largest_gain_sector"] = mainch["change_pt"].idxmax()
    m["sector_change_pt"] = {k: round(float(v), 2) for k, v in ch["change_pt"].items()}
    m["sector_share_last"] = {k: round(float(v), 2) for k, v in ch["share_last"].items()}
    m["sector_share_peak"] = {k: round(float(v), 2) for k, v in ch["share_peak"].items()}

    # 頑健性
    rob = []
    def add(label, s):
        p, v = peak(s)
        rob.append({"check": label, "peak_period": p, "peak_share": round(v, 2), "last_share": round(float(s.iloc[-1]), 2),
                    "drop_pt": round(v - float(s.iloc[-1]), 2)})
    add("基本：国債・財投債（時価）", boj)
    sh_tb = shares(True)
    add("国庫短期証券を含む国債等（時価）", sh_tb["中央銀行"])
    # 簿価・額面に近い基準
    ratio = t["FOF_FFAB420L311"] / t["FOF_FFAS420L311"]
    face_tot = t["FOF_FFAB420L311"] + t["FOF_FFAS181L311"] * ratio
    bk = (b["MABJMA5B"] / face_tot).dropna() * 100
    add("日銀勘定の長期国債（簿価）÷額面に近い発行残高", bk)
    fy = boj[[p for p in boj.index if p.endswith("Q1")]]
    add("年度末（3月末）だけ", fy)
    bkb = b["MABJMA5B"].dropna()
    rob.append({"check": "日銀の残高（時価）の頂点", "peak_period": bj.idxmax(),
                "peak_amount_tn": round(float(bj.max()) / 1e4, 1), "last_amount_tn": round(float(bj.iloc[-1]) / 1e4, 1)})
    rob.append({"check": "日銀の残高（簿価、日銀勘定の長期国債）の頂点", "peak_period": bkb.idxmax(),
                "peak_amount_tn": round(float(bkb.max()) / 1e4, 1), "last_amount_tn": round(float(bkb.loc[last]) / 1e4, 1)})
    rob = pd.DataFrame(rob, columns=["check", "peak_period", "peak_share", "last_share", "drop_pt", "peak_amount_tn", "last_amount_tn"])
    rob.to_csv(R / "robustness.csv", index=False)
    m["robustness"] = [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in rob.to_dict(orient="records")]
    rng = pd.concat([boj, sh_tb["中央銀行"], bk], axis=1).dropna().loc["2013Q1":]
    rng = rng.max(axis=1) - rng.min(axis=1)
    m["definition_range_max_pt_since2013"] = round(float(rng.max()), 2)
    m["definition_range_max_period"] = rng.idxmax()
    m["definition_range_last_pt"] = round(float(rng.iloc[-1]), 2)
    m["face_to_market_ratio_last"] = round(float(ratio.iloc[-1]), 4)
    m["face_to_market_ratio_at_peak"] = round(float(ratio[pk]), 4)
    m["book_share_last"] = round(float(bk[last]), 2)
    m["bs01_long_last_month_note"] = "日銀勘定は四半期末の月の値を使用"
    # 仮説の判定
    m["H1"] = "支持" if (pv > 50 and int(pk[:4]) >= 2023) else "外れ"
    m["H2"] = "支持" if m["boj_share_drop_pt"] >= 5 else "外れ"
    m["H3"] = ("支持" if (dS < 0 and flow / dS >= 0.5) else "外れ")
    m["H4"] = "支持" if m["largest_gain_sector"] == "海外" else "外れ"
    json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(m, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
