"""切り出した第1表（PDF 1ページ）から、年度×産業（大分類）の表を作る（オフライン。pdftotext を使う）。
出力：data/koyouhoken_by_industry.csv（fy, code, name, new, new_voluntary, closed, withdrawn, stock_end）"""
import pathlib, re, subprocess
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
Z2H = str.maketrans("０１２３４５６７８９", "0123456789")
def fy_of(t):
    m = re.search(r"(平成|令和)([０-９0-9元]+)年度[（(]単位：所[）)]", t)
    n = 1 if m.group(2) == "元" else int(m.group(2).translate(Z2H))
    return (1988 if m.group(1) == "平成" else 2018) + n
recs = []
for p in sorted(RAW.glob("koyouhoken_*_t1.pdf")):
    t = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True).stdout.decode("utf-8")
    fy = fy_of(t)
    for line in t.splitlines():
        s = line.strip()
        m = re.match(r"^([Ａ-Ｔ])\s*(\S+)", s)
        is_total = re.match(r"^計\s", s)
        if not (m or is_total): continue
        nums = [int(x.replace(",", "")) for x in re.findall(r"(?<![（\d])\d{1,3}(?:,\d{3})*(?![）\d])", s.split("）")[-1] if "）" in s else s)]
        if len(nums) < 8: continue
        nums = nums[-8:]
        code = "TOTAL" if is_total else m.group(1)
        name = "計" if is_total else m.group(2)
        recs.append(dict(fy=fy, code=code, name=name, new=nums[0], new_voluntary=nums[1], closed=nums[2], withdrawn=nums[3], stock_end=nums[4]))
d = pd.DataFrame(recs).drop_duplicates(["fy", "code"])
chk = d[d.code != "TOTAL"].groupby("fy")[["new", "closed", "stock_end"]].sum() - d[d.code == "TOTAL"].set_index("fy")[["new", "closed", "stock_end"]]
print("check (sum of industries - total):", chk.to_dict()); assert (chk[["new", "closed"]].abs() == 0).all().all()
d.to_csv(DATA / "koyouhoken_by_industry.csv", index=False)
print(d.groupby("fy").size().to_dict()); print(d[d.code == "TOTAL"].to_string())
