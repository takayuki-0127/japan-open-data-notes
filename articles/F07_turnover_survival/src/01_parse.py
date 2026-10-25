"""厚労省の PDF から取り出した文字（data/raw/mhlw_turnover_pdf_text.json）を表にし、景気指標と合わせる。
PDF の文字は、ページ上で pdf.js の getTextContent で行ごとに並べたもの（README 参照）。"""
import json, re
from common import *

T = json.load(open(RAW / "mhlw_turnover_pdf_text.json", encoding="utf-8"))
NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+|-)"

def era(m):
    y = 1 if m.group(2) == "元" else int(m.group(2))
    return (1988 if m.group(1) == "平成" else 2018) + y

# ---- 1) 学歴別・卒業年別（1996〜2023年3月卒は3年目まで、2024年は2年目まで、2025年は1年目まで）
t = T["001318985"].split("\n")
rates, cnts, part = [], [], []
for l in t:
    l2 = re.sub(r"(平成|令和)(\d+|元)年\d+月", "", l)
    dec = re.findall(r"\d+\.\d", l2)
    ints = re.findall(r"(?<![\d.])\d{1,3}(?:,\d{3})*(?![\d.])", l2)
    if len(dec) == 4: rates.append([float(x) for x in dec])
    if len(ints) == 5: cnts.append([int(x.replace(",", "")) for x in ints])
    if len(ints) in (3, 4) and not dec and "注" not in l and "就職者" not in l and "人）" not in l:
        part.append([int(x.replace(",", "")) for x in ints])
rows = []
for i, (r, c) in enumerate(zip(rates[:112], cnts[:112])):
    rows.append(dict(grad_year=1996 + i % 28, education=EDU[i // 28], hires=c[0],
                     sep_y1=c[2], sep_y2=c[3], sep_y3=c[4], sep3y=c[1], rate3y=r[0]))
# 末尾の途中までの卒業年（各学歴：2024年3月卒＝4つ、2025年3月卒＝3つの数）
assert len(part) == 8, part
for j, ed in enumerate(EDU):
    a, b = part[2 * j], part[2 * j + 1]
    rows.append(dict(grad_year=2024, education=ed, hires=a[0], sep_y1=a[2], sep_y2=a[3], sep_y3=np.nan, sep3y=np.nan, rate3y=np.nan))
    rows.append(dict(grad_year=2025, education=ed, hires=b[0], sep_y1=b[2], sep_y2=np.nan, sep_y3=np.nan, sep3y=np.nan, rate3y=np.nan))
main = pd.DataFrame(rows).sort_values(["education", "grad_year"])
full = main[main.grad_year <= 2023]
assert (full.sep_y1 + full.sep_y2 + full.sep_y3 - full.sep3y).abs().max() == 0
assert (full.sep3y / full.hires * 100 - full.rate3y).abs().max() < 0.06
main.to_csv(DATA / "turnover_by_education.csv", index=False)

# ---- 2) 産業別（大学・高校、2003〜2025年3月卒）
def parse_ind(key, ed):
    out = []
    for pg in T[key].split("##P")[1:]:
        lines = pg.split("\n")
        hdr = [l for l in lines if "月卒" in l][0]
        yrs = [era(m) for m in re.finditer(r"(平成|令和)(\d+|元)年", hdr)]
        pend = None
        for l in lines:
            s = l.strip()
            if not s or any(k in s for k in ["卒", "注", "離職", "集計値", "産業分類", "単位", "就職者数", "①"]) or s.startswith("（"):
                continue
            toks = s.split(" ")
            nums = [x for x in toks if re.fullmatch(NUM, x)]
            name = "".join(x for x in toks if not re.fullmatch(NUM, x))
            if nums and not name: pend = nums; continue
            if name and not nums and pend: nums, pend = pend, None
            v = [np.nan if x == "-" else int(x.replace(",", "")) for x in nums]
            if len(yrs) == 3 and len(v) == 9:      # 最後のページ：4つ・3つ・2つ
                out += [dict(education=ed, grad_year=yrs[0], industry=name, hires=v[0], sep_cum3=v[1], sep_cum2=v[2], sep_cum1=v[3]),
                        dict(education=ed, grad_year=yrs[1], industry=name, hires=v[4], sep_cum3=np.nan, sep_cum2=v[5], sep_cum1=v[6]),
                        dict(education=ed, grad_year=yrs[2], industry=name, hires=v[7], sep_cum3=np.nan, sep_cum2=np.nan, sep_cum1=v[8])]
            elif name and len(v) == 4 * len(yrs):
                for i, y in enumerate(yrs):
                    out.append(dict(education=ed, grad_year=y, industry=name, hires=v[4*i], sep_cum3=v[4*i+1], sep_cum2=v[4*i+2], sep_cum1=v[4*i+3]))
    return pd.DataFrame(out)
ind = pd.concat([parse_ind("001319024", "大学"), parse_ind("001319006", "高校")])
chk = ind[ind.industry == "調査産業計"].merge(full, on=["education", "grad_year"])
assert (chk.hires_x - chk.hires_y).abs().max() == 0 and (chk.sep_cum3 - chk.sep3y).abs().max() == 0
ind.to_csv(DATA / "turnover_by_industry.csv", index=False)

# ---- 3) 事業所規模別（大学・高校、2003〜2023年3月卒、1・2・3年目までの累積）
SIZES = ["5人未満", "5～29人", "30～99人", "100～499人", "500～999人", "1000人以上"]
out = []
for key, ed in [("001319018", "大学"), ("001319002", "高校")]:
    lab, yr = None, 2002
    for l in T[key].split("\n"):
        m = re.search(r"([１２３])年目まで", l)
        if m: lab = "１２３".index(m.group(1)) + 1
        l2 = re.sub(r"(平成|令和)(\d+|元)年.*?卒", "", l)
        toks = re.findall(r"\d{1,3}(?:,\d{3})+|\d+\.\d|\d+", re.sub("[１２３]", "", l2))
        if len(toks) == 15 and lab:
            if lab == 1: yr += 1
            v = [float(x.replace(",", "")) for x in toks]
            out.append(dict(education=ed, grad_year=yr, k=lab, size="規模計", sep_cum=v[1], rate_cum=v[2], hires=v[0]))
            for i, s in enumerate(SIZES):
                out.append(dict(education=ed, grad_year=yr, k=lab, size=s, sep_cum=v[3+2*i], rate_cum=v[4+2*i], hires=v[3+2*i] / v[4+2*i] * 100))
            lab = None
size = pd.DataFrame(out)
size.to_csv(DATA / "turnover_by_size.csv", index=False)

# ---- 4) 景気指標（年平均）：有効求人倍率（パートを含む一般）、完全失業率（季節調整値の年平均）
jo = pd.read_csv(RAW / "job_openings_national_annual.csv")[["年", "有効求人倍率"]].rename(columns={"年": "year", "有効求人倍率": "jobs_ratio"})
lf = pd.read_excel(RAW / "lt01-a10.xlsx", sheet_name="季節調整値", header=None)
lf = lf[lf[1].astype(str).str.endswith("月")].reset_index(drop=True)
lf["year"] = 1953 + lf.index // 12
lf["unemp"] = pd.to_numeric(lf[19], errors="coerce")
ue = lf.groupby("year").unemp.mean().round(2).reset_index()
macro = jo.merge(ue, on="year", how="outer").sort_values("year")
macro.to_csv(DATA / "macro_annual.csv", index=False)
print(main.groupby("education").grad_year.agg(["min", "max", "count"]))
print(ind.groupby("education").grad_year.agg(["min", "max"]), ind.industry.nunique())
print(size.groupby("education").grad_year.agg(["min", "max"]))
print(macro.tail(4))
