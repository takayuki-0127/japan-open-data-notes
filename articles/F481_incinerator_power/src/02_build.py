"""data/raw の焼却施設の表（2005〜2024年度、20ファイル）から、必要な列だけを抜き出して data/facilities.csv を作る。ネットにはつながない。
列の位置は年度で違うので、見出しの文字で探す。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CODE = re.compile(r"^\d{4,5}$")  # 地方公共団体コード（4〜5桁。先頭の0が落ちている年がある）。2010〜2012年度は施設コードの列が空のため、こちらで行を判定する
KEYS = {  # 出力の列名: 見出しに含まれる文字（最初に見つかった列を使う）
    "pref": ["都道府県名"], "fac_code": ["施設コード"], "name": ["施設名称"],
    "tons": ["年間処理量"], "cap_tpd": ["処理能力"], "start_fy": ["使用開始年度"],
    "gen_kw": ["発電能力"], "gen_mwh": ["総発電量"], "status": ["施設の改廃"],
}


def num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


out = []
for p in sorted(RAW.glob("incinerator_fy*.xls*")):
    fy = int(re.search(r"fy(\d{4})", p.name).group(1))
    sheets = pd.read_excel(p, sheet_name=None, header=None, dtype=str)
    df = max(sheets.values(), key=len)  # 施設の表（いちばん長いシート）
    m = df.apply(lambda c: c.astype(str).str.strip().str.match(CODE))
    ccol = int(m.sum().idxmax())  # 5桁のコードが最も多い列
    is_code = m[ccol]
    first = int(np.argmax(is_code.values))
    head = df.iloc[:first].fillna("").astype(str)
    hdr = ["".join(head.iloc[:, j].tolist()).replace("\n", "").replace(" ", "") for j in range(df.shape[1])]
    col = {}
    for k, kws in KEYS.items():
        cand = [j for j, h in enumerate(hdr) if all(w in h for w in kws)]
        if k == "gen_kw":
            cand = [j for j in cand if "効率" not in hdr[j]]
        col[k] = cand[0]
    d = df.iloc[first:][is_code.iloc[first:]].copy()
    rec = pd.DataFrame({k: d.iloc[:, j].astype(str).str.strip() for k, j in col.items()})
    for k in ["tons", "cap_tpd", "start_fy", "gen_kw", "gen_mwh"]:
        rec[k] = num(rec[k])
    rec["status"] = rec["status"].replace({"nan": ""})
    rec.insert(0, "fy", fy)
    out.append(rec)
    print(fy, len(rec), {k: hdr[j][:12] for k, j in col.items() if k in ("gen_kw", "gen_mwh", "cap_tpd")})
fac = pd.concat(out, ignore_index=True)
fac = fac.sort_values(["fy", "fac_code"]).reset_index(drop=True)
fac.to_csv(ROOT / "data" / "facilities.csv", index=False)
print(len(fac))
