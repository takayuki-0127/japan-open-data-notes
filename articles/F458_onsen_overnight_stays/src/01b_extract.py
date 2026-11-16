"""data/raw/onsen_trend_table.pdf から表の数字を取り出して data/onsen_trend.csv にする（一度だけ流す。pdftotext（poppler-utils）が必要）。
取り出した行は、源泉総数 = 自噴＋動力（利用源泉）＋自噴＋動力（未利用源泉）が成り立つかで確かめる。"""
import pathlib, re, subprocess, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
txt = subprocess.run(["pdftotext", "-layout", str(ROOT / "data" / "raw" / "onsen_trend_table.pdf"), "-"], capture_output=True, text=True, check=True).stdout
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}
era = None
rows = []
for line in txt.splitlines():
    s = unicodedata.normalize("NFKC", line).strip()
    m = re.match(r"^(昭和|平成|令和)?(元|\d+)年度\s+(.*)$", s)
    if not m:
        continue
    if m.group(1):
        era = m.group(1)
    fy = ERA[era] + (1 if m.group(2) == "元" else int(m.group(2)))
    toks = m.group(3).split()
    vals = [None if t in ("-", "－") else float(t.replace(",", "")) for t in toks]
    # 後ろから：国民保養温泉地の延宿泊、公衆浴場数、延宿泊利用人員、収容定員、宿泊施設数
    rows.append(dict(fy=fy, n_tokens=len(vals), stays=vals[-3], capacity=vals[-4], facilities=vals[-5], public_baths=vals[-2],
                     kokumin_stays=vals[-1], onsen_areas=vals[2] if len(vals) >= 3 else None, sources_total=vals[3] if len(vals) >= 4 else None,
                     a_jifun=vals[4] if len(vals) >= 6 else None, a_doryoku=vals[5] if len(vals) >= 6 else None,
                     b_jifun=vals[6] if len(vals) >= 8 else None, b_doryoku=vals[7] if len(vals) >= 8 else None))
d = pd.DataFrame(rows)
# 確かめ：表の列の数がそろっている年（1970年度以降）で 源泉総数 = 4つの和
ok = d[(d.fy >= 1970) & (d.n_tokens == 20)]
chk = (ok.a_jifun + ok.a_doryoku + ok.b_jifun + ok.b_doryoku - ok.sources_total).abs()
print("源泉総数との差（件）の最大:", chk.max(), " 差がある年度:", list(ok.fy[chk > 0]))
assert (chk / ok.sources_total).max() < 0.001, ok[chk > 5]  # 元の表そのものの小さな差（0.1%未満）だけを許す。列がずれていれば大きな差になる
assert d.fy.is_unique and d.fy.min() == 1957 and d.fy.max() == 2024, (d.fy.min(), d.fy.max())
d.to_csv(ROOT / "data" / "onsen_trend.csv", index=False)
print(d[["fy", "n_tokens", "facilities", "capacity", "stays", "kokumin_stays"]].to_string())
