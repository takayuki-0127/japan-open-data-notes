"""303：架空の注文データを月×地域の表にまとめる処理。BUG に名前を入れると、その不具合（または無害な書き換え）が入る。
仕様：
 1. 店コードは前後の空白を取り、大文字にそろえる
 2. 同じ order_id が複数あれば、updated_at がいちばん新しい行だけを使う
 3. status が CANCELLED（大文字小文字は問わない）の注文は除く
 4. 金額が空の行は除き、除いた件数を数える
 5. 税抜きの行（tax_included=0）は 1.1 倍して税込みにそろえる。端数は、月×地域の合計を出してから四捨五入
 6. 注文の月は、日本時間（UTC+9）の注文日時で決める
 7. 店マスタにない店コードは、地域「不明」に入れる（落とさない）。店マスタに同じコードが2行あれば、最初の1行を使う
 8. 出力：month, region, sales, orders, customers（customers は月×地域の中で重ならない顧客の数）。month・region の順に並べる
"""
import pandas as pd

def normalize_store(s, bug):
    if bug == "店コードをそろえない":
        return s
    if bug == "店コードの空白だけ取る":
        return s.str.strip()
    return s.str.strip().str.upper()

def dedup_orders(df, bug):
    if bug == "重複を取らない":
        return df
    df = df.sort_values(["order_id", "updated_at"])
    keep = "first" if bug == "重複で古い行を残す" else "last"
    return df.drop_duplicates("order_id", keep=keep)

def drop_cancelled(df, bug):
    if bug == "取消を除かない":
        return df
    if bug == "取消を大文字だけで判定":
        return df[df.status != "CANCELLED"]
    return df[df.status.str.upper() != "CANCELLED"]

def clean_amount(df, bug):
    if bug == "金額の空を0にする":
        return df.assign(amount=df.amount.fillna(0)), 0
    n = int(df.amount.isna().sum())
    return df[df.amount.notna()], n

def to_tax_included(df, bug):
    """税込みにそろえる。端数の扱いをはっきりさせるため、金額は「10分の1円」の整数で持つ（amount_x10）"""
    amt = df.amount.astype("int64")
    if bug == "税を全部の行にかける":
        x10 = amt * 11
    elif bug == "税込みの行にも税をかける（逆）":
        x10 = (amt * 10).where(df.tax_included == 0, amt * 11)
    else:
        x10 = (amt * 10).where(df.tax_included == 1, amt * 11)
    if bug == "行ごとに四捨五入":
        x10 = ((x10 + 5) // 10) * 10
    return df.assign(amount_x10=x10)

def order_month(df, bug):
    ts = pd.to_datetime(df.ordered_at_utc)
    if bug != "月を UTC で決める":
        ts = ts + pd.Timedelta(hours=9)
    if bug == "月末の日を前の月に入れない（23時以降を翌月へ）":
        ts = ts + pd.Timedelta(hours=1)
    return df.assign(month=ts.dt.strftime("%Y-%m"))

def join_region(df, master, bug):
    m = master.assign(store_code=master.store_code.str.strip().str.upper())
    if bug != "店マスタの重複を取らない":
        m = m.drop_duplicates("store_code", keep="first")
    how = "inner" if bug == "マスタにない店を落とす" else "left"
    out = df.merge(m[["store_code", "region"]], on="store_code", how=how)
    if bug != "地域が空のまま集計":
        out["region"] = out.region.fillna("不明")
    return out

def aggregate(df, bug):
    g = df.groupby(["month", "region"])          # 地域が空（NaN）の行は、groupby の既定では落ちる
    cust = g.customer_id.count() if bug == "顧客を延べで数える" else g.customer_id.nunique()
    out = pd.DataFrame({"sales": ((g.amount_x10.sum() + 5) // 10).astype("int64"),   # 合計してから四捨五入
                        "orders": g.order_id.count(), "customers": cust}).reset_index()
    if bug == "（無害）列の順を変える":
        out = out[["region", "month", "sales", "orders", "customers"]]
    if bug == "（無害）行の順を変える":
        return out.sort_values(["region", "month"]).reset_index(drop=True)
    return out.sort_values(["month", "region"]).reset_index(drop=True)

def run(orders, master, bug=None):
    df = orders.copy()
    df["store_code"] = normalize_store(df.store_code, bug)
    df = dedup_orders(df, bug)
    df = drop_cancelled(df, bug)
    df, n_null = clean_amount(df, bug)
    df = to_tax_included(df, bug)
    df = order_month(df, bug)
    df = join_region(df, master, bug)
    return aggregate(df, bug), {"rejected_null_amount": n_null}

BUGS = ["店コードをそろえない", "店コードの空白だけ取る", "重複を取らない", "重複で古い行を残す", "取消を除かない", "取消を大文字だけで判定",
        "金額の空を0にする", "税を全部の行にかける", "税込みの行にも税をかける（逆）", "行ごとに四捨五入", "月を UTC で決める",
        "月末の日を前の月に入れない（23時以降を翌月へ）", "店マスタの重複を取らない", "マスタにない店を落とす", "地域が空のまま集計", "顧客を延べで数える"]
HARMLESS = ["（無害）列の順を変える", "（無害）行の順を変える"]
