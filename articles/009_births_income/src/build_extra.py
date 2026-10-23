"""追加データ：統計でみる市区町村のすがた2026（D 行政基盤・H 居住・I 健康・医療）と、
総務省「ふるさと納税に関する現況調査」（令和7年度受入額・令和8年度課税の住民税控除額）を、市区町村コードでつなぐ。
出力: data/municipal_extra.csv"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "data" / "raw_extra"

def read_kiso(path):
    df = pd.read_excel(path, header=None)   # 行7=項目コード、行10以降=地域（列1=地域コード）
    cols = [c for c in range(10, df.shape[1]) if str(df.iat[7, c]).strip() not in ("nan", "")]
    body = df.iloc[10:]
    out = pd.DataFrame({"code": pd.to_numeric(body[1], errors="coerce")})
    for c in cols:
        out[str(df.iat[7, c]).strip()] = pd.to_numeric(body[c], errors="coerce")
    out = out.dropna(subset=["code"]); out["code"] = out["code"].astype(int)
    return out.drop_duplicates("code")

def code5(s):  # 6桁の団体コード（検査数字つき）→ 5桁
    return s.astype(int).astype(str).str.zfill(6).str[:5].astype(int)

def furusato():
    a = pd.read_excel(RAW / "furusato_r7_recv.xlsx", header=None, skiprows=13)[[0, 4, 17]]
    a.columns = ["c6", "fn_recv", "fn_cost"]          # ①受入額（円）、募集に要した費用の合計（円）
    a = a[pd.to_numeric(a.c6, errors="coerce").notna()]; a["code"] = code5(a.c6)
    b = pd.read_excel(RAW / "furusato_r8_deduction.xlsx", sheet_name="集計表", header=None, skiprows=18)[[0, 3, 4, 5]]
    b.columns = ["c6", "fn_donors", "fn_donation", "fn_ded_city"]   # 住民の寄附者数・寄附金額・市町村民税の控除額
    b = b[pd.to_numeric(b.c6, errors="coerce").notna()]; b["code"] = code5(b.c6)
    m = a.drop(columns="c6").merge(b.drop(columns="c6"), on="code", how="outer")
    return m.apply(pd.to_numeric, errors="coerce")

if __name__ == "__main__":
    d = furusato()
    for L in "dhi":
        d = d.merge(read_kiso(RAW / f"2026-{L}.xls"), on="code", how="outer")
    d.to_csv(ROOT / "data" / "municipal_extra.csv", index=False)
    print(d.shape)
